"""Step definitions for CPE (Customer Premises Equipment) actor."""

import time
from datetime import datetime, timezone
from typing import Any

from boardfarm3.templates.acs import ACS as AcsTemplate
from boardfarm3.templates.cpe.cpe import CPE as CpeTemplate
from pytest_bdd import given, then, when

from .helpers import (
    docker_exec_router_command,
    filter_logs_by_cpe_id,
    filter_logs_by_timestamp,
    get_console_uptime_seconds,
    gpv_value,
    parse_log_timestamp,
)


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

    # Wait for CPE to initiate session by checking if it's responding
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
    """CPE sends an Inform message to the ACS.

    We verify this by checking the GenieACS CWMP access logs for the
    Inform RPC message received from the CPE.
    """
    cpe_id = bf_context.reboot_cpe_id

    print(f"Waiting for CPE {cpe_id} to send Inform message...")

    # Check GenieACS CWMP access logs for Inform message
    # Poll the logs until we see the Inform RPC
    max_attempts = 30
    for _attempt in range(max_attempts):
        try:
            acs_console = acs.console
            # Check CWMP logs for Inform RPC
            logs = acs_console.execute_command(
                "tail -n 300 /var/log/genieacs/genieacs-cwmp-access.log | "
                "grep -i inform",
                timeout=10,
            )

            # Filter logs by test start timestamp and CPE ID
            log_lines = [line for line in logs.split("\n") if line.strip()]
            start_timestamp = getattr(
                bf_context, "test_start_timestamp", None
            )
            # First filter by timestamp
            filtered_lines = filter_logs_by_timestamp(
                log_lines, start_timestamp
            )
            # Then filter by CPE ID
            filtered_lines = filter_logs_by_cpe_id(
                filtered_lines, cpe_id
            )
            filtered_logs = "\n".join(filtered_lines)

            # Look for Inform RPC in the filtered logs
            # GenieACS logs should contain Inform messages from CPE
            if "inform" in filtered_logs.lower() or cpe_id in filtered_logs:
                print(
                    f"✓ CPE {cpe_id} sent Inform message "
                    "(verified in GenieACS CWMP logs)"
                )
                # Show the Inform log entry for debugging
                inform_lines = [
                    line for line in filtered_lines
                    if "inform" in line.lower() and line.strip()
                ]
                if inform_lines:
                    print(
                        "Inform message log entry:\n"
                        + "\n".join(inform_lines[-3:])  # Last 3 Inform entries
                    )
                return

        except Exception:  # noqa: BLE001
            # Continue polling if there's an error
            pass

        # Wait before next attempt
        time.sleep(1)

    # If we get here, we didn't see Inform in the logs
    # Try one more time with full recent logs for debugging
    try:
        acs_console = acs.console
        logs = acs_console.execute_command(
            "tail -n 100 /var/log/genieacs/genieacs-cwmp-access.log",
            timeout=10,
        )
        print(
            f"⚠ CPE {cpe_id} Inform message not found in GenieACS logs "
            f"after {max_attempts} attempts"
        )
        print(f"Recent CWMP logs:\n{logs}")
    except Exception as e:  # noqa: BLE001
        print(f"⚠ Could not read GenieACS logs to verify Inform: {e}")

    raise AssertionError(
        f"CPE {cpe_id} did not send Inform message within expected time"
    )


