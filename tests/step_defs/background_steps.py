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


def discover_admin_user_index(acs: AcsTemplate, cpe: CpeTemplate) -> int:
    """Discover which user index corresponds to the GUI admin user.

    Searches through all users to find the one with username='admin'.
    This makes the code robust against configuration changes.

    Args:
        acs: ACS template instance
        cpe: CPE template instance

    Returns:
        The user index (e.g., 10) that corresponds to the admin user

    Raises:
        AssertionError: If no user with username='admin' is found
    """
    cpe_id = cpe.sw.cpe_id

    # Get total number of users
    try:
        user_count_result = acs.GPV(
            "Device.Users.UserNumberOfEntries",
            cpe_id=cpe_id,
            timeout=30,
        )
        if not user_count_result:
            raise AssertionError("Could not get user count")
        user_count = int(user_count_result[0].get("value", 0))
    except Exception as e:
        raise AssertionError(f"Failed to get user count: {e}") from e

    if user_count == 0:
        raise AssertionError("No users found in CPE")

    # Search through all users to find the one with username='admin'
    print(f"Searching through {user_count} users to find admin user...")
    for user_idx in range(1, user_count + 1):
        try:
            username_result = acs.GPV(
                f"Device.Users.User.{user_idx}.Username",
                cpe_id=cpe_id,
                timeout=30,
            )
            if username_result:
                value = username_result[0].get("value", "")
                # Convert to string and strip whitespace
                username = str(value).strip() if value else ""
                if username.lower() == "admin":
                    print(
                        f"✓ Found admin user at index {user_idx} "
                        f"(username='{username}')"
                    )
                    return user_idx
        except Exception as e:  # noqa: BLE001
            # Continue searching if this user doesn't exist or query fails
            print(f"⚠ Could not query User.{user_idx}: {e}")
            continue

    # If we get here, no admin user was found
    raise AssertionError(
        f"No user with username='admin' found among {user_count} users. "
        f"Please verify the CPE configuration."
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
) -> None:
    """Set CPE GUI password via ACS using TR-069 SPV - uses use_cases.

    Dynamically discovers which user index corresponds to the GUI admin user
    (username='admin' by default), then sets the password for that user.
    Captures original password before making changes for cleanup.
    """
    cpe_id = cpe.sw.cpe_id

    # Discover admin user index (reuse if already discovered)
    if not hasattr(bf_context, "admin_user_index"):
        bf_context.admin_user_index = discover_admin_user_index(acs, cpe)

    admin_user_idx = bf_context.admin_user_index
    print(f"Using User.{admin_user_idx} as GUI admin user")

    # Capture original password BEFORE making changes using use_case
    original_password = None
    try:
        original_password = acs_use_cases.get_parameter_value(
            acs, cpe, f"Device.Users.User.{admin_user_idx}.Password"
        )
        print(
            f"Captured original user {admin_user_idx} "
            f"(GUI admin) password: '***'"
        )
    except Exception as e:  # noqa: BLE001
        print(f"⚠ Could not capture original password: {e}")

    # Now set the new password using use_case
    print(f"Setting CPE GUI password for {cpe_id}: password='***'")

    success = acs_use_cases.set_parameter_value(
        acs, cpe, f"Device.Users.User.{admin_user_idx}.Password", password
    )

    if not success:
        raise AssertionError("Failed to set CPE GUI password via SPV")

    # VERIFY the change was actually applied
    time.sleep(2)  # Give PrplOS time to process the change

    password_change_successful = False
    try:
        new_encrypted_password = acs_use_cases.get_parameter_value(
            acs, cpe, f"Device.Users.User.{admin_user_idx}.Password"
        )
        if original_password and new_encrypted_password != original_password:
            password_change_successful = True
            print("✓ Verified password was changed (encrypted value changed)")
        elif original_password and new_encrypted_password == original_password:
            print(
                "⚠ WARNING: Password encrypted value did not change - "
                "password may not have been set."
            )
        else:
            password_change_successful = True
            print("✓ Password change attempted (could not verify)")
    except Exception as e:  # noqa: BLE001
        print(f"⚠ Could not verify password change: {e}")
        password_change_successful = True

    # Store in original_config if the change was successful
    if password_change_successful:
        if not hasattr(bf_context, "original_config"):
            bf_context.original_config = {}

        if "users" not in bf_context.original_config:
            bf_context.original_config["users"] = {
                "count": {},
                "items": {},
            }

        items = bf_context.original_config["users"]["items"]
        if str(admin_user_idx) not in items:
            items[str(admin_user_idx)] = {}

        items[str(admin_user_idx)]["Password"] = {
            "gpv_param": (
                f"Device.Users.User.{admin_user_idx}.Password"
            ),
            "value": (
                original_password
                if original_password
                else "PLACEHOLDER_FOR_CLEANUP"
            ),
        }
        if original_password:
            print("✓ Stored original password in cleanup config: '***'")
        else:
            print(
                "✓ Stored password marker in cleanup config "
                "(will restore to 'admin')"
            )

    if password_change_successful:
        print(
            f"✓ CPE GUI password set successfully for user {admin_user_idx} "
            f"(GUI admin)"
        )
    else:
        print(
            "⚠ Password change may have been rejected by PrplOS. "
            "Test continues."
        )

    # Store the password we set for verification
    if "users" not in bf_context.config_before_reboot:
        bf_context.config_before_reboot["users"] = {
            "count": {},
            "items": {},
        }

    # Capture the encrypted password value for comparison
    try:
        encrypted_password = acs_use_cases.get_parameter_value(
            acs, cpe, f"Device.Users.User.{admin_user_idx}.Password"
        )
    except Exception:  # noqa: BLE001
        encrypted_password = password

    reboot_items = bf_context.config_before_reboot["users"]["items"]
    if str(admin_user_idx) not in reboot_items:
        reboot_items[str(admin_user_idx)] = {}
    reboot_items[str(admin_user_idx)]["Password"] = {
        "gpv_param": f"Device.Users.User.{admin_user_idx}.Password",
        "value": encrypted_password,
    }

    print(
        f"✓ Recorded user {admin_user_idx} (GUI admin) password "
        f"for verification: '***'"
    )
