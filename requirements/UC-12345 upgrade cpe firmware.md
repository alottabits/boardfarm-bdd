
## Goal

Upgrade the CPE firmware to the desired version and verify its operational state.

## Scope

The E2E system, including the ACS, firmware hosting server, CPE, and network infrastructure.

## Primary Actor

Operator

## Stakeholders

- Subscriber
- ACS Administrator
- Network Operations

## Level

user-goal

## Preconditions

1.  A new, cryptographically signed firmware file is available.
2.  The operator has administrative access to the ACS and the firmware hosting server.
3.  The target CPE is online, registered with the ACS, and fully provisioned.
4.  The user has configured a custom username and password for the CPE's web interface.
5.  The user has configured a custom SSID for the wireless network.

## Minimal Guarantees

- The CPE remains operational on its existing firmware if any step of the upgrade process fails.
- The ACS logs all upgrade-related activities, including failures.

## Success Guarantees

1.  The CPE is running the new, specified firmware version.
2.  The CPE is online, fully provisioned, and connected to the ACS.
3.  The ACS correctly reports the new firmware version for the device.
4.  Subscriber credentials and critical LAN configurations (e.g., SSID, password) are preserved.
5.  Internet connectivity for the subscriber is restored.

## Trigger

The CPE's pre-configured periodic `Inform` interval elapses, causing it to initiate a TR-069 session with the ACS, while a pending firmware upgrade is queued on the ACS.

## Main Success Scenario
1. An operator places the new, signed firmware file on an image server that is routable from the CPE's WAN interface.
2. An operator configures the ACS to issue a `Download` command for the target CPE.
3. The CPE sends an `Inform` message to the ACS when its periodic interval elapses.
4. The ACS issues the pre-configured `Download` RPC.
5. The CPE downloads the firmware from the image server.
6. The CPE validates the firmware.
7. After successful validation, the CPE installs the firmware and automatically **reboots**.
8. The CPE reconnects to the ACS.
9. The ACS reflects the updated software version for the CPE.
10. Use case succeeds and all success guarantees are met.

## Extensions

- **6.a Firmware Verification Fails**:
    1. The CPE verifies the firmware but rejects it due to validation failure.
    2. The CPE reports the failed verification to the ACS.
    3. The ACS records the failure with a non-zero fault code.
    4. The CPE does not reboot and remains on the previous firmware version.
    5. Use case fails; minimal guarantees are met.

- **8.a CPE Fails to Provision After Reboot**:
    1. After rebooting with the new firmware, the CPE fails to reconnect in a stable, provisioned state.
    2. The device rolls back autonomously to the previous firmware and reboots.
    3. The CPE reconnects and resumes normal operation on the original firmware.
    4. Use case fails; minimal guarantees are met.

- **10.a Subscriber Credentials are Reset to Factory Default**:
    1. The firmware upgrade succeeds, but user-configured settings are lost.
    2. Subscriber re-configures user credentials and LAN settings.
    3. Use case succeeds with comments, noting the configuration loss.

## Technology & Data Variations List

- **Firmware hosting protocol**: HTTP or HTTPS. The WAN container in the testbed provides HTTP service via lighttpd, and native PrplOS sysupgrade handles HTTP/HTTPS URLs directly. This eliminates the need for TFTP-specific handling logic.
- **Artifact resolution source**: Artifact (filename/URI/version) can be derived from device inventory/configuration or explicitly provided in the test context.
- **Firmware file location**: IP address/host and path on the HTTP server (e.g., `http://172.25.1.2/firmware.bin`).
- **TR-069 trigger method**: The CPE's periodic `Inform` interval or an ACS-triggered `ScheduleInform`.

## Related information

This process assumes the use of the TR-069 protocol for CPE management. The cryptographic signature verification is a critical security measure to prevent unauthorized firmware from being installed.