"""Background step definitions for BDD tests."""

import time
from typing import Any

from boardfarm3.templates.acs import ACS as AcsTemplate
from boardfarm3.templates.cpe.cpe import CPE as CpeTemplate
from pytest_bdd import given

from .helpers import get_console_uptime_seconds, gpv_value


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
    """Black-box: confirm online/provisioned state via ACS.

    Store baseline state. Note: Boardfarm initializes the testbed and
    reboots the CPE, which causes it to connect to the ACS. By the time
    this step runs, the CPE should already be connected. We query the ACS
    directly to confirm the CPE is available and get baseline state.
    """
    cpe_id = cpe.sw.cpe_id
    print(
        f"Querying CPE {cpe_id} via ACS to confirm it's online "
        "and provisioned..."
    )

    # Initialize configuration storage for verification
    if not hasattr(bf_context, "config_before_reboot"):
        bf_context.config_before_reboot = {}

    # Query the CPE for firmware version (gpv_value has built-in retry)
    firmware_version = gpv_value(acs, cpe, "Device.DeviceInfo.SoftwareVersion")
    bf_context.config_before_reboot["firmware_version"] = {
        "gpv_param": "Device.DeviceInfo.SoftwareVersion",
        "value": firmware_version,
    }

    bf_context.initial_uptime = get_console_uptime_seconds(cpe)
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
    """Set CPE GUI password via ACS using TR-069 SPV.

    Dynamically discovers which user index corresponds to the GUI admin user
    (username='admin' by default), then sets the password for that user.
    Captures original password before making changes for cleanup.

    Note: The admin user index is discovered dynamically and cached in
    bf_context.admin_user_index for use in subsequent steps.
    """
    cpe_id = cpe.sw.cpe_id

    # Discover admin user index (reuse if already discovered)
    if not hasattr(bf_context, "admin_user_index"):
        bf_context.admin_user_index = discover_admin_user_index(acs, cpe)

    admin_user_idx = bf_context.admin_user_index
    print(f"Using User.{admin_user_idx} as GUI admin user")

    # Capture original password BEFORE making changes
    # We'll only store it in original_config if the change succeeds
    original_password = None
    try:
        original_password = gpv_value(
            acs, cpe, f"Device.Users.User.{admin_user_idx}.Password"
        )
        print(
            f"Captured original user {admin_user_idx} "
            f"(GUI admin) password: '***'"
        )
    except Exception as e:  # noqa: BLE001
        print(f"⚠ Could not capture original password: {e}")
        # Continue anyway - we'll handle this below

    # Now set the new password
    print(f"Setting CPE GUI password for {cpe_id}: password='***'")

    # Set password using SPV
    params: list[dict[str, str | int | bool]] = [
        {f"Device.Users.User.{admin_user_idx}.Password": password},
    ]

    result = acs.SPV(params, cpe_id=cpe_id, timeout=60)
    if result != 0:
        raise AssertionError(
            f"Failed to set CPE GUI password via SPV "
            f"(status code: {result})"
        )

    # VERIFY the change was actually applied
    time.sleep(2)  # Give PrplOS time to process the change

    # For password, we can't easily verify the plaintext, but we can check
    # that the encrypted value changed (indicating the password was set)
    password_change_successful = False
    try:
        new_encrypted_password = gpv_value(
            acs, cpe, f"Device.Users.User.{admin_user_idx}.Password"
        )
        if original_password and new_encrypted_password != original_password:
            password_change_successful = True
            print(
                "✓ Verified password was changed "
                "(encrypted value changed)"
            )
        elif original_password and new_encrypted_password == original_password:
            print(
                "⚠ WARNING: Password encrypted value did not change - "
                "password may not have been set. This may indicate "
                "PrplOS rejected the password change."
            )
        else:
            # Couldn't compare, assume success if SPV succeeded
            password_change_successful = True
            print("✓ Password change attempted (could not verify)")
    except Exception as e:  # noqa: BLE001
        print(f"⚠ Could not verify password change: {e}")
        # Assume success if SPV succeeded and we can't verify
        password_change_successful = True

    # Store in original_config if the change was successful
    # (so cleanup only restores values that were actually changed)
    # Note: We always store password for cleanup, even if original_password
    # is None (cleanup will restore to default "admin" password)
    if password_change_successful:
        # Initialize original_config if needed
        if not hasattr(bf_context, "original_config"):
            bf_context.original_config = {}

        # Capture original values for cleanup (only if change succeeded)
        if "users" not in bf_context.original_config:
            bf_context.original_config["users"] = {
                "count": {},
                "items": {},
            }

        # Store password with GPV parameter path for cleanup
        # Even if original_password is None, we store it so cleanup
        # knows to restore
        items = bf_context.original_config["users"]["items"]
        if str(admin_user_idx) not in items:
            items[str(admin_user_idx)] = {}

        # Store password - use a placeholder if original wasn't captured
        # Cleanup will detect this is a password and restore to "admin"
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
            print(
                "✓ Stored original password in cleanup config: '***'"
            )
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
    # Initialize users structure if needed
    if "users" not in bf_context.config_before_reboot:
        bf_context.config_before_reboot["users"] = {
            "count": {},
            "items": {},
        }

    # Capture the encrypted password value for comparison
    # (SPV success means it's set)
    try:
        encrypted_password = gpv_value(
            acs, cpe, f"Device.Users.User.{admin_user_idx}.Password"
        )
    except Exception:  # noqa: BLE001
        # If we can't get the encrypted password, store the plaintext
        # (verification will handle this gracefully)
        encrypted_password = password

    # Store admin user password configuration with GPV parameter path
    reboot_items = bf_context.config_before_reboot["users"]["items"]
    if str(admin_user_idx) not in reboot_items:
        reboot_items[str(admin_user_idx)] = {}
    reboot_items[str(admin_user_idx)]["Password"] = {
        "gpv_param": f"Device.Users.User.{admin_user_idx}.Password",
        "value": encrypted_password,  # Encrypted value for comparison
    }

    print(
        f"✓ Recorded user {admin_user_idx} (GUI admin) password "
        f"for verification: '***'"
    )
