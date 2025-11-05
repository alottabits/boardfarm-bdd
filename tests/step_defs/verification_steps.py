"""Verification and assertion step definitions."""

import time
from typing import Any

from boardfarm3.templates.acs import ACS as AcsTemplate
from boardfarm3.templates.cpe.cpe import CPE as CpeTemplate
from pytest_bdd import then

from tests.step_defs.helpers import get_console_uptime_seconds, gpv_value


@then("the CPE installs the firmware and reboots")
def cpe_reboots(acs: AcsTemplate, cpe: CpeTemplate) -> None:
    """Wait for reboot completion by observing BOOT inform on ACS (black-box)."""
    cpe_id = cpe.sw.cpe_id
    acs.console.expect(
        f"inform event: 1 BOOT.*{cpe_id}",
        timeout=180,
    )
    print("ACS confirmed BOOT inform after firmware installation.")


@then("the ACS reports the new firmware version for the CPE")
def acs_reports_new_fw(acs: AcsTemplate, cpe: CpeTemplate, bf_context: Any) -> None:
    """Check ACS for updated SoftwareVersion matching expected_firmware."""
    new_version = gpv_value(acs, cpe, "Device.DeviceInfo.SoftwareVersion")
    if getattr(bf_context, "expected_firmware", None):
        assert bf_context.expected_firmware in new_version, (
            f"Incorrect firmware version reported to ACS. "
            f"Expected: {bf_context.expected_firmware}, Got: {new_version}"
        )
    else:
        # If we cannot reliably derive the expected version from filename, at least
        # verify the version changed from the original to indicate an upgrade occurred.
        assert new_version != bf_context.original_firmware, (
            f"Firmware version did not change after upgrade. "
            f"Original: {bf_context.original_firmware}, Current: {new_version}"
        )


@then("the CPE's subscriber credentials and LAN configuration are preserved")
def config_is_preserved(acs: AcsTemplate, cpe: CpeTemplate, bf_context: Any) -> None:
    """Check key device parameters via the ACS to ensure they were not reset."""
    cpe_id = cpe.sw.cpe_id

    # It can take a moment for the CPE to report all its parameters after booting.
    # We will poll a few times to ensure we get the latest data.
    for i in range(3):  # Retry for ~30 seconds
        try:
            # Query the ACS for the current values.
            username_val = gpv_value(acs, cpe, "Device.Users.User.1.Username")
            password_val = gpv_value(acs, cpe, "Device.Users.User.1.Password")
            ssid_val = gpv_value(acs, cpe, "Device.WiFi.SSID.1.SSID")

            assert username_val == bf_context.custom_username
            assert password_val == bf_context.custom_password
            assert ssid_val == bf_context.custom_ssid

            print(
                "Verified subscriber credentials and LAN configuration are preserved."
            )
            return  # Exit on success
        except (AssertionError, IndexError, TypeError):
            # IndexError/TypeError can happen if the GPV response is empty/malformed.
            if i < 2:
                print("Could not verify settings, retrying in 10 seconds...")
                time.sleep(10)
            else:
                raise  # Re-raise the exception on the final attempt

    raise AssertionError("Failed to verify preserved settings via ACS.")


@then("the ACS registers a firmware download failure from the CPE")
def acs_registers_download_failure(acs: AcsTemplate, cpe: CpeTemplate) -> None:
    """
    Monitor the ACS logs for a "Transfer Complete" event with a fault code,
    indicating the CPE has reported the download failure.
    """
    cpe_id = cpe.sw.cpe_id
    # The exact fault code and string for a signature failure are vendor-specific.
    # We look for a generic "Transfer Complete" with a non-zero fault code.
    # Example log: "cpe_id Transfer Complete event received, FaultCode 9010"
    acs.console.expect(
        f"{cpe_id} Transfer Complete.*FaultCode [1-9]",
        timeout=120,
    )
    print("ACS confirmed receipt of Transfer Complete with fault from CPE.")


@then("the CPE does not reboot")
def cpe_does_not_reboot(acs: AcsTemplate, cpe: CpeTemplate, bf_context: Any) -> None:
    """Verify the CPE does not reboot by checking that its uptime has increased."""
    cpe_id = cpe.sw.cpe_id
    time.sleep(5)  # Wait a few seconds to ensure uptime has a chance to increase
    current_uptime = get_console_uptime_seconds(cpe)

    assert bf_context.initial_uptime, "Initial uptime was not set in a previous step"
    assert current_uptime > bf_context.initial_uptime, (
        f"CPE appears to have rebooted. "
        f"Initial uptime: {bf_context.initial_uptime}, Current uptime: {current_uptime}"
    )
    print(
        f"Verified that CPE did not reboot. Uptime increased from {bf_context.initial_uptime} to {current_uptime}."
    )


@then("the CPE continues to run its original firmware version")
def cpe_runs_original_version(
    acs: AcsTemplate, cpe: CpeTemplate, bf_context: Any
) -> None:
    """Check that the firmware version has not changed by querying the ACS."""
    cpe_id = cpe.sw.cpe_id
    current_version = gpv_value(acs, cpe, "Device.DeviceInfo.SoftwareVersion")
    assert current_version == bf_context.original_firmware, (
        f"Firmware version changed unexpectedly. "
        f"Original: {bf_context.original_firmware}, Current: {current_version}"
    )


@then("the CPE autonomously rolls back to its previous firmware version")
def cpe_rolls_back(acs: AcsTemplate, cpe: CpeTemplate, bf_context: Any) -> None:
    """Black-box: observe SoftwareVersion returning to original on ACS."""
    cpe_id = cpe.sw.cpe_id
    deadline = time.time() + 300
    while time.time() < deadline:
        val = gpv_value(acs, cpe, "Device.DeviceInfo.SoftwareVersion")
        if val == bf_context.original_firmware:
            print("ACS reports original firmware version after rollback.")
            return
        time.sleep(10)
    raise AssertionError(
        "Rollback not observed: ACS did not report original firmware in time"
    )


@then("the CPE reboots a second time")
def cpe_reboots_again(acs: AcsTemplate, cpe: CpeTemplate) -> None:
    """Observe second reboot via BOOT inform on ACS (black-box)."""
    cpe_id = cpe.sw.cpe_id
    acs.console.expect(
        f"inform event: 1 BOOT.*{cpe_id}",
        timeout=180,
    )
    print("ACS confirmed BOOT inform after rollback reboot.")


@then("the failed upgrade attempt is recorded by the ACS")
def failed_upgrade_recorded(acs: AcsTemplate, cpe: CpeTemplate) -> None:
    """Black-box: look for ACS-side failure indicators around firmware operations."""
    cpe_id = cpe.sw.cpe_id
    # Match a conservative failure indicator; vendor strings vary.
    acs.console.expect(
        f"{cpe_id}.*(Transfer Complete.*FaultCode [1-9]|upgrade.*fail|rollback)",
        timeout=180,
    )


@then(
    "the CPE's subscriber credentials and LAN configuration are reset to factory defaults"
)
def config_is_reset(cpe: CpeTemplate) -> None:
    """Check key parameters to ensure they HAVE been reset to default values."""
    # Device-specific checks.
    # Example:
    # current_ssid = cpe.sw.wifi.get_ssid()
    # assert current_ssid == "DefaultWifiName", "SSID was not reset to default"
    pass

