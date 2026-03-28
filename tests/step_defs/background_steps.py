"""Background step definitions for BDD tests.

This module provides background/setup step definitions for pytest-bdd.
All business logic is delegated to boardfarm3 use_cases for portability.
"""

import time
from typing import Any

from boardfarm3.templates.acs import ACS as AcsTemplate
from boardfarm3.templates.cpe.cpe import CPE as CpeTemplate
from boardfarm3.use_cases import acs as acs_use_cases
from boardfarm3.use_cases import cpe as cpe_use_cases
from pytest_bdd import given


def _extract_index_from_key(key: str) -> int | None:
    """Extract the instance index from a GPV response key.

    GPV response keys may be mangled by the GenieACS driver's
    ``strip('._value')`` call, e.g. ``Device.Users.User.10.Usernam``
    instead of ``Device.Users.User.10.Username``.  We therefore
    split on dots and look for an integer at position 3.
    """
    parts = key.split(".")
    if len(parts) >= 5:
        try:
            return int(parts[3])
        except ValueError:
            pass
    return None


_INDEX_MULTIPLIER = 2
_MAX_USER_INDEX = 30


def discover_admin_user_index(acs: AcsTemplate, cpe: CpeTemplate) -> int:
    """Discover which user index corresponds to the GUI admin user.

    TR-069 instance indices are not guaranteed to be contiguous
    (1, 2, 3 …).  We query ``UserNumberOfEntries`` to learn
    how many users exist, then scan indices 1 … user_count * 2
    with individual GPV calls.  Each call triggers a CWMP
    connection-request → getParameterValues cycle, so the CPE
    is queried live (not just the ACS database).

    The scan exits early once all expected users have been found,
    avoiding unnecessary connection requests.

    If ``UserNumberOfEntries`` is unavailable (e.g. after a fresh
    ACS restart), the scan falls back to a fixed ceiling.

    Args:
        acs: ACS template instance
        cpe: CPE template instance

    Returns:
        The user index (e.g., 10) that corresponds to the admin user

    Raises:
        AssertionError: If no user with username='admin' is found
    """
    cpe_id = cpe.sw.cpe_id

    max_idx = _MAX_USER_INDEX
    user_count = None
    try:
        raw = acs_use_cases.get_parameter_value(
            acs, cpe, "Device.Users.UserNumberOfEntries",
            retries=2,
        )
        user_count = int(raw)
        if user_count > 0:
            max_idx = user_count * _INDEX_MULTIPLIER
    except Exception:  # noqa: BLE001
        pass

    if user_count is not None:
        print(
            f"CPE reports {user_count} users — scanning "
            f"indices 1–{max_idx} for admin user"
        )
    else:
        print(
            f"UserNumberOfEntries unavailable — scanning "
            f"indices 1–{max_idx} for admin user"
        )

    found_usernames: list[str] = []
    for user_idx in range(1, max_idx + 1):
        try:
            username = acs_use_cases.get_parameter_value(
                acs, cpe,
                f"Device.Users.User.{user_idx}.Username",
                retries=3,
            )
        except Exception:  # noqa: BLE001
            continue

        username = str(username).strip()
        if not username:
            continue

        found_usernames.append(f"User.{user_idx}={username}")
        if username.lower() == "admin":
            print(f"Found admin user at index {user_idx}")
            return user_idx

        if user_count and len(found_usernames) >= user_count:
            break

    raise AssertionError(
        f"No user with username='admin' found among "
        f"indices 1–{max_idx}. "
        f"Discovered: {found_usernames}"
    )