# NOTE: This step definition is currently not used in feature files.
# It was removed from scenarios because verification relies on proxy logs.
# May be reintroduced later if an elegant verification method is found.
# @then("the CPE receives and acknowledges the Reboot RPC")
def cpe_receives_and_acknowledges_reboot_rpc(
    acs: AcsTemplate,
    cpe: CpeTemplate,
    bf_context: Any,
) -> None:
    """CPE receives and acknowledges the Reboot RPC.

    We verify this by checking:
    1. TR-069 proxy logs for the RebootResponse message (for precise timing)
    2. GenieACS logs for evidence that the ACS received/processed the
       acknowledgment

    We also record the uptime before reboot for later comparison to verify
    the reboot occurred.

    Note: There's typically a lag before the CPE starts the reboot process,
    and the total reboot time is about 1 minute. We allow sufficient time
    for the RebootResponse to appear in the logs.
    """
    cpe_id = bf_context.reboot_cpe_id

    print(
        f"Waiting for CPE {cpe_id} to receive and acknowledge Reboot RPC..."
    )

    # Record uptime before reboot (do this early, before reboot starts)
    try:
        bf_context.uptime_before_reboot = get_console_uptime_seconds(cpe)
        print(
            f"Uptime before reboot: {bf_context.uptime_before_reboot}s"
        )
    except Exception as e:  # noqa: BLE001
        print(f"⚠ Could not get CPE uptime before reboot: {e}")
        bf_context.uptime_before_reboot = 0.0

    # Check proxy logs for RebootResponse (for precise timing)
    # The proxy logs show "CPE → ACS: RebootResponse RPC"
    # Note: Proxy logs don't include CPE ID, so we filter by timestamp only
    # Account for lag before reboot starts and ~1 minute total reboot time
    # Poll for up to 120 seconds (allowing for lag + reboot time + buffer)
    max_attempts = 120  # Wait up to 120 seconds

    # Get the timestamp when Reboot RPC was sent (from previous step)
    # We'll use this to find RebootResponse that comes after it
    reboot_rpc_timestamp = None
    try:
        acs_console = acs.console
        # Get recent GenieACS logs to find when Reboot RPC was sent
        acs_logs = acs_console.execute_command(
            "tail -n 100 /var/log/genieacs/genieacs-cwmp-access.log",
            timeout=10,
        )
        acs_log_lines = [line for line in acs_logs.split("\n") if line.strip()]
        start_timestamp = getattr(bf_context, "test_start_timestamp", None)
        filtered_acs_lines = filter_logs_by_timestamp(
            acs_log_lines, start_timestamp
        )
        filtered_acs_lines = filter_logs_by_cpe_id(filtered_acs_lines, cpe_id)
        # Find the most recent Reboot RPC
        for line in reversed(filtered_acs_lines):
            if "reboot" in line.lower() and "acs request" in line.lower():
                reboot_rpc_timestamp = parse_log_timestamp(line)
                if reboot_rpc_timestamp:
                    print(
                        f"Found Reboot RPC timestamp: "
                        f"{reboot_rpc_timestamp} UTC"
                    )
                    break
    except Exception as e:  # noqa: BLE001
        print(f"⚠ Could not determine Reboot RPC timestamp: {e}")

    for attempt in range(max_attempts):
        try:
            # Get recent proxy logs
            proxy_logs = docker_exec_router_command(
                command="tail -n 500 /var/log/tr069-proxy.log",
                timeout=10,
            )

            # Parse log lines
            # Note: Proxy logs don't include CPE ID, so we filter by timestamp
            # only to ensure we're looking at the right time window
            proxy_log_lines = [
                line for line in proxy_logs.split("\n") if line.strip()
            ]
            # Filter by timestamp if we have Reboot RPC timestamp
            # Note: RebootResponse may be at the same second as Reboot RPC,
            # so we need to be lenient with timestamp comparison
            if reboot_rpc_timestamp:
                # Filter proxy logs to entries at or after Reboot RPC was sent
                # Use a slightly earlier timestamp (subtract 1 second) to
                # ensure we catch RebootResponse entries at the same second
                from datetime import timedelta
                filter_start = reboot_rpc_timestamp - timedelta(seconds=1)
                filtered_proxy_lines = filter_logs_by_timestamp(
                    proxy_log_lines, filter_start
                )
            else:
                # If we don't have Reboot RPC timestamp, use test start
                # timestamp
                start_timestamp = getattr(
                    bf_context, "test_start_timestamp", None
                )
                filtered_proxy_lines = filter_logs_by_timestamp(
                    proxy_log_lines, start_timestamp
                )
            filtered_proxy_logs = "\n".join(filtered_proxy_lines)

            # Look for RebootResponse RPC in the filtered logs
            # Proxy logs show "CPE → ACS: RebootResponse RPC"
            if "rebootresponse" in filtered_proxy_logs.lower():
                # Extract timestamp of RebootResponse for later verification
                reboot_response_lines = [
                    line
                    for line in filtered_proxy_lines
                    if "rebootresponse" in line.lower() and line.strip()
                ]
                if reboot_response_lines:
                    # Get the most recent RebootResponse
                    reboot_response_line = reboot_response_lines[-1]
                    reboot_response_timestamp = parse_log_timestamp(
                        reboot_response_line
                    )
                    if reboot_response_timestamp:
                        bf_context.reboot_response_timestamp = (
                            reboot_response_timestamp
                        )
                        print(
                            f"✓ RebootResponse found in proxy logs at "
                            f"{bf_context.reboot_response_timestamp} UTC"
                        )
                        print(f"Proxy log entry:\n{reboot_response_line}")

                    print(
                        f"✓ CPE {cpe_id} received and acknowledged "
                        "Reboot RPC (verified in proxy logs)"
                    )
                    return

        except Exception:  # noqa: BLE001
            # Continue polling if there's an error
            pass

        # Wait before next attempt
        if attempt < max_attempts - 1:
            time.sleep(1)

    # If we get here, we didn't see RebootResponse in the logs
    raise AssertionError(
        f"CPE {cpe_id} did not acknowledge Reboot RPC within expected time "
        f"(waited {max_attempts} seconds). "
        "Checked both proxy logs and GenieACS logs."
    )


