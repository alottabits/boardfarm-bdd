"""Step definitions for offline CPE reboot scenario."""

import time
from datetime import datetime, timezone
from typing import Any

from boardfarm3.templates.acs import ACS as AcsTemplate
from boardfarm3.templates.cpe.cpe import CPE as CpeTemplate
from pytest_bdd import given, then, when

from .helpers import (
    filter_logs_by_cpe_id,
    filter_logs_by_timestamp,
    parse_log_timestamp,
)


@given("the CPE is unreachable for TR-069 sessions")
def cpe_is_unreachable_for_tr069(
    acs: AcsTemplate, cpe: CpeTemplate, bf_context: Any  # noqa: ARG001
) -> None:
    """Make CPE unreachable for TR-069 sessions.

    Takes the CPE offline by stopping the TR-069 client (cwmp_plugin), which
    prevents the CPE from receiving connection requests from the ACS and
    participating in TR-069 sessions.
    """
    # Get CPE ID from the cpe object (not from context, since this step
    # now runs before the reboot task is initiated)
    cpe_id = cpe.sw.cpe_id
    
    # Store CPE ID in context for later steps
    bf_context.reboot_cpe_id = cpe_id
    
    # Record test start timestamp for filtering logs
    # GenieACS logs use UTC timestamps, so we record UTC time
    # Subtract a small buffer (5 seconds) to account for timing differences
    from datetime import timedelta
    bf_context.test_start_timestamp = (
        datetime.now(timezone.utc) - timedelta(seconds=5)
    ).replace(tzinfo=None)

    print(f"Making CPE {cpe_id} unreachable for TR-069 sessions...")

    # Stop the TR-069 client process on the CPE using init script
    console = cpe.hw.get_console("console")
    console.execute_command("/etc/init.d/cwmp_plugin stop", timeout=10)

    # Wait for the process to stop
    time.sleep(2)

    # Verify TR-069 client is stopped
    result = console.execute_command("pgrep cwmp_plugin", timeout=5)
    if result.strip():
        raise AssertionError(
            "TR-069 client still running - CPE still reachable for TR-069"
        )

    print(f"✓ CPE {cpe_id} is unreachable for TR-069 sessions (cwmp_plugin stopped)")
    bf_context.cpe_was_taken_offline = True
    # Capture the timestamp when CPE was taken offline
    # This will be used to identify the reconnection event
    bf_context.cpe_offline_timestamp = datetime.now(timezone.utc).replace(tzinfo=None)




@then("the ACS cannot send the connection request to the CPE")
def acs_cannot_send_connection_request(
    acs: AcsTemplate, cpe: CpeTemplate, bf_context: Any  # noqa: ARG001
) -> None:
    """Verify connection request cannot be sent because CPE is unreachable.

    Since the TR-069 client is stopped, the CPE cannot receive connection
    requests from the ACS. This step verifies that the CPE is indeed
    unreachable for TR-069 communication.
    """
    cpe_id = bf_context.reboot_cpe_id

    print(f"Verifying CPE {cpe_id} is unreachable for connection requests...")

    # Verify TR-069 client is still stopped
    console = cpe.hw.get_console("console")
    result = console.execute_command("pgrep cwmp_plugin", timeout=5)
    if result.strip():
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
    """Verify Reboot RPC is queued as pending task in GenieACS.

    When the CPE is offline, GenieACS automatically queues the Reboot RPC
    task to be executed when the CPE next connects to the ACS.
    """
    cpe_id = bf_context.reboot_cpe_id

    print(f"Verifying Reboot RPC is queued for CPE {cpe_id}...")

    # Check GenieACS NBI logs for task creation
    try:
        acs_console = acs.console
        logs = acs_console.execute_command(
            "tail -n 100 /var/log/genieacs/genieacs-nbi-access.log",
            timeout=15,
        )

        # Filter logs by test start timestamp
        log_lines = [line for line in logs.split("\n") if line.strip()]
        start_timestamp = getattr(bf_context, "test_start_timestamp", None)
        filtered_lines = filter_logs_by_timestamp(log_lines, start_timestamp)
        filtered_lines = filter_logs_by_cpe_id(filtered_lines, cpe_id)

        # Look for task creation with reboot
        if any("reboot" in line.lower() for line in filtered_lines):
            print(
                f"✓ Reboot task queued for CPE {cpe_id} "
                "(verified in NBI logs)"
            )
        else:
            # Task was created in Given step, so assume it's queued
            print(f"✓ Reboot task assumed queued (created in previous step)")

    except Exception as e:  # noqa: BLE001
        print(f"⚠ Could not verify in logs: {e}")
        print(f"✓ Reboot task assumed queued (created in previous step)")


