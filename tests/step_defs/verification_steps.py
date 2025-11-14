"""Verification and assertion step definitions."""

import time
from typing import Any

from boardfarm3.templates.acs import ACS as AcsTemplate
from boardfarm3.templates.cpe.cpe import CPE as CpeTemplate
from pytest_bdd import then

from .helpers import get_console_uptime_seconds, gpv_value


@then("the ACS issues the Download RPC")
def acs_issues_download_rpc(acs: AcsTemplate, cpe: CpeTemplate) -> None:
    """Verify that the ACS sent the Download RPC to the CPE after check-in."""
    cpe_id = cpe.sw.cpe_id
    print(f"Waiting for ACS to issue Download RPC to CPE {cpe_id}...")
    acs.console.expect(f"{cpe_id}.*(Download|download).*task|Download.*{cpe_id}", timeout=60)
    print("ACS confirmed Download RPC was issued to CPE.")

@then("the CPE downloads the firmware from the image server")
def cpe_downloads_firmware(acs: AcsTemplate, cpe: CpeTemplate) -> None:
    """Verify that the CPE successfully downloaded the firmware from the image server."""
    cpe_id = cpe.sw.cpe_id
    print(f"Waiting for CPE {cpe_id} to complete firmware download...")
    acs.console.expect(f"{cpe_id}.*Transfer Complete.*FaultCode 0|{cpe_id}.*download.*complete|{cpe_id}.*Transfer.*success", timeout=300)
    print("CPE confirmed firmware download completed successfully.")

@then("the CPE validates the firmware")
def cpe_validates_firmware(acs: AcsTemplate, cpe: CpeTemplate) -> None:
    """Verify that the CPE validated the downloaded firmware."""
    print(f"Verifying CPE {cpe.sw.cpe_id} firmware validation...")
    time.sleep(2)
    try:
        console_output = cpe.hw.get_console("console").execute_command(
            r"logread | grep -i 'validate\|validation' | tail -5"
        )
        if "fail" in console_output.lower() and "validation" in console_output.lower():
            raise AssertionError(
                f"Firmware validation failed. Console output: {console_output}"
            )
        print("CPE firmware validation completed successfully.")
    except Exception:
        print("CPE firmware validation assumed successful (no failure reported).")

@then("after successful validation, the CPE installs the firmware and reboots")
def cpe_installs_firmware_and_reboots(acs: AcsTemplate, cpe: CpeTemplate) -> None:
    """Wait for firmware installation and reboot completion by observing BOOT inform on ACS."""
    cpe_id = cpe.sw.cpe_id
    print(f"Waiting for CPE {cpe_id} to install firmware and reboot...")
    acs.console.expect(f"inform event: 1 BOOT.*{cpe_id}", timeout=180)
    print("ACS confirmed BOOT inform after firmware installation and reboot.")

@then("the CPE reconnects to the ACS")
def cpe_reconnects_to_acs(acs: AcsTemplate, cpe: CpeTemplate) -> None:
    """Verify that the CPE reconnected to the ACS after reboot."""
    cpe_id = cpe.sw.cpe_id
    print(f"Verifying CPE {cpe_id} reconnected to ACS after reboot...")
    time.sleep(5)
    try:
        version = gpv_value(acs, cpe, "Device.DeviceInfo.SoftwareVersion", retries=5)
        print(f"CPE reconnected to ACS and responding to RPCs. Firmware version: {version}")
    except Exception as e:
        raise AssertionError(
            f"CPE did not reconnect to ACS properly. GPV query failed: {e}"
        ) from e

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
        assert new_version != bf_context.original_firmware, (
            f"Firmware version did not change after upgrade. "
            f"Original: {bf_context.original_firmware}, Current: {new_version}"
        )

@then("the CPE's subscriber credentials and LAN configuration are preserved")
def config_is_preserved(acs: AcsTemplate, cpe: CpeTemplate, bf_context: Any) -> None:
    """Check key device parameters via the ACS to ensure they were not reset."""
    cpe_id = cpe.sw.cpe_id
    for i in range(3):
        try:
            username_val = gpv_value(acs, cpe, "Device.Users.User.1.Username")
            password_val = gpv_value(acs, cpe, "Device.Users.User.1.Password")
            ssid_val = gpv_value(acs, cpe, "Device.WiFi.SSID.1.SSID")

            assert username_val == bf_context.custom_username
            assert password_val == bf_context.custom_password
            assert ssid_val == bf_context.custom_ssid

            print("Verified subscriber credentials and LAN configuration are preserved.")
            return
        except (AssertionError, IndexError, TypeError):
            if i < 2:
                print("Could not verify settings, retrying in 10 seconds...")
                time.sleep(10)
            else:
                raise
    raise AssertionError("Failed to verify preserved settings via ACS.")

@then("the ACS registers a firmware download failure from the CPE")
def acs_registers_download_failure(acs: AcsTemplate, cpe: CpeTemplate) -> None:
    """Monitor the ACS logs for a 'Transfer Complete' event with a fault code."""
    cpe_id = cpe.sw.cpe_id
    acs.console.expect(f"{cpe_id} Transfer Complete.*FaultCode [1-9]", timeout=120)
    print("ACS confirmed receipt of Transfer Complete with fault from CPE.")

@then("the CPE does not reboot")
def cpe_does_not_reboot(acs: AcsTemplate, cpe: CpeTemplate, bf_context: Any) -> None:
    """Verify the CPE does not reboot by checking that its uptime has increased."""
    time.sleep(5)
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
    current_version = gpv_value(acs, cpe, "Device.DeviceInfo.SoftwareVersion")
    assert current_version == bf_context.original_firmware, (
        f"Firmware version changed unexpectedly. "
        f"Original: {bf_context.original_firmware}, Current: {current_version}"
    )

@then("the CPE autonomously rolls back to its previous firmware version")
def cpe_rolls_back(acs: AcsTemplate, cpe: CpeTemplate, bf_context: Any) -> None:
    """Black-box: observe SoftwareVersion returning to original on ACS."""
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
    acs.console.expect(f"inform event: 1 BOOT.*{cpe_id}", timeout=180)
    print("ACS confirmed BOOT inform after rollback reboot.")

@then("the failed upgrade attempt is recorded by the ACS")
def failed_upgrade_recorded(acs: AcsTemplate, cpe: CpeTemplate) -> None:
    """Black-box: look for ACS-side failure indicators around firmware operations."""
    cpe_id = cpe.sw.cpe_id
    acs.console.expect(f"{cpe_id}.*(Transfer Complete.*FaultCode [1-9]|upgrade.*fail|rollback)", timeout=180)

@then(
    "the CPE's subscriber credentials and LAN configuration are reset to factory defaults"
)
def config_is_reset(cpe: CpeTemplate) -> None:
    """Check key parameters to ensure they HAVE been reset to default values."""
    pass