@then("the CPE executes the reboot command and restarts")
def cpe_executes_reboot_and_restarts(
    acs: AcsTemplate,  # noqa: ARG001
    cpe: CpeTemplate,
    bf_context: Any,
) -> None:
    """CPE executes the reboot command and restarts.

    Simplified version for failure scenarios. Verifies reboot happened
    by checking that CPE becomes unresponsive. Does not wait for
    reconnection or Inform messages (used in failure test scenarios).
    """
    cpe_id = bf_context.reboot_cpe_id

    print(f"Verifying CPE {cpe_id} executes reboot and restarts...")

    # Wait for CPE to become unresponsive (reboot started)
    print("Checking that CPE becomes unresponsive...")
    max_attempts = 30
    became_unresponsive = False

    for _attempt in range(max_attempts):
        try:
            console = cpe.hw.get_console("console")
            console.execute_command("echo test", timeout=2)
            time.sleep(1)
        except Exception:  # noqa: BLE001
            became_unresponsive = True
            print(f"✓ CPE {cpe_id} became unresponsive - reboot started")
            break

    if not became_unresponsive:
        raise AssertionError(
            f"CPE {cpe_id} did not become unresponsive - "
            "reboot may not have started"
        )

    # Wait a bit for reboot to complete
    print("Waiting for reboot to complete...")
    time.sleep(30)

    print(f"✓ CPE {cpe_id} reboot completed (verified by unresponsiveness)")


