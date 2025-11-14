"""Provisioning and connectivity step definitions."""

import time
from typing import Any

from boardfarm3.templates.acs import ACS as AcsTemplate
from boardfarm3.templates.cpe.cpe import CPE as CpeTemplate
from boardfarm3.templates.wan import WAN as WanTemplate
from pytest_bdd import given, then

from .helpers import gpv_value


@given(
    "the network is configured to prevent the CPE from provisioning after its reboot"
)
def break_provisioning() -> None:
    """Modify the network environment to cause a provisioning failure."""
    pass


@then("the CPE is connected to the ACS")
def cpe_connected_to_acs(acs: AcsTemplate, cpe: CpeTemplate) -> None:
    """Black-box: assert current ACS connectivity by expecting latest BOOT or Periodic inform."""
    cpe_id = cpe.sw.cpe_id
    acs.console.expect(
        f"inform event: (1 BOOT|2 PERIODIC).*(?=.*{cpe_id})",
        timeout=120,
    )


@then("the CPE re-provisions")
def cpe_reprovisions(acs: AcsTemplate, cpe: CpeTemplate) -> None:
    """Observe provisioning completion via ACS-side BOOT + settlement window."""
    cpe_id = cpe.sw.cpe_id
    acs.console.expect(
        f"inform event: 1 BOOT.*{cpe_id}",
        timeout=120,
    )
    time.sleep(5)


@then("internet connectivity for the subscriber is restored")
def internet_connectivity_restored(wan: WanTemplate) -> None:
    """Verify that the CPE has internet connectivity."""
    try:
        wan.console.execute_command("ping -c 3 8.8.8.8")
    except Exception as e:
        raise AssertionError(f"Internet connectivity check failed: {e}")


@then("the CPE fails to provision on the network")
def cpe_fails_to_provision(acs: AcsTemplate, cpe: CpeTemplate) -> None:
    """Black-box: infer provisioning failure from ACS logs/events."""
    cpe_id = cpe.sw.cpe_id
    print("Waiting for provisioning failure to be recorded by ACS...")
    acs.console.expect(
        f"{cpe_id}.*(provision|Provision|CONFIG).*fail|Provisioning failed",
        timeout=180,
    )
    print("ACS recorded provisioning failure for CPE.")


@then("the CPE successfully provisions using the original firmware")
def cpe_provisions_on_original(
    acs: AcsTemplate, cpe: CpeTemplate, bf_context: Any
) -> None:
    """Verify the CPE is online and running the original firmware via the ACS."""
    cpe_id = cpe.sw.cpe_id
    acs.console.expect(
        f"inform event: 1 BOOT.*{cpe_id}",
        timeout=120,
    )
    print("ACS confirmed receipt of final BOOT inform from CPE after rollback.")

    current_version = gpv_value(acs, cpe, "Device.DeviceInfo.SoftwareVersion")
    assert current_version == bf_context.original_firmware, (
        f"Firmware did not roll back to original version. "
        f"Expected: {bf_context.original_firmware}, Got: {current_version}"
    )
    print(f"Verified CPE is running original firmware '{current_version}' via ACS.")