@given("a CPE is online and fully provisioned")
def cpe_is_online_and_provisioned(
    acs: AcsTemplate, cpe: CpeTemplate, bf_context: Any
) -> None:
    """Black-box: confirm online/provisioned state via ACS - uses use_cases.

    Store baseline state. Note: Boardfarm initializes the testbed and
    reboots the CPE, which causes it to connect to the ACS. By the time
    this step runs, the CPE should already be connected.
    """
    cpe_id = cpe.sw.cpe_id
    print(
        f"Querying CPE {cpe_id} via ACS to confirm it's online "
        "and provisioned..."
    )

    # Initialize configuration storage for verification
    if not hasattr(bf_context, "config_before_reboot"):
        bf_context.config_before_reboot = {}

    # Query the CPE for firmware version using use_case
    firmware_version = acs_use_cases.get_parameter_value(
        acs, cpe, "Device.DeviceInfo.SoftwareVersion"
    )
    bf_context.config_before_reboot["firmware_version"] = {
        "gpv_param": "Device.DeviceInfo.SoftwareVersion",
        "value": firmware_version,
    }

    # Get uptime using use_case
    bf_context.initial_uptime = cpe_use_cases.get_console_uptime_seconds(cpe)
    print(
        f"CPE baseline state captured: firmware="
        f"{firmware_version}, "
        f"uptime={bf_context.initial_uptime}s"
    )


@given('the user has set the CPE GUI password to "{password}"')
def user_sets_cpe_gui_password(
    acs: AcsTemplate,
    cpe: CpeTemplate,
    bf_context: Any,
    password: str,
):
    """Set CPE GUI password via ACS using TR-069 SPV - uses use_cases.

    Dynamically discovers which user index corresponds to the GUI admin user
    (username='admin' by default), then sets the password for that user.

    Yield-based teardown restores the password to the PrplOS default ("admin")
    when the scenario ends — even on failure. The teardown is idempotent: if
    the password was already restored by a later step, the redundant SPV call
    is swallowed harmlessly.
    """
    cpe_id = cpe.sw.cpe_id

    # Discover admin user index (reuse if already discovered)
    if not hasattr(bf_context, "admin_user_index"):
        bf_context.admin_user_index = discover_admin_user_index(acs, cpe)

    admin_user_idx = bf_context.admin_user_index
    param = f"Device.Users.User.{admin_user_idx}.Password"

    # Capture original encrypted password for change verification
    original_password = None
    try:
        original_password = acs_use_cases.get_parameter_value(acs, cpe, param)
    except Exception:  # noqa: BLE001
        pass

    # Set the new password
    print(f"Setting CPE GUI password for {cpe_id} (user {admin_user_idx})")
    success = acs_use_cases.set_parameter_value(acs, cpe, param, password)
    if not success:
        raise AssertionError("Failed to set CPE GUI password via SPV")

    # Verify the change was applied
    time.sleep(2)
    try:
        new_encrypted = acs_use_cases.get_parameter_value(acs, cpe, param)
        if original_password and new_encrypted != original_password:
            print("✓ Verified password was changed (encrypted value changed)")
        elif original_password and new_encrypted == original_password:
            print("⚠ Password encrypted value did not change")
        else:
            print("✓ Password change attempted (could not verify)")
    except Exception:  # noqa: BLE001
        pass

    # Store encrypted password for reboot-preservation verification
    if not hasattr(bf_context, "config_before_reboot"):
        bf_context.config_before_reboot = {}
    if "users" not in bf_context.config_before_reboot:
        bf_context.config_before_reboot["users"] = {"count": {}, "items": {}}

    try:
        encrypted_password = acs_use_cases.get_parameter_value(acs, cpe, param)
    except Exception:  # noqa: BLE001
        encrypted_password = password

    reboot_items = bf_context.config_before_reboot["users"]["items"]
    if str(admin_user_idx) not in reboot_items:
        reboot_items[str(admin_user_idx)] = {}
    reboot_items[str(admin_user_idx)]["Password"] = {
        "gpv_param": param,
        "value": encrypted_password,
    }

    print(f"✓ CPE GUI password set for user {admin_user_idx}")

    yield

    try:
        acs_use_cases.set_parameter_value(acs, cpe, param, "admin")
        print("✓ CPE GUI password restored to default")
    except Exception as exc:  # noqa: BLE001
        print(f"⚠ Could not restore CPE GUI password: {exc}")