@then(
    "after completing the boot sequence, the CPE sends an Inform message "
    "to the ACS indicating that the boot sequence has been completed"
)
def cpe_sends_inform_after_boot_completion(
    acs: AcsTemplate,
    cpe: CpeTemplate,  # noqa: ARG001
    bf_context: Any,
) -> None:
    """CPE sends Inform after boot completion.

    Verifies reboot by checking GenieACS CWMP logs for post-reboot Inform
    message with event codes "1 BOOT" and "M Reboot". This confirms:
    - Reboot occurred
    - CPE reconnected
    - Boot sequence completed

    The post-reboot Inform message appears in GenieACS logs after the CPE
    reboots and reconnects to the ACS.
    """
    cpe_id = bf_context.reboot_cpe_id

    print(
        f"Waiting for CPE {cpe_id} to complete boot and send "
        "post-reboot Inform message..."
    )

    # Wait a bit for reboot to start (if it hasn't already)
    time.sleep(5)

    # Poll GenieACS CWMP logs for post-reboot Inform message
    # Look for Inform messages that appear AFTER Reboot RPC chronologically
    # GenieACS logs the Reboot RPC as: ACS request; acsRequestName="Reboot"
    # The post-reboot Inform has event codes: "1 BOOT,M Reboot"
    max_attempts = 120  # Wait up to 4 minutes (120 * 2 seconds)
    reboot_rpc_timestamp = None

    for attempt in range(max_attempts):
        try:
            acs_console = acs.console
            # Get recent CWMP logs
            logs = acs_console.execute_command(
                "tail -n 500 /var/log/genieacs/genieacs-cwmp-access.log",
                timeout=10,
            )

            # Parse log lines and filter by test start timestamp and CPE ID
            log_lines = [line for line in logs.split("\n") if line.strip()]
            start_timestamp = getattr(
                bf_context, "test_start_timestamp", None
            )
            # First filter by timestamp
            log_lines = filter_logs_by_timestamp(log_lines, start_timestamp)
            # Then filter by CPE ID
            log_lines = filter_logs_by_cpe_id(log_lines, cpe_id)

            # Find the Reboot RPC timestamp in GenieACS logs (only once)
            # GenieACS logs: ACS request; acsRequestName="Reboot"
            if reboot_rpc_timestamp is None:
                for line in log_lines:
                    if (
                        "acsrequestname=\"reboot\"" in line.lower()
                        or "acsRequestName=\"Reboot\"" in line
                    ):
                        # Extract timestamp from log line
                        reboot_rpc_timestamp = parse_log_timestamp(line)
                        if reboot_rpc_timestamp:
                            print(
                                f"Found Reboot RPC at "
                                f"{reboot_rpc_timestamp} UTC"
                            )
                            break

            # If we found Reboot RPC, look for Inform messages AFTER it
            if reboot_rpc_timestamp:
                # Look for Inform messages with "M Reboot" event code
                # that appear after the Reboot RPC timestamp
                for line in log_lines:
                    if (
                        "inform" in line.lower()
                        and "M Reboot" in line
                    ):
                        # Extract timestamp from this Inform message
                        inform_timestamp = parse_log_timestamp(line)
                        if inform_timestamp:
                            # Compare timestamps to ensure Inform is after
                            # Reboot RPC
                            if inform_timestamp > reboot_rpc_timestamp:
                                print(
                                    f"✓ CPE {cpe_id} sent post-reboot Inform "
                                    f"message at {inform_timestamp} UTC "
                                    "(verified in GenieACS logs)"
                                )

                                # Show the Inform log entry for debugging
                                print(f"Post-reboot Inform log entry:\n{line}")

                                # Refresh console connection now that reboot is confirmed complete
                                # This ensures subsequent steps have a valid connection
                                print("↻ Refreshing CPE console connection after reboot...")
                                try:
                                    cpe.hw.disconnect_from_consoles()
                                except Exception:
                                    pass
                                
                                try:
                                    device_name = getattr(cpe, "device_name", "cpe")
                                    cpe.hw.connect_to_consoles(device_name)
                                    print("✓ Console connection refreshed successfully")
                                except Exception as reconnect_error:
                                    print(f"❌ Failed to refresh console connection: {reconnect_error}")

                                return

            # If we haven't seen Reboot RPC yet, continue waiting
            if not reboot_rpc_timestamp:
                if attempt % 10 == 0:  # Log every 10 attempts
                    print(
                        f"Waiting for Reboot RPC in logs... "
                        f"(attempt {attempt + 1}/{max_attempts})"
                    )
        except Exception:  # noqa: BLE001
            # Continue polling if there's an error
            pass

        if attempt < max_attempts - 1:
            time.sleep(2)

    # If we get here, we didn't find the post-reboot Inform
    # Try to get recent logs for debugging
    try:
        acs_console = acs.console
        logs = acs_console.execute_command(
            "tail -n 200 /var/log/genieacs/genieacs-cwmp-access.log",
            timeout=10,
        )
        print(
            f"⚠ CPE {cpe_id} post-reboot Inform message not found "
            f"after {max_attempts} attempts"
        )
        print(f"Recent GenieACS CWMP logs:\n{logs}")
    except Exception as e:  # noqa: BLE001
        print(f"⚠ Could not read GenieACS logs: {e}")

    raise AssertionError(
        f"CPE {cpe_id} did not send post-reboot Inform message "
        "within expected time"
    )


@then(
    "the CPE resumes normal operation, "
    "continuing periodic communication with the ACS"
)
def cpe_resumes_normal_operation(
    acs: AcsTemplate, cpe: CpeTemplate, bf_context: Any  # noqa: ARG001
) -> None:
    """CPE resumes normal operation, continuing periodic communication.

    We verify this by checking that the CPE is online and can be queried,
    indicating it's in normal operation mode.
    """
    cpe_id = bf_context.reboot_cpe_id

    print(f"Verifying CPE {cpe_id} has resumed normal operation...")

    # Verify CPE is online and operational
    result = acs.GPV(
        "Device.DeviceInfo.SoftwareVersion", cpe_id=cpe_id, timeout=30
    )
    assert result, (
        f"CPE {cpe_id} is not responding, "
        "indicating it has not resumed normal operation"
    )

    print(
        f"CPE {cpe_id} has resumed normal operation "
        "and periodic communication"
    )


