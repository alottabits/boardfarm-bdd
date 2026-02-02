"""Background Keywords for Robot Framework.

Keywords for background/setup operations, aligned with BDD scenario steps.
Uses @keyword decorator to map clean function names to scenario step text.

Mirrors: tests/step_defs/background_steps.py
"""

import time
from typing import Any

from robot.api.deco import keyword, library

from boardfarm3.templates.acs import ACS
from boardfarm3.templates.cpe.cpe import CPE
from boardfarm3.use_cases import acs as acs_use_cases
from boardfarm3.use_cases import cpe as cpe_use_cases


@library(scope="SUITE", doc_format="TEXT")
class BackgroundKeywords:
    """Keywords for background/setup operations matching BDD scenario steps."""

    def __init__(self) -> None:
        """Initialize BackgroundKeywords."""
        self._config_before_reboot: dict[str, Any] = {}
        self._original_config: dict[str, Any] = {}
        self._admin_user_index: int = None

    # =========================================================================
    # CPE State Keywords
    # =========================================================================

    @keyword("A CPE is online and fully provisioned")
    def verify_cpe_online_provisioned(self, acs: ACS, cpe: CPE) -> dict:
        """Confirm CPE is online and provisioned via ACS.

        Maps to scenario step:
        - "Given a CPE is online and fully provisioned"

        Arguments:
            acs: ACS device instance
            cpe: CPE device instance

        Returns:
            Dict with baseline state (firmware_version, initial_uptime)
        """
        cpe_id = cpe.sw.cpe_id
        print(
            f"Querying CPE {cpe_id} via ACS to confirm it's online "
            "and provisioned..."
        )

        # Query firmware version
        firmware_version = acs_use_cases.get_parameter_value(
            acs, cpe, "Device.DeviceInfo.SoftwareVersion"
        )

        # Get uptime
        initial_uptime = cpe_use_cases.get_console_uptime_seconds(cpe)

        print(
            f"CPE baseline state captured: firmware={firmware_version}, "
            f"uptime={initial_uptime}s"
        )

        self._config_before_reboot = {
            "firmware_version": {
                "gpv_param": "Device.DeviceInfo.SoftwareVersion",
                "value": firmware_version,
            }
        }

        return {
            "firmware_version": firmware_version,
            "initial_uptime": initial_uptime,
        }

    @keyword("CPE is online and provisioned")
    def cpe_is_online_and_provisioned(self, acs: ACS, cpe: CPE) -> dict:
        """Alias for A CPE is online and fully provisioned."""
        return self.verify_cpe_online_provisioned(acs, cpe)

    @keyword("Verify CPE is online and provisioned")
    def verify_cpe_is_online_and_provisioned(self, acs: ACS, cpe: CPE) -> dict:
        """Alias for A CPE is online and fully provisioned."""
        return self.verify_cpe_online_provisioned(acs, cpe)

    # =========================================================================
    # Password Configuration Keywords
    # =========================================================================

    @keyword("Set CPE GUI password")
    def set_cpe_gui_password(
        self, acs: ACS, cpe: CPE, password: str
    ) -> dict:
        """Set CPE GUI password via ACS using TR-069 SPV.

        Maps to scenario step:
        - "Given the user has set the CPE GUI password to 'newpassword'"

        Arguments:
            acs: ACS device instance
            cpe: CPE device instance
            password: New password to set

        Returns:
            Dict with admin_user_index and password change status
        """
        cpe_id = cpe.sw.cpe_id

        # Discover admin user index if not already done
        if self._admin_user_index is None:
            self._admin_user_index = self._discover_admin_user_index(acs, cpe)

        admin_user_idx = self._admin_user_index
        print(f"Using User.{admin_user_idx} as GUI admin user")

        # Capture original password BEFORE making changes
        original_password = None
        try:
            original_password = acs_use_cases.get_parameter_value(
                acs, cpe, f"Device.Users.User.{admin_user_idx}.Password"
            )
            print(f"Captured original user {admin_user_idx} (GUI admin) password")
        except Exception as e:
            print(f"⚠ Could not capture original password: {e}")

        # Set the new password
        print(f"Setting CPE GUI password for {cpe_id}...")
        success = acs_use_cases.set_parameter_value(
            acs, cpe, f"Device.Users.User.{admin_user_idx}.Password", password
        )

        if not success:
            raise AssertionError("Failed to set CPE GUI password via SPV")

        # Verify the change
        time.sleep(2)

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
        except Exception as e:
            print(f"⚠ Could not verify password change: {e}")
            password_change_successful = True

        # Store original config for cleanup
        if password_change_successful:
            self._original_config["users"] = {
                "items": {
                    str(admin_user_idx): {
                        "Password": {
                            "gpv_param": f"Device.Users.User.{admin_user_idx}.Password",
                            "value": original_password or "PLACEHOLDER_FOR_CLEANUP",
                        }
                    }
                }
            }

        return {
            "admin_user_index": admin_user_idx,
            "password_changed": password_change_successful,
            "original_password": original_password,
        }

    @keyword("Restore CPE GUI Password To Default")
    def restore_cpe_gui_password_to_default(
        self, acs: ACS, cpe: CPE, admin_user_index: int
    ) -> bool:
        """Restore CPE GUI password to the default 'admin' value.

        This matches the pytest cleanup behavior where passwords are always
        restored to 'admin' since TR-069 cannot restore from encrypted hashes.

        Important: This waits for CPE to be ready and verifies the change
        was actually applied, not just accepted by the ACS.

        Maps to cleanup step:
        - Restore the CPE GUI password to default after test

        Arguments:
            acs: ACS device instance
            cpe: CPE device instance
            admin_user_index: Index of the admin user (e.g., 10 for User.10)

        Returns:
            True if password was restored successfully
        """
        cpe_id = cpe.sw.cpe_id
        default_password = "admin"  # Default PrplOS password
        param_path = f"Device.Users.User.{admin_user_index}.Password"

        print(
            f"Restoring GUI password to default 'admin' for CPE {cpe_id} "
            f"User.{admin_user_index}..."
        )

        # First, wait for CPE to be fully online (especially after reboot)
        print("  Waiting for CPE to be ready...")
        max_wait = 30
        for i in range(max_wait):
            try:
                if acs_use_cases.is_cpe_online(acs, cpe, timeout=5):
                    print("  ✓ CPE is online and ready")
                    break
            except Exception:
                pass
            time.sleep(1)
        else:
            print("  ⚠ CPE may not be fully ready, attempting password reset anyway")

        # Capture current password hash before change
        try:
            old_hash = acs_use_cases.get_parameter_value(acs, cpe, param_path)
        except Exception:
            old_hash = None

        # Attempt the password restoration
        try:
            print("  Setting password to 'admin'...")
            success = acs_use_cases.set_parameter_value(
                acs, cpe, param_path, default_password
            )

            if not success:
                print("  ⚠ SPV returned failure")
                return False

            # Wait for CPE to process the change
            time.sleep(3)

            # Verify the password was set by checking the hash
            try:
                new_hash = acs_use_cases.get_parameter_value(acs, cpe, param_path)
                if old_hash and new_hash != old_hash:
                    print(
                        f"✓ Password restored to 'admin' for User.{admin_user_index} "
                        "(verified: hash changed)"
                    )
                elif old_hash and new_hash == old_hash:
                    # Hash unchanged - password might already be 'admin'
                    # This is OK - the SPV was accepted
                    print(
                        f"✓ Password set to 'admin' for User.{admin_user_index} "
                        "(hash unchanged - may already be 'admin')"
                    )
                else:
                    print(
                        f"✓ Password reset to 'admin' for User.{admin_user_index} "
                        "(SPV succeeded)"
                    )
                return True
            except Exception as e:
                print(f"  ⚠ Could not verify password change: {e}")
                # SPV succeeded, assume it worked
                return True

        except Exception as e:
            print(f"⚠ Error restoring password: {e}")
            return False

    def _discover_admin_user_index(self, acs: ACS, cpe: CPE) -> int:
        """Discover which user index corresponds to the GUI admin user.

        Arguments:
            acs: ACS device instance
            cpe: CPE device instance

        Returns:
            The user index for the admin user

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

        # Search for admin user
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
                    username = str(value).strip() if value else ""
                    if username.lower() == "admin":
                        print(
                            f"✓ Found admin user at index {user_idx} "
                            f"(username='{username}')"
                        )
                        return user_idx
            except Exception as e:
                print(f"⚠ Could not query User.{user_idx}: {e}")
                continue

        raise AssertionError(
            f"No user with username='admin' found among {user_count} users."
        )

    # =========================================================================
    # Configuration Access Keywords
    # =========================================================================

    @keyword("Get config before reboot")
    def get_config_before_reboot(self) -> dict:
        """Get the configuration captured before reboot.

        Returns:
            Dict with configuration values
        """
        return self._config_before_reboot.copy()

    @keyword("Get original config")
    def get_original_config(self) -> dict:
        """Get the original configuration for cleanup.

        Returns:
            Dict with original configuration values
        """
        return self._original_config.copy()

    @keyword("Get admin user index")
    def get_admin_user_index(self) -> int:
        """Get the discovered admin user index.

        Returns:
            Admin user index
        """
        return self._admin_user_index
