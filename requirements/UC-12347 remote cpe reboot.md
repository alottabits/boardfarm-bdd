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

## Level

user-goal

## Preconditions

1. The target CPE is online, registered with the ACS, and fully provisioned.
2. The operator has administrative access to the ACS.
3. The CPE is capable of receiving TR-069 RPCs from the ACS.

## Minimal Guarantees

- The ACS logs all reboot-related activities, including failures.
- If the reboot fails, the CPE remains in its current operational state (no partial reboot state).
- The ACS maintains the device record and configuration even if the CPE fails to reconnect after reboot.

## Success Guarantees

1. The CPE successfully reboots and completes the boot sequence.
2. The CPE reconnects to the ACS after reboot (verified by successful Inform message and response to RPC requests).
3. The ACS correctly identifies the reboot event via the Inform message (event code "1 BOOT" with "M Reboot").
4. The CPE's configuration and operational state are preserved after reboot.
5. The CPE resumes normal operation and continues periodic Inform sessions with the ACS.

## Trigger

An operator initiates a reboot command via the ACS UI or NBI API, targeting a specific CPE device.

## Main Success Scenario

1. An operator configures the ACS to issue a `Reboot` RPC for the target CPE.
2. The ACS triggers an immediate connection request to the CPE (via `?connection_request=` parameter or "Commit" action in UI).
3. The CPE sends an `Inform` message to the ACS (either triggered by connection request or during periodic Inform interval).
4. The ACS issues the `Reboot` RPC to the CPE.
5. The CPE receives and acknowledges the `Reboot` RPC with a `RebootResponse`.
6. The CPE initiates the reboot sequence (executes system reboot command).
7. The CPE shuts down gracefully and restarts.
8. After completing the boot sequence, the CPE reconnects to the ACS by sending an `Inform` message with event code "1 BOOT" and "M Reboot".
9. The ACS acknowledges the Inform and may issue follow-up RPCs to verify device state.
10. The CPE resumes normal operation and periodic Inform sessions.
11. Use case succeeds and all success guarantees are met.

## Extensions

- **4.a CPE Not Connected When Reboot Requested**:
    1. The ACS attempts to send the Reboot RPC, but the CPE is not currently connected.
    2. The ACS queues the Reboot RPC as a pending task.
    3. When the CPE's next periodic Inform interval elapses, it connects to the ACS.
    4. The ACS issues the queued Reboot RPC.
    5. Continue from step 5 of the main success scenario.

- **5.a CPE Rejects Reboot RPC**:
    1. The CPE receives the Reboot RPC but rejects it (e.g., due to access rights or invalid state).
    2. The CPE responds with a `RebootResponse` containing a fault code.
    3. The ACS records the failure with the fault code.
    4. The CPE does not reboot and remains in its current operational state.
    5. Use case fails; minimal guarantees are met.

- **7.a CPE Fails to Complete Boot Sequence**:
    1. The CPE initiates reboot but fails to complete the boot sequence (e.g., kernel panic, boot loop).
    2. The CPE does not reconnect to the ACS within the expected time window.
    3. The ACS detects the absence of periodic Inform messages.
    4. The ACS logs the failure and may trigger alerts.
    5. Use case fails; minimal guarantees are met (device record preserved, but CPE is non-operational).

- **8.a CPE Fails to Reconnect After Reboot**:
    1. The CPE successfully reboots but fails to reconnect to the ACS (e.g., network configuration lost, ACS unreachable).
    2. The ACS does not receive Inform messages from the CPE after the expected reconnection window.
    3. The ACS logs the disconnection and may trigger alerts.
    4. Use case fails; minimal guarantees are met (device record preserved, but CPE is disconnected).

- **10.a CPE Configuration Lost During Reboot**:
    1. The reboot succeeds, but some configuration parameters are reset to defaults.
    2. The CPE reconnects to the ACS with default or partial configuration.
    3. The ACS detects configuration discrepancies and may trigger reprovisioning.
    4. Use case succeeds with comments, noting the configuration loss and reprovisioning.

## Technology & Data Variations List

- **TR-069 trigger method**: The reboot can be triggered via:
    - ACS UI "Commit" action (immediate connection request)
    - NBI API with `?connection_request=` query parameter (immediate connection request)
    - Queued task waiting for next periodic Inform interval
- **Reboot timing**: The reboot may occur immediately after receiving the RPC, or after a configurable delay (if supported by the CPE).
- **Network address changes**: The CPE's IP address may change after reboot (e.g., DHCP lease renewal), but this does not affect ACS connectivity as long as the CPE can reach the ACS.
- **Inform event codes**: The CPE's post-reboot Inform message includes event codes indicating:
    - "1 BOOT" - Boot event
    - "M Reboot" - Reboot method/trigger
    - "4 VALUE CHANGE" - Configuration or state changes

## Related information

- This use case assumes the use of the TR-069 protocol for CPE management.
- Unlike Factory Reset, the Reboot operation does not require MTD flash partitions and works successfully in containerized environments.
- The reboot operation is typically faster than firmware upgrades and does not involve file downloads or validation steps.
- The CPE's ability to reconnect after reboot depends on network configuration being preserved (e.g., WAN interface configuration, ACS URL, credentials).
- In containerized testbed environments, the reboot effectively restarts the container, which is handled gracefully by Docker.