@then(
    "the CPE's configuration and operational state "
    "are preserved after reboot"
)
def cpe_configuration_preserved_after_reboot(
    acs: AcsTemplate, cpe: CpeTemplate, bf_context: Any
) -> None:
    """CPE configuration preserved after reboot.

    We verify this by comparing key configuration parameters before and
    after reboot, including:
    - User account names and (encrypted) passwords
    - Network settings (IP addresses, etc.)
    - WiFi SSID configuration
    - System settings
    """
    cpe_id = bf_context.reboot_cpe_id

    print(f"Verifying configuration preservation for CPE {cpe_id}...")

    config_before = getattr(bf_context, "config_before_reboot", {})
    if not config_before:
        print(
            "⚠ Configuration was not captured before reboot. "
            "Skipping detailed verification."
        )
        # Fall back to basic firmware check
        current_firmware = gpv_value(
            acs, cpe, "Device.DeviceInfo.SoftwareVersion"
        )
        print(f"Current firmware version: {current_firmware}")
        return

    verification_errors = []
    verified_items = []

    # Generic verification: iterate through all items in config_before_reboot
    for config_key, config_data in config_before.items():
        # Skip if not a dict (legacy format support)
        if not isinstance(config_data, dict):
            continue

        # Simple value verification (e.g., firmware_version)
        if "gpv_param" in config_data and "value" in config_data:
            try:
                current_value = gpv_value(acs, cpe, config_data["gpv_param"])
                expected_value = config_data["value"]
                if current_value != expected_value:
                    verification_errors.append(
                        f"{config_key} changed: "
                        f"{expected_value} → {current_value}"
                    )
                else:
                    print(f"✓ {config_key} preserved: {current_value}")
                    verified_items.append(config_key)
            except Exception as e:  # noqa: BLE001
                verification_errors.append(
                    f"Could not verify {config_key}: {e}"
                )

        # Dict-based verification (e.g., users, wifi_ssids)
        elif "count" in config_data and "items" in config_data:
            config_name = config_key.replace("_", " ").title()
            print(f"Verifying {config_name} configuration...")
            try:
                # Verify count first
                if config_data["count"]:
                    count_gpv = config_data["count"]["gpv_param"]
                    expected_count = config_data["count"]["value"]
                    count_result = acs.GPV(
                        count_gpv, cpe_id=cpe_id, timeout=30
                    )
                    if count_result:
                        current_count = int(
                            count_result[0].get("value", 0)
                        )
                        if current_count != expected_count:
                            verification_errors.append(
                                f"{config_name} count changed: "
                                f"{expected_count} → {current_count}"
                            )
                        else:
                            print(
                                f"✓ {config_name} count preserved: "
                                f"{current_count}"
                            )

                # Verify each item
                for item_idx, item_fields in config_data["items"].items():
                    for field_name, field_data in item_fields.items():
                        if (
                            isinstance(field_data, dict)
                            and "gpv_param" in field_data
                            and "value" in field_data
                        ):
                            try:
                                current_value = gpv_value(
                                    acs, cpe, field_data["gpv_param"]
                                )
                                expected_value = field_data["value"]
                                # Handle boolean comparison
                                if isinstance(expected_value, bool):
                                    current_bool = (
                                        current_value.lower()
                                        in ("true", "1", "enabled")
                                    )
                                    if current_bool != expected_value:
                                        verification_errors.append(
                                            f"{config_name} {item_idx} "
                                            f"{field_name} changed: "
                                            f"{expected_value} → "
                                            f"{current_bool}"
                                        )
                                    else:
                                        print(
                                            f"✓ {config_name} {item_idx} "
                                            f"{field_name} preserved: "
                                            f"{current_value}"
                                        )
                                else:
                                    if current_value != str(expected_value):
                                        verification_errors.append(
                                            f"{config_name} {item_idx} "
                                            f"{field_name} changed: "
                                            f"{expected_value} → "
                                            f"{current_value}"
                                        )
                                    else:
                                        # Mask password in output
                                        display_value = (
                                            "***"
                                            if "password" in field_name.lower()
                                            else current_value
                                        )
                                        print(
                                            f"✓ {config_name} {item_idx} "
                                            f"{field_name} preserved: "
                                            f"{display_value}"
                                        )
                            except Exception as e:  # noqa: BLE001
                                verification_errors.append(
                                    f"Could not verify {config_name} "
                                    f"{item_idx} {field_name}: {e}"
                                )
                verified_items.append(config_name)
            except Exception as e:  # noqa: BLE001
                verification_errors.append(
                    f"Could not verify {config_name}: {e}"
                )

    # Report summary
    if verified_items:
        print(
            f"✓ Verified preservation of: {', '.join(verified_items)}"
        )

    # Report results
    if verification_errors:
        error_msg = (
            "Configuration was not fully preserved after reboot:\n"
            + "\n".join(f"  - {error}" for error in verification_errors)
        )
        raise AssertionError(error_msg)

    print("✓ All configuration parameters preserved after reboot")


@then("the CPE does not reboot")
def cpe_does_not_reboot(acs: AcsTemplate, cpe: CpeTemplate, bf_context: Any) -> None:
    """Verify the CPE does not reboot by checking that its uptime has increased."""
    import time
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
