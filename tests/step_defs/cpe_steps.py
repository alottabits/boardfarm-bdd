"""Step definitions for CPE (Customer Premises Equipment) actor.

This module provides step definitions for CPE-related operations in pytest-bdd.
All business logic is delegated to boardfarm3 use_cases for portability.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from boardfarm3.templates.acs import ACS as AcsTemplate
from boardfarm3.templates.cpe.cpe import CPE as CpeTemplate
from boardfarm3.use_cases import acs as acs_use_cases
from boardfarm3.use_cases import cpe as cpe_use_cases
from pytest_bdd import given, then, when


@when(
    "the CPE receives the connection request "
    "and initiates a session with the ACS"
)
def cpe_receives_connection_request_and_initiates_session(
    acs: AcsTemplate, cpe: CpeTemplate, bf_context: Any  # noqa: ARG001
) -> None:
    """CPE receives connection request and initiates session.

    This happens automatically when the CPE receives the connection request.
    We verify this by waiting for the CPE to send an Inform message, which
    indicates the session has been initiated.
    """
    cpe_id = bf_context.reboot_cpe_id
    print(
        f"Waiting for CPE {cpe_id} to receive connection request "
        "and initiate session..."
    )
    # The actual verification happens in the next step when Inform is sent


@when("the CPE sends an Inform message to the ACS")
@then("the CPE sends an Inform message to the ACS")
def cpe_sends_inform_message(
    acs: AcsTemplate,
    cpe: CpeTemplate,  # noqa: ARG001
    bf_context: Any,
) -> None:
    """CPE sends an Inform message to the ACS - delegates to use_case."""
    cpe_id = bf_context.reboot_cpe_id
    since = getattr(bf_context, "test_start_timestamp", None)

    print(f"Waiting for CPE {cpe_id} to send Inform message...")

    acs_use_cases.wait_for_inform_message(
        acs, cpe_id, since=since, timeout=30
    )

    print(f"✓ CPE {cpe_id} sent Inform message (verified in GenieACS logs)")


@then("the CPE executes the reboot command and restarts")
def cpe_executes_reboot_and_restarts(
    acs: AcsTemplate,  # noqa: ARG001
    cpe: CpeTemplate,
    bf_context: Any,
) -> None:
    """CPE executes the reboot command and restarts - delegates to use_case."""
    cpe_id = bf_context.reboot_cpe_id

    print(f"Verifying CPE {cpe_id} executes reboot and restarts...")

    cpe_use_cases.wait_for_reboot_completion(cpe, timeout=60)

    print(f"✓ CPE {cpe_id} reboot completed")


@then(
    "after completing the boot sequence, the CPE sends an Inform message "
    "to the ACS indicating that the boot sequence has been completed"
)
def cpe_sends_inform_after_boot_completion(
    acs: AcsTemplate,
    cpe: CpeTemplate,
    bf_context: Any,
) -> None:
    """CPE sends Inform after boot completion - delegates to use_case.

    Verifies reboot by checking GenieACS CWMP logs for post-reboot Inform
    message with event codes "1 BOOT" and "M Reboot".
    """
    cpe_id = bf_context.reboot_cpe_id
    since = getattr(bf_context, "test_start_timestamp", None)

    print(
        f"Waiting for CPE {cpe_id} to complete boot and send "
        "post-reboot Inform message..."
    )

    # Wait for boot Inform with reboot event codes
    inform_timestamp = acs_use_cases.wait_for_boot_inform(
        acs, cpe_id, since=since, timeout=240
    )

    print(
        f"✓ CPE {cpe_id} sent post-reboot Inform message at {inform_timestamp} UTC"
    )

    # Refresh console connection after reboot
    print("↻ Refreshing CPE console connection after reboot...")
    if cpe_use_cases.refresh_console_connection(cpe):
        print("✓ Console connection refreshed successfully")
    else:
        print("⚠ Could not refresh console connection")


@then(
    "the CPE resumes normal operation, "
    "continuing periodic communication with the ACS"
)
def cpe_resumes_normal_operation(
    acs: AcsTemplate, cpe: CpeTemplate, bf_context: Any
) -> None:
    """CPE resumes normal operation - delegates to use_case."""
    cpe_id = bf_context.reboot_cpe_id

    print(f"Verifying CPE {cpe_id} has resumed normal operation...")

    is_online = acs_use_cases.is_cpe_online(acs, cpe, timeout=30)

    assert is_online, (
        f"CPE {cpe_id} is not responding, "
        "indicating it has not resumed normal operation"
    )

    print(
        f"✓ CPE {cpe_id} has resumed normal operation "
        "and periodic communication"
    )


@then(
    "the CPE's configuration and operational state "
    "are preserved after reboot"
)
def cpe_configuration_preserved_after_reboot(
    acs: AcsTemplate, cpe: CpeTemplate, bf_context: Any
) -> None:
    """CPE configuration preserved after reboot - delegates to use_case."""
    cpe_id = bf_context.reboot_cpe_id

    print(f"Verifying configuration preservation for CPE {cpe_id}...")

    config_before = getattr(bf_context, "config_before_reboot", {})
    if not config_before:
        print(
            "⚠ Configuration was not captured before reboot. "
            "Skipping detailed verification."
        )
        # Fall back to basic online check
        is_online = acs_use_cases.is_cpe_online(acs, cpe, timeout=30)
        assert is_online, f"CPE {cpe_id} is not responding"
        print(f"✓ CPE {cpe_id} is online (basic verification)")
        return

    verification_errors = cpe_use_cases.verify_config_preservation(
        cpe, acs, config_before
    )

    if verification_errors:
        error_msg = (
            "Configuration was not fully preserved after reboot:\n"
            + "\n".join(f"  - {error}" for error in verification_errors)
        )
        raise AssertionError(error_msg)

    print("✓ All configuration parameters preserved after reboot")


@then("the CPE does not reboot")
def cpe_does_not_reboot(
    acs: AcsTemplate, cpe: CpeTemplate, bf_context: Any  # noqa: ARG001
) -> None:
    """Verify the CPE does not reboot - delegates to use_case."""
    import time
    time.sleep(5)

    current_uptime = cpe_use_cases.get_console_uptime_seconds(cpe)

    assert bf_context.initial_uptime, (
        "Initial uptime was not set in a previous step"
    )
    assert current_uptime > bf_context.initial_uptime, (
        f"CPE appears to have rebooted. "
        f"Initial uptime: {bf_context.initial_uptime}, "
        f"Current uptime: {current_uptime}"
    )

    print(
        f"✓ Verified that CPE did not reboot. "
        f"Uptime increased from {bf_context.initial_uptime} to {current_uptime}."
    )


@given("the CPE is unreachable for TR-069 sessions")
def cpe_is_unreachable_for_tr069(
    acs: AcsTemplate, cpe: CpeTemplate, bf_context: Any  # noqa: ARG001
) -> None:
    """Make CPE unreachable for TR-069 sessions - delegates to use_case."""
    # Get CPE ID and store in context
    cpe_id = cpe.sw.cpe_id
    bf_context.reboot_cpe_id = cpe_id

    # Record test start timestamp for filtering logs
    bf_context.test_start_timestamp = (
        datetime.now(timezone.utc) - timedelta(seconds=5)
    ).replace(tzinfo=None)

    print(f"Making CPE {cpe_id} unreachable for TR-069 sessions...")

    cpe_use_cases.stop_tr069_client(cpe)

    print(
        f"✓ CPE {cpe_id} is unreachable for TR-069 sessions "
        "(cwmp_plugin stopped)"
    )
    bf_context.cpe_was_taken_offline = True
    bf_context.cpe_offline_timestamp = (
        datetime.now(timezone.utc).replace(tzinfo=None)
    )


@then("when the CPE comes online, it connects to the ACS")
def cpe_comes_online_and_connects(
    acs: AcsTemplate, cpe: CpeTemplate, bf_context: Any
) -> None:
    """Bring CPE back online and wait for ACS connection - delegates to use_case."""
    cpe_id = bf_context.reboot_cpe_id
    offline_timestamp = getattr(bf_context, "cpe_offline_timestamp", None)

    print(f"Bringing CPE {cpe_id} back online...")

    # Start TR-069 client
    cpe_use_cases.start_tr069_client(cpe)
    print(f"✓ CPE {cpe_id} TR-069 client restarted")

    # Wait for CPE to connect to ACS
    print(f"Waiting for CPE {cpe_id} to connect to ACS...")

    acs_use_cases.wait_for_inform_message(
        acs,
        cpe_id,
        event_codes=["1 BOOT"],
        since=offline_timestamp,
        timeout=120,
    )

    bf_context.cpe_reconnection_timestamp = (
        datetime.now(timezone.utc).replace(tzinfo=None)
    )
    print(f"✓ CPE {cpe_id} reconnected to ACS")


# =============================================================================
# Unused step definitions (kept for potential future use)
# =============================================================================

# NOTE: This step definition is currently not used in feature files.
# It was removed from scenarios because verification relies on proxy logs.
# @then("the CPE receives and acknowledges the Reboot RPC")
def cpe_receives_and_acknowledges_reboot_rpc(
    acs: AcsTemplate,
    cpe: CpeTemplate,
    bf_context: Any,
) -> None:
    """CPE receives and acknowledges the Reboot RPC - delegates to use_case.

    NOTE: This step is currently unused. It relies on proxy logs which
    require docker exec access.
    """
    cpe_id = bf_context.reboot_cpe_id
    since = getattr(bf_context, "test_start_timestamp", None)

    print(
        f"Waiting for CPE {cpe_id} to receive and acknowledge Reboot RPC..."
    )

    # Record uptime before reboot
    try:
        bf_context.uptime_before_reboot = cpe_use_cases.get_console_uptime_seconds(cpe)
        print(f"Uptime before reboot: {bf_context.uptime_before_reboot}s")
    except Exception as e:  # noqa: BLE001
        print(f"⚠ Could not get CPE uptime before reboot: {e}")
        bf_context.uptime_before_reboot = 0

    # Wait for Reboot RPC in ACS logs
    reboot_timestamp = acs_use_cases.wait_for_reboot_rpc(
        acs, cpe_id, since=since, timeout=120
    )

    if reboot_timestamp:
        bf_context.reboot_rpc_timestamp = reboot_timestamp

    print(f"✓ CPE {cpe_id} received and acknowledged Reboot RPC")
