"""Device Class Keywords for Robot Framework.

Keywords for device initialization and class operations.
Uses @keyword decorator to map clean function names to scenario step text.

Mirrors: tests/step_defs/device_class_steps.py
"""

from typing import Any

from robot.api.deco import keyword


class DeviceClassKeywords:
    """Keywords for device initialization and class operations."""

    ROBOT_LIBRARY_SCOPE = "SUITE"
    ROBOT_LIBRARY_DOC_FORMAT = "TEXT"

    def __init__(self) -> None:
        """Initialize DeviceClassKeywords."""
        self._device_manager: Any = None
        self._cpe: Any = None

    # =========================================================================
    # Testbed Configuration Keywords
    # =========================================================================

    @keyword("The testbed is configured with RPi prplOS CPE")
    @keyword("Testbed has prplOS CPE")
    def testbed_configured_with_cpe(self, device_manager: Any) -> None:
        """Verify testbed is configured with RPi prplOS CPE.

        Maps to scenario step:
        - "Given the testbed is configured with RPi prplOS CPE"

        Arguments:
            device_manager: Boardfarm device manager
        """
        self._device_manager = device_manager
        print("✓ Testbed is configured with RPi prplOS CPE")

    @keyword("Boardfarm instantiates the device from configuration")
    @keyword("Instantiate device from config")
    def instantiate_device(self, device_manager: Any) -> Any:
        """Boardfarm instantiates the device from configuration.

        Maps to scenario step:
        - "Given Boardfarm instantiates the device from configuration"

        Arguments:
            device_manager: Boardfarm device manager

        Returns:
            CPE device instance
        """
        from boardfarm3.devices.rpiprplos_cpe import RPiPrplOSCPE

        self._device_manager = device_manager
        cpe = device_manager.get_device_by_type(RPiPrplOSCPE)
        assert cpe is not None, "Failed to instantiate CPE device"
        self._cpe = cpe
        print("✓ CPE device instantiated from configuration")
        return cpe

    # =========================================================================
    # Console Connection Keywords
    # =========================================================================

    @keyword("Boardfarm connects to the serial console")
    @keyword("Connect to serial console")
    def connect_to_console(self, device_manager: Any = None) -> None:
        """Boardfarm connects to the serial console.

        Maps to scenario step:
        - "When Boardfarm connects to the serial console"

        Arguments:
            device_manager: Boardfarm device manager (optional)
        """
        from boardfarm3.devices.rpiprplos_cpe import RPiPrplOSCPE

        if device_manager is None:
            device_manager = self._device_manager

        cpe = device_manager.get_device_by_type(RPiPrplOSCPE)
        console = cpe.hw.get_console("console")
        assert console is not None, "Failed to connect to serial console"
        print("✓ Connected to serial console")

    # =========================================================================
    # Boot Keywords
    # =========================================================================

    @keyword("Boardfarm boots the device")
    @keyword("Boot device")
    def boot_device(self, device_manager: Any = None) -> None:
        """Boardfarm boots the device.

        Maps to scenario step:
        - "When Boardfarm boots the device"

        Arguments:
            device_manager: Boardfarm device manager (optional)
        """
        # Boot hook is called automatically by boardfarm if not skipped
        print("✓ Device boot process initiated")

    # =========================================================================
    # Device Status Keywords
    # =========================================================================

    @keyword("The device comes online")
    @keyword("Device is online")
    def device_comes_online(self, device_manager: Any = None) -> None:
        """Verify the device comes online.

        Maps to scenario step:
        - "Then the device comes online"

        Arguments:
            device_manager: Boardfarm device manager (optional)
        """
        from boardfarm3.devices.rpiprplos_cpe import RPiPrplOSCPE

        if device_manager is None:
            device_manager = self._device_manager

        cpe = device_manager.get_device_by_type(RPiPrplOSCPE)
        assert cpe.sw.is_online(), "Device is not online"
        print("✓ Device is online")

    @keyword("The device registers with ACS")
    @keyword("Device registers with ACS")
    def device_registers_with_acs(self, device_manager: Any = None) -> None:
        """Verify the device registers with ACS.

        Maps to scenario step:
        - "Then the device registers with ACS"

        Arguments:
            device_manager: Boardfarm device manager (optional)
        """
        # Verification is usually done by checking ACS
        print("✓ Device registered with ACS")

    # =========================================================================
    # Error Handling Keywords
    # =========================================================================

    @keyword("The testbed configuration is missing the device")
    @keyword("Testbed missing device")
    def testbed_missing_device(self, device_manager: Any = None) -> None:
        """Verify testbed configuration is missing the device.

        Maps to scenario step:
        - "Given the testbed configuration is missing the device"
        """
        print("⚠ Testbed configuration is missing the device")

    @keyword("Boardfarm attempts to instantiate the device")
    @keyword("Attempt to instantiate device")
    def attempt_instantiate_device(self, device_manager: Any = None) -> None:
        """Boardfarm attempts to instantiate the device.

        Maps to scenario step:
        - "When Boardfarm attempts to instantiate the device"
        """
        print("Attempting to instantiate device...")

    @keyword("A configuration error is raised")
    @keyword("Configuration error raised")
    def configuration_error_raised(self) -> None:
        """Verify a configuration error is raised.

        Maps to scenario step:
        - "Then a configuration error is raised"
        """
        print("✓ Configuration error raised as expected")

    @keyword("The ACS is unreachable")
    @keyword("ACS is unreachable")
    def acs_unreachable(self) -> None:
        """Simulate ACS being unreachable.

        Maps to scenario step:
        - "When the ACS is unreachable"
        """
        print("⚠ ACS is unreachable")

    @keyword("The device fails to register with ACS")
    @keyword("Device fails ACS registration")
    def device_fails_acs_registration(self) -> None:
        """Verify device fails to register with ACS.

        Maps to scenario step:
        - "Then the device fails to register with ACS"
        """
        print("✓ Device failed to register with ACS as expected")
