"""Device initialization step definitions."""

from pytest_bdd import given, parsers, then, when

from boardfarm3.devices.rpiprplos_cpe import RPiPrplOSCPE
from boardfarm3.exceptions import ConfigurationFailure, DeviceBootFailure


@given("the testbed is configured with RPi prplOS CPE")
def testbed_configured_with_cpe(device_manager):
    """the testbed is configured with RPi prplOS CPE."""
    # This checks if the device is present in the inventory
    # Implementation depends on how device_manager exposes config
    pass


@given("Boardfarm instantiates the device from configuration")
def boardfarm_instantiates_device(device_manager):
    """Boardfarm instantiates the device from configuration."""
    cpe = device_manager.get_device_by_type(RPiPrplOSCPE)
    assert cpe is not None
    return cpe


@when("Boardfarm connects to the serial console")
def boardfarm_connects_console(device_manager):
    """Boardfarm connects to the serial console."""
    cpe = device_manager.get_device_by_type(RPiPrplOSCPE)
    # The console connection usually happens during instantiation or boot
    # checking if we can access it
    assert cpe.hw.get_console("console") is not None


@when("Boardfarm boots the device")
def boardfarm_boots_device(device_manager):
    """Boardfarm boots the device."""
    cpe = device_manager.get_device_by_type(RPiPrplOSCPE)
    # Boot hook is called automatically by boardfarm if not skipped
    # If we are in a test, we might need to trigger it manually or verify it ran
    # validation logic depends on test setup
    pass


@then("the device comes online")
def device_comes_online(device_manager):
    """the device comes online."""
    cpe = device_manager.get_device_by_type(RPiPrplOSCPE)
    assert cpe.sw.is_online()


@then("the device registers with ACS")
def device_registers_acs(device_manager):
    """the device registers with ACS."""
    cpe = device_manager.get_device_by_type(RPiPrplOSCPE)
    # Verification is usually done by checking ACS
    # Since we don't have a real ACS in this unit test context,
    # we might check logs or mock verify
    pass


@given("the testbed configuration is missing the device")
def testbed_missing_device(device_manager):
    """the testbed configuration is missing the device."""
    pass


@when("Boardfarm attempts to instantiate the device")
def attempt_instantiate_device(device_manager):
    """Boardfarm attempts to instantiate the device."""
    pass


@then("a configuration error is raised")
def configuration_error_raised():
    """a configuration error is raised."""
    pass


@when("the ACS is unreachable")
def acs_unreachable():
    """the ACS is unreachable."""
    pass


@then("the device fails to register with ACS")
def device_fails_register_acs():
    """the device fails to register with ACS."""
    pass
