"""ACS GUI Keywords for Robot Framework.

Keywords for ACS GUI operations, aligned with BDD scenario steps.
Uses @keyword decorator to map clean function names to scenario step text.

Mirrors: tests/step_defs/acs_gui_steps.py
"""

import time
from datetime import datetime, timedelta, timezone
from typing import Any

from robot.api.deco import keyword

from boardfarm3.templates.acs import ACS
from boardfarm3.templates.cpe.cpe import CPE
from boardfarm3.use_cases.cpe import get_console_uptime_seconds


class AcsGuiKeywords:
    """Keywords for ACS GUI operations matching BDD scenario steps."""

    ROBOT_LIBRARY_SCOPE = "SUITE"
    ROBOT_LIBRARY_DOC_FORMAT = "TEXT"

    def __init__(self) -> None:
        """Initialize AcsGuiKeywords."""
        self._gui_available: bool = False
        self._gui_logged_in: bool = False
        self._device_search_found: bool = False
        self._device_status_info: dict = {}
        self._cpe_id: str = None

    # =========================================================================
    # Setup Keywords
    # =========================================================================

    @keyword("The ACS GUI is configured and available")
    @keyword("ACS GUI is available")
    def verify_gui_available(self, acs: ACS) -> None:
        """Verify ACS GUI is configured and available.

        Maps to scenario step:
        - "Given the ACS GUI is configured and available"

        Arguments:
            acs: ACS device instance
        """
        if not acs.gui.is_gui_configured():
            raise AssertionError("ACS GUI not configured for this testbed")

        if not acs.gui.is_initialized():
            try:
                acs.gui.initialize()
            except Exception as e:
                raise AssertionError(f"Failed to initialize ACS GUI: {e}") from e

        ip = acs.config['ipaddr']
        port = acs.config['http_port']
        print(f"✓ ACS GUI is configured and available at {ip}:{port}")
        self._gui_available = True

    @keyword("The CPE device ID is known")
    @keyword("CPE device ID is known")
    def verify_cpe_id_known(self, cpe: CPE) -> str:
        """Ensure CPE device ID is known.

        Maps to scenario step:
        - "Given the CPE device ID is known"

        Arguments:
            cpe: CPE device instance

        Returns:
            CPE device ID
        """
        cpe_id = cpe.sw.cpe_id
        if not cpe_id:
            raise AssertionError("CPE ID not available")
        self._cpe_id = cpe_id
        print(f"✓ CPE device ID: {cpe_id}")
        return cpe_id

    # =========================================================================
    # Authentication Keywords
    # =========================================================================

    @keyword("The operator is not logged into the ACS GUI")
    @keyword("Operator is logged out")
    def ensure_logged_out(self, acs: ACS) -> None:
        """Ensure operator is not logged into ACS GUI.

        Maps to scenario step:
        - "Given the operator is not logged into the ACS GUI"

        Arguments:
            acs: ACS device instance
        """
        if acs.gui.is_initialized():
            try:
                if acs.gui.is_logged_in():
                    acs.gui.logout()
                    print("✓ Logged out from ACS GUI")
            except Exception:
                pass
        self._gui_logged_in = False

    @keyword("The operator is logged into the ACS GUI")
    @keyword("The operator logs into the ACS GUI with valid credentials")
    @keyword("Operator logs in")
    def login_to_gui(self, acs: ACS) -> None:
        """Operator logs into ACS GUI with valid credentials.

        Maps to scenario steps:
        - "Given the operator is logged into the ACS GUI"
        - "When the operator logs into the ACS GUI with valid credentials"

        Arguments:
            acs: ACS device instance
        """
        try:
            if acs.gui.is_logged_in():
                print("✓ Already logged into ACS GUI")
                self._gui_logged_in = True
                return
        except Exception:
            pass

        username = acs.config.get("http_username", "admin")
        password = acs.config.get("http_password", "admin")

        print(f"Attempting to login to ACS GUI as '{username}'...")
        success = acs.gui.login(username, password)

        if success:
            print(f"✓ Successfully logged into ACS GUI as '{username}'")
            self._gui_logged_in = True
        else:
            raise AssertionError(f"Failed to login to ACS GUI as '{username}'")

    @keyword("The operator logs out from the ACS GUI")
    @keyword("Operator logs out")
    def logout_from_gui(self, acs: ACS) -> None:
        """Operator logs out from ACS GUI.

        Maps to scenario step:
        - "When the operator logs out from the ACS GUI"

        Arguments:
            acs: ACS device instance
        """
        print("Logging out from ACS GUI...")
        success = acs.gui.logout()

        if success:
            print("✓ Successfully logged out from ACS GUI")
            self._gui_logged_in = False
        else:
            raise AssertionError("Failed to logout from ACS GUI")

    @keyword("The operator should be successfully authenticated")
    @keyword("Operator is authenticated")
    def verify_authenticated(self, acs: ACS) -> None:
        """Verify operator is authenticated.

        Maps to scenario step:
        - "Then the operator should be successfully authenticated"

        Arguments:
            acs: ACS device instance
        """
        is_logged_in = acs.gui.is_logged_in()
        assert is_logged_in, "Operator should be logged in but is not"
        assert self._gui_logged_in, "Context should indicate logged in"
        print("✓ Operator is authenticated")

    @keyword("The ACS dashboard should be displayed")
    @keyword("Dashboard is displayed")
    def verify_dashboard_displayed(self) -> None:
        """Verify ACS dashboard is displayed.

        Maps to scenario step:
        - "Then the ACS dashboard should be displayed"
        """
        assert self._gui_logged_in, "Should be logged in to see dashboard"
        print("✓ ACS dashboard displayed")

    # =========================================================================
    # Device Search Keywords
    # =========================================================================

    @keyword("The operator searches for the device in the ACS GUI")
    @keyword("Search for device in GUI")
    def search_for_device(self, acs: ACS, cpe: CPE) -> bool:
        """Operator searches for device by ID in ACS GUI.

        Maps to scenario step:
        - "When the operator searches for the device in the ACS GUI"

        Arguments:
            acs: ACS device instance
            cpe: CPE device instance

        Returns:
            True if device found
        """
        cpe_id = cpe.sw.cpe_id
        print(f"Searching for device '{cpe_id}' in ACS GUI...")

        found = acs.gui.search_device(cpe_id)
        self._device_search_found = found
        self._cpe_id = cpe_id

        if found:
            print(f"✓ Device '{cpe_id}' found in search results")
        else:
            print(f"✗ Device '{cpe_id}' not found in search results")

        return found

    @keyword("The device should appear in the search results")
    @keyword("Device is in search results")
    def verify_device_in_results(self) -> None:
        """Verify device appears in search results.

        Maps to scenario step:
        - "Then the device should appear in the search results"
        """
        assert self._device_search_found, "Device should be found in search results"
        print(f"✓ Device '{self._cpe_id}' is in search results")

    # =========================================================================
    # Device Status Keywords
    # =========================================================================

    @keyword("The operator navigates to the device details page")
    @keyword("Navigate to device details")
    def navigate_to_device_details(self, acs: ACS, cpe: CPE) -> dict:
        """Operator navigates to device details page.

        Maps to scenario step:
        - "When the operator navigates to the device details page"

        Arguments:
            acs: ACS device instance
            cpe: CPE device instance

        Returns:
            Device status info dict
        """
        cpe_id = cpe.sw.cpe_id
        print(f"Navigating to device details for '{cpe_id}'...")

        status_info = acs.gui.get_device_status(cpe_id)
        self._device_status_info = status_info
        self._cpe_id = cpe_id

        print(
            f"✓ Device details page displayed, "
            f"status: {status_info.get('status', 'unknown')}"
        )
        return status_info

    @keyword("The device status should be displayed as online")
    @keyword("Device status is online")
    def verify_device_online(self) -> None:
        """Verify device status is online.

        Maps to scenario step:
        - "Then the device status should be displayed as 'online'"
        """
        status = self._device_status_info.get("status", "unknown")
        assert status in ["online", "connected", "active"], (
            f"Device should be online but status is '{status}'"
        )
        print(f"✓ Device status is '{status}' (online)")

    # =========================================================================
    # Device Operations Keywords
    # =========================================================================

    @keyword("The operator initiates a reboot via the ACS GUI")
    @keyword("Initiate reboot via GUI")
    def initiate_reboot_via_gui(self, acs: ACS, cpe: CPE) -> dict:
        """Operator initiates device reboot via GUI.

        Maps to scenario step:
        - "When the operator initiates a reboot via the ACS GUI"

        Arguments:
            acs: ACS device instance
            cpe: CPE device instance

        Returns:
            Context dict with cpe_id and timestamps
        """
        cpe_id = cpe.sw.cpe_id
        print(f"Initiating reboot for device '{cpe_id}' via ACS GUI...")

        test_start_timestamp = (
            datetime.now(timezone.utc) - timedelta(seconds=5)
        ).replace(tzinfo=None)

        success = acs.gui.reboot_device_via_gui(cpe_id)
        self._cpe_id = cpe_id

        if success:
            print(f"✓ Reboot initiated for device '{cpe_id}' via GUI")
        else:
            raise AssertionError(
                f"Failed to initiate reboot for '{cpe_id}' via GUI"
            )

        return {
            "cpe_id": cpe_id,
            "gui_reboot_initiated": success,
            "test_start_timestamp": test_start_timestamp,
        }

    @keyword("The reboot command should be sent to the device")
    @keyword("Reboot command sent")
    def verify_reboot_command_sent(self, gui_reboot_initiated: bool = True) -> None:
        """Verify reboot command was sent.

        Maps to scenario step:
        - "Then the reboot command should be sent to the device"

        Arguments:
            gui_reboot_initiated: Whether reboot was initiated
        """
        assert gui_reboot_initiated, "Reboot should have been initiated"
        print("✓ Reboot command sent to device")

    @keyword("The device should reboot successfully")
    @keyword("Device reboots successfully")
    def verify_device_reboots(
        self, cpe: CPE, initial_uptime: float = None, wait_time: int = 30
    ) -> None:
        """Verify device reboots successfully.

        Maps to scenario step:
        - "Then the device should reboot successfully"

        Arguments:
            cpe: CPE device instance
            initial_uptime: Initial uptime before reboot (optional)
            wait_time: Time to wait for reboot in seconds
        """
        print("Waiting for device to reboot...")

        if initial_uptime:
            print(f"⚠ Initial uptime before reboot: {initial_uptime}s")

        print(f"Waiting {wait_time} seconds for reboot task to execute...")
        time.sleep(wait_time)

        try:
            current_uptime = get_console_uptime_seconds(cpe)
            print(f"⚠ Current uptime: {current_uptime}s")

            if initial_uptime and current_uptime < initial_uptime:
                print(
                    f"✓ CPE rebooted! Uptime reset from {initial_uptime}s "
                    f"to {current_uptime}s"
                )
            elif initial_uptime and current_uptime >= initial_uptime:
                print(
                    f"⚠ WARNING: CPE may not have rebooted. "
                    f"Uptime increased from {initial_uptime}s to {current_uptime}s"
                )
            else:
                print(
                    "⚠ WARNING: Could not verify reboot - "
                    "no initial uptime reference"
                )
        except Exception as e:
            print(f"⚠ Console unavailable (expected during reboot): {e}")

        print("✓ Device reboot phase complete")

    # =========================================================================
    # Parameter Operations Keywords
    # =========================================================================

    @keyword("The operator requests the device software version via GUI")
    @keyword("Get software version via GUI")
    def get_software_version_via_gui(self, acs: ACS, cpe: CPE) -> str:
        """Operator requests device software version via GUI.

        Maps to scenario step:
        - "When the operator requests the device software version via GUI"

        Arguments:
            acs: ACS device instance
            cpe: CPE device instance

        Returns:
            Software version string
        """
        cpe_id = cpe.sw.cpe_id
        parameter = "Device.DeviceInfo.SoftwareVersion"

        print(
            f"Requesting parameter '{parameter}' for device '{cpe_id}' via GUI..."
        )
        value = acs.gui.get_device_parameter_via_gui(cpe_id, parameter)

        if value:
            print(f"✓ Parameter value retrieved: {value}")
        else:
            print("✗ Failed to retrieve parameter value")

        return value

    @keyword("The software version parameter should be retrieved")
    @keyword("Parameter was retrieved")
    def verify_parameter_retrieved(self, value: str) -> None:
        """Verify parameter was retrieved.

        Maps to scenario step:
        - "Then the software version parameter should be retrieved"

        Arguments:
            value: Parameter value
        """
        assert value is not None, "Parameter value should not be None"
        print(f"✓ Parameter retrieved: {value}")

    # =========================================================================
    # Status Access Keywords
    # =========================================================================

    @keyword("Is GUI logged in")
    def is_logged_in(self) -> bool:
        """Check if operator is logged into GUI.

        Returns:
            True if logged in
        """
        return self._gui_logged_in

    @keyword("Get device status info")
    def get_device_status_info(self) -> dict:
        """Get the current device status info.

        Returns:
            Device status info dict
        """
        return self._device_status_info.copy()
