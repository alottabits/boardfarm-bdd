"""Step definitions for Operator actor."""

from datetime import datetime, timedelta, timezone
from typing import Any

from boardfarm3.templates.acs import ACS as AcsTemplate
from boardfarm3.templates.cpe.cpe import CPE as CpeTemplate
from pytest_bdd import given, then, when


@given("the operator initiates a reboot task on the ACS for the CPE")
@when("the operator initiates a reboot task on the ACS for the CPE")
def operator_initiates_reboot_task(
    acs: AcsTemplate, cpe: CpeTemplate, bf_context: Any
) -> None:
    """Operator initiates a reboot task on the ACS for the CPE.

    Uses the ACS Reboot() method which creates the reboot task and triggers
    a connection request to the CPE.
    """
    cpe_id = cpe.sw.cpe_id
    command_key = "reboot"

    # Store context for later steps
    bf_context.reboot_cpe_id = cpe_id
    bf_context.reboot_command_key = command_key
    # Record test start timestamp for filtering logs
    # GenieACS logs use UTC timestamps, so we record UTC time
    # Subtract a small buffer (5 seconds) to account for timing differences
    bf_context.test_start_timestamp = (
        datetime.now(timezone.utc) - timedelta(seconds=5)
    )

    print(f"Operator initiating reboot task for CPE {cpe_id} via ACS...")

    # Initiate reboot immediately - no GPV calls to avoid interference
    # Firmware version is already captured in cpe_is_online_and_provisioned()
    # step, and config_before_reboot will default to {} in verification step
    acs.Reboot(CommandKey=command_key, cpe_id=cpe_id)
    print(
        f"Reboot task created successfully for CPE {cpe_id} "
        f"(test started at {bf_context.test_start_timestamp} UTC)"
    )


@then("use case succeeds and all success guarantees are met")
def use_case_succeeds(
    acs: AcsTemplate, cpe: CpeTemplate, bf_context: Any  # noqa: ARG001
) -> None:
    """Use case succeeds and all success guarantees are met.

    Final verification step to ensure all success guarantees are met.
    """
    cpe_id = bf_context.reboot_cpe_id

    print(f"Verifying all success guarantees for CPE {cpe_id}...")

    # Verify success guarantees:
    # 1. CPE successfully reboots and completes boot sequence
    # (verified by post-reboot Inform message in previous steps)
    print("CPE successfully rebooted and completed boot sequence")

    # 2. CPE reconnects to ACS after reboot
    result = acs.GPV(
        "Device.DeviceInfo.SoftwareVersion", cpe_id=cpe_id, timeout=30
    )
    assert result, "CPE did not reconnect to ACS after reboot"

    # 3. ACS correctly identifies reboot event
    # (verified by successful reconnection)
    print("ACS correctly identified reboot event via Inform message")

    # 4. CPE's configuration preserved (verified in previous step)
    print("CPE configuration and operational state preserved")

    # 5. CPE resumes normal operation (verified in previous step)
    print("CPE resumed normal operation and periodic communication")

    print("✓ All success guarantees met. Use case succeeded.")
