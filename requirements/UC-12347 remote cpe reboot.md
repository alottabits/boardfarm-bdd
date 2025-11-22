## Goal

Remotely reboot the CPE device to restore connectivity, apply configuration changes, or resolve operational issues without physical access to the device.

## Scope

The E2E system, including the ACS, CPE, and network infrastructure.

## Primary Actor

Operator

## Stakeholders

- Subscriber
- ACS Administrator
- Network Operations
- CPE
- ACS

## Level

user-goal

## Preconditions

1. The target CPE is online, registered with the ACS, and fully provisioned.
2. The operator has administrative access to the ACS.
3. The user has set the CPE GUI password.

## Minimal Guarantees

- The ACS logs all reboot-related activities, including failures.
- If the reboot fails, the CPE remains in its current operational state.
- The ACS maintains the device record and configuration even if the CPE fails to reconnect after reboot.

## Success Guarantees

1. The CPE successfully reboots and completes the boot sequence.
2. The CPE reconnects to the ACS after reboot.
3. The ACS correctly identifies the reboot event via the Inform message.
4. The CPE's configuration and operational state are preserved after reboot.
5. The CPE resumes normal operation and continues periodic Inform sessions with the ACS.

## Trigger

An operator initiates a reboot command via the ACS targeting a specific CPE device.

## Main Success Scenario

1. An operator initiates a reboot command via the ACS.
2. The ACS creates a reboot task for the CPE.
3. The ACS sends a connection request to the CPE.
4. The CPE receives the connection request and initiates a session with the ACS.
5. The CPE sends an Inform message to the ACS.
6. The ACS responds to the Inform message by issuing the Reboot RPC to the CPE.
7. The CPE receives and acknowledges the Reboot RPC.
8. The CPE executes the reboot command.
9. The CPE shuts down gracefully and restarts.
10. After completing the boot sequence, the CPE reconnects to the ACS.
11. The CPE sends an Inform message to the ACS indicating that the boot sequence has been completed.
12. The ACS responds to the Inform message.
13. The ACS may verify device state.
14. The CPE resumes normal operation, continuing periodic communication with the ACS.
15. Use case succeeds and all success guarantees are met.

## Extensions

- **3.a CPE Not Connected When Reboot Requested**:
  
  1. The CPE is unreachable for TR-069 sessions (e.g., TR-069 client stopped, network disconnected).
  2. The operator initiates a reboot task on the ACS for the CPE.
  3. The ACS creates a reboot task, but cannot send the connection request to the CPE.
  4. The ACS queues the Reboot RPC as a pending task.
  5. When the CPE comes online, it connects to the ACS.
  6. The CPE sends an Inform message to the ACS.
  7. The ACS issues the queued Reboot RPC.
  8. Continue from step 7 of the main success scenario.



## Technology & Data Variations List

- **Trigger method**: The reboot can be triggered via:
  - ACS UI interface
  - ACS API interface
  - Queued task waiting for next periodic check-in interval
- **Connection request**: The ACS may send an immediate connection request to the CPE, causing immediate check-in rather than waiting for periodic communication.
- **Reboot timing**: The reboot may occur immediately after receiving the RPC, or after a configurable delay (if supported by the CPE).
- **Network address changes**: The CPE's IP address may change after reboot (e.g., DHCP lease renewal), but this does not affect ACS connectivity as long as the CPE can reach the ACS.
- **Post-reboot notification**: The CPE's post-reboot Inform message includes event codes indicating:
  - Boot event (device has restarted)
  - Reboot method/trigger (indicates ACS-initiated reboot)
  - The command key from the original Reboot RPC is included
  - Value change events may be included if configuration or state changes occurred

## Related information

- This use case assumes the use of the TR-069 protocol for CPE management.
- The CPE's ability to reconnect after reboot depends on network configuration being preserved (e.g., WAN interface configuration, ACS URL, credentials).
- The command key from the Reboot RPC is returned in the post-reboot Inform message, allowing the ACS to correlate the reboot event with the original request.
- In containerized testbed environments, the reboot effectively restarts the container, which is handled gracefully by Docker.
- For detailed technical flow and implementation details, see: `boardfarm-bdd/docs/GenieACS_Reboot_Button_Analysis.md`