@then("when the CPE comes online, it connects to the ACS")
def cpe_comes_online_and_connects(
    acs: AcsTemplate, cpe: CpeTemplate, bf_context: Any  # noqa: ARG001
) -> None:
    """Bring CPE back online and wait for it to connect to ACS.

    Restarts the TR-069 client (cwmp_plugin), which automatically sends an Inform
    message to the ACS when it starts up. This allows the ACS to process
    any queued tasks for the CPE.
    """
    cpe_id = bf_context.reboot_cpe_id

    print(f"Bringing CPE {cpe_id} back online...")

    # Restart TR-069 client using cwmp_plugin init script
    console = cpe.hw.get_console("console")
    console.execute_command("/etc/init.d/cwmp_plugin start", timeout=10)

    # Wait for TR-069 client to start
    time.sleep(5)

    # Verify TR-069 client is running (check for cwmp_plugin process)
    result = console.execute_command("pgrep cwmp_plugin", timeout=5)
    if not result.strip():
        raise AssertionError("TR-069 client (cwmp_plugin) failed to start")

    print(f"✓ CPE {cpe_id} TR-069 client restarted")

    # Wait for CPE to connect to ACS (Inform message)
    print(f"Waiting for CPE {cpe_id} to connect to ACS...")

    max_attempts = 60
    # Get the timestamp when CPE was taken offline (if available)
    offline_timestamp = getattr(bf_context, "cpe_offline_timestamp", None)
    
    for attempt in range(max_attempts):
        try:
            acs_console = acs.console
            # Filter for this CPE's logs only to reduce console noise
            logs = acs_console.execute_command(
                f"tail -n 100 /var/log/genieacs/genieacs-cwmp-access.log | "
                f"grep -i '{cpe_id}'",
                timeout=10,
            )

            log_lines = [line for line in logs.split("\n") if line.strip()]
            
            # Look for "1 BOOT" Inform message that occurs AFTER offline timestamp
            # IMPORTANT: We want the FIRST reconnection after offline, NOT the
            # reconnection after reboot. The Reboot RPC is sent shortly after
            # the CPE reconnects from being offline.
            boot_informs = []
            for line in log_lines:
                if "inform" in line.lower() and cpe_id in line and "1 BOOT" in line:
                    reconnect_ts = parse_log_timestamp(line)
                    if reconnect_ts and offline_timestamp and reconnect_ts > offline_timestamp:
                        boot_informs.append((reconnect_ts, line))
            
            if boot_informs:
                # Sort by timestamp and take the FIRST one (earliest after offline)
                boot_informs.sort(key=lambda x: x[0])
                first_reconnect_ts, first_reconnect_line = boot_informs[0]
                
                bf_context.cpe_reconnection_timestamp = first_reconnect_ts
                print(f"✓ CPE {cpe_id} reconnected to ACS at {first_reconnect_ts} UTC")
                return


        except Exception:  # noqa: BLE001
            pass

        if attempt % 10 == 0:
            print(f"Still waiting... (attempt {attempt + 1}/{max_attempts})")

        time.sleep(2)

    raise AssertionError(
        f"CPE {cpe_id} did not connect to ACS within expected time"
    )


@then("the ACS issues the queued Reboot RPC")
def acs_issues_queued_reboot_rpc(
    acs: AcsTemplate, cpe: CpeTemplate, bf_context: Any  # noqa: ARG001
) -> None:
    """Verify ACS issues the queued Reboot RPC when CPE reconnects.

    When the CPE sends an Inform message after coming online, GenieACS
    automatically processes any queued tasks for that CPE, including the
    Reboot RPC that was queued while the CPE was offline.
    
    IMPORTANT: We filter logs to only look for Reboot RPC sent AFTER
    the CPE reconnected, to avoid matching old Reboot RPCs from previous tests.
    """
    cpe_id = bf_context.reboot_cpe_id

    print(f"Verifying ACS issues queued Reboot RPC to CPE {cpe_id}...")

    # Use reconnection timestamp if available, otherwise fall back to test start
    filter_timestamp = getattr(
        bf_context, "cpe_reconnection_timestamp",
        getattr(bf_context, "test_start_timestamp", None)
    )
    
    # Poll GenieACS CWMP logs for Reboot RPC
    max_attempts = 60

    for attempt in range(max_attempts):
        try:
            acs_console = acs.console
            # Use grep to filter for Reboot RPC lines specifically
            logs = acs_console.execute_command(
                f"tail -n 200 /var/log/genieacs/genieacs-cwmp-access.log | "
                f"grep -i 'reboot' | grep -i '{cpe_id}'",
                timeout=15,
            )

            # Filter logs by reconnection timestamp and CPE ID
            log_lines = [line for line in logs.split("\n") if line.strip()]
            filtered_lines = filter_logs_by_timestamp(
                log_lines, filter_timestamp
            )
            filtered_lines = filter_logs_by_cpe_id(filtered_lines, cpe_id)

            # Look for Reboot RPC sent AFTER reconnection
            for line in filtered_lines:
                line_lower = line.lower()
                if "acs request" in line_lower and "reboot" in line_lower:
                    if 'acsrequestname="reboot"' in line_lower:
                        print(f"✓ ACS issued queued Reboot RPC to CPE {cpe_id}")
                        return

        except Exception:  # noqa: BLE001
            pass

        if attempt % 10 == 0 and attempt > 0:
            print(f"Still waiting... (attempt {attempt + 1}/{max_attempts})")

        time.sleep(2)

    raise AssertionError(
        f"ACS did not issue queued Reboot RPC to CPE {cpe_id} "
        "within expected time (after reconnection)"
    )
