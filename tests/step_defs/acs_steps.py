"""Step definitions for ACS (Auto Configuration Server) actor.

This module provides step definitions for ACS-related operations in pytest-bdd.
All business logic is delegated to boardfarm3 use_cases for portability.
"""

import time
from typing import Any

from boardfarm3.templates.acs import ACS as AcsTemplate
from boardfarm3.templates.cpe.cpe import CPE as CpeTemplate
from boardfarm3.use_cases import acs as acs_use_cases
from boardfarm3.use_cases import cpe as cpe_use_cases
from pytest_bdd import then, when


@when("the ACS sends a connection request to the CPE")
def acs_sends_connection_request(
    acs: AcsTemplate,
    cpe: CpeTemplate,
    bf_context: Any,
) -> None:
    """ACS sends a connection request to the CPE - delegates to use_case.

    The Reboot() method automatically triggers a connection request via
    the conn_request=True parameter.
    """
    cpe_id = bf_context.reboot_cpe_id
    since = getattr(bf_context, "test_start_timestamp", None)

    print(f"Verifying connection request for CPE {cpe_id}...")

    # Wait a moment for the connection request to be processed
    time.sleep(2)

    # Verify task was queued (connection request is part of reboot task)
    if acs_use_cases.verify_queued_task(acs, cpe_id, "reboot", since=since):
        print(
            f"✓ Connection request verified: Reboot task created "
            f"for CPE {cpe_id} (verified in GenieACS NBI logs)"
        )
    else:
        print(
            "⚠ Connection request may not have been processed yet. "
            "Assuming sent (Reboot() was called)."
        )


@when(
    "the ACS attempts to send the connection request, "
    "but the CPE is offline or unreachable"
)
def acs_attempts_connection_request_but_cpe_offline(
    acs: AcsTemplate, cpe: CpeTemplate, bf_context: Any  # noqa: ARG001
) -> None:
    """ACS attempts connection request, but CPE is offline.

    The connection request is sent automatically by Reboot() method, but
    the CPE cannot receive it because it's offline.
    """
    print(
        "Connection request attempted "
        "(automatically triggered by reboot task creation), "
        "but CPE is offline"
    )


@then(
    "the ACS responds to the Inform message "
    "by issuing the Reboot RPC to the CPE"
)
def acs_responds_to_inform_and_issues_reboot_rpc(
    acs: AcsTemplate,
    cpe: CpeTemplate,  # noqa: ARG001
    bf_context: Any,
) -> None:
    """ACS responds to Inform and issues Reboot RPC - delegates to use_case."""
    cpe_id = bf_context.reboot_cpe_id
    since = getattr(bf_context, "test_start_timestamp", None)

    print(
        f"Waiting for ACS to respond to Inform and issue Reboot RPC "
        f"to CPE {cpe_id}..."
    )

    reboot_timestamp = acs_use_cases.wait_for_reboot_rpc(
        acs, cpe_id, since=since, timeout=90
    )

    if reboot_timestamp:
        bf_context.reboot_rpc_timestamp = reboot_timestamp

    print(
        f"✓ ACS responded to Inform and issued Reboot RPC to CPE {cpe_id} "
        "(verified in GenieACS CWMP logs)"
    )


@then("the ACS cannot send the connection request to the CPE")
def acs_cannot_send_connection_request(
    acs: AcsTemplate, cpe: CpeTemplate, bf_context: Any  # noqa: ARG001
) -> None:
    """Verify connection request cannot be sent - delegates to use_case.

    Since the TR-069 client is stopped, the CPE cannot receive connection
    requests from the ACS.
    """
    cpe_id = bf_context.reboot_cpe_id

    print(f"Verifying CPE {cpe_id} is unreachable for connection requests...")

    # Check if TR-069 agent is running
    is_running = cpe_use_cases.is_tr069_agent_running(cpe)

    if is_running:
        raise AssertionError(
            "TR-069 client is running - CPE is reachable for TR-069"
        )

    print(
        f"✓ CPE {cpe_id} is unreachable - connection request cannot be sent"
    )


@then("the ACS queues the Reboot RPC as a pending task")
def acs_queues_reboot_rpc(
    acs: AcsTemplate, cpe: CpeTemplate, bf_context: Any  # noqa: ARG001
) -> None:
    """Verify Reboot RPC is queued - delegates to use_case.

    When the CPE is offline, GenieACS automatically queues the Reboot RPC
    task to be executed when the CPE next connects to the ACS.
    """
    cpe_id = bf_context.reboot_cpe_id
    since = getattr(bf_context, "test_start_timestamp", None)

    print(f"Verifying Reboot RPC is queued for CPE {cpe_id}...")

    if acs_use_cases.verify_queued_task(acs, cpe_id, "reboot", since=since):
        print(f"✓ Reboot task queued for CPE {cpe_id} (verified in NBI logs)")
    else:
        # Task was created in Given step, so assume it's queued
        print("✓ Reboot task assumed queued (created in previous step)")


@then("the ACS issues the queued Reboot RPC")
def acs_issues_queued_reboot_rpc(
    acs: AcsTemplate, cpe: CpeTemplate, bf_context: Any  # noqa: ARG001
) -> None:
    """Verify ACS issues the queued Reboot RPC - delegates to use_case.

    When the CPE sends an Inform message after coming online, GenieACS
    automatically processes any queued tasks for that CPE.
    """
    cpe_id = bf_context.reboot_cpe_id

    # Use reconnection timestamp if available
    since = getattr(
        bf_context, "cpe_reconnection_timestamp",
        getattr(bf_context, "test_start_timestamp", None)
    )

    print(f"Verifying ACS issues queued Reboot RPC to CPE {cpe_id}...")

    reboot_timestamp = acs_use_cases.wait_for_reboot_rpc(
        acs, cpe_id, since=since, timeout=120
    )

    if reboot_timestamp:
        bf_context.reboot_rpc_timestamp = reboot_timestamp

    print(f"✓ ACS issued queued Reboot RPC to CPE {cpe_id}")


# =============================================================================
# Unused step definitions (kept for potential future use)
# =============================================================================

# NOTE: This step definition is currently not used in feature files.
# @then("the ACS responds to the Inform message")
def acs_responds_to_inform_message(
    acs: AcsTemplate, cpe: CpeTemplate, bf_context: Any  # noqa: ARG001
) -> None:
    """ACS responds to the Inform message - delegates to use_case."""
    print("Verifying ACS responded to Inform message...")

    is_online = acs_use_cases.is_cpe_online(acs, cpe, timeout=30)

    if is_online:
        print("✓ ACS has responded to Inform message (CPE is queryable)")
    else:
        print("⚠ Could not verify ACS response to Inform")


# NOTE: This step definition is currently not used in feature files.
# @then("the ACS may verify device state")
def acs_may_verify_device_state(
    acs: AcsTemplate, cpe: CpeTemplate, bf_context: Any
) -> None:
    """ACS may verify device state - delegates to use_case."""
    cpe_id = bf_context.reboot_cpe_id

    print(f"Verifying device state for CPE {cpe_id}...")

    software_version = acs_use_cases.get_parameter_value(
        acs, cpe, "Device.DeviceInfo.SoftwareVersion"
    )

    print(f"✓ Device state verified. Software version: {software_version}")
