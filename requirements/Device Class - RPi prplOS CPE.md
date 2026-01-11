# Device Class - RPi prplOS CPE

**Goal**: Boardfarm can successfully instantiate and boot a physical RPi4 running prplOS.

**Actors**:
- Boardfarm (System)
- Test Engineer (User)
- RPi4 (Device Under Test)
- ACS (Auto Configuration Server)

**Preconditions**:
- RPi4 is connected via serial console (/dev/ttyUSB0)
- RPi4 is connected to network (WAN/LAN)
- Boardfarm environment is configured (virtualenv, config files)

**Success Guarantees**:
- Boardfarm instantiates the `RPiPrplOSCPE` class
- Serial console connection is established
- Device boots successfully
- Device obtains IP address
- Device registers with ACS
- Device is accessible for testing

**Main Success Scenario**:
1.  Boardfarm reads the configuration for `bf_rpiprplos_cpe`.
2.  Boardfarm instantiates the device class.
3.  Boardfarm connects to the serial console.
4.  Boardfarm initiates the boot sequence.
5.  Device performs soft reboot.
6.  Device connects to WAN.
7.  Device configures ACS URL via TR-181.
8.  Device sends Inform message to ACS.
9.  Boardfarm verifies device is online and registered in ACS.

**Extensions**:

*   **1.a Device Not Found in Configuration**:
    *   Boardfarm fails to find device entry.
    *   Test fails with configuration error.

*   **3.a Serial Console Connection Failure**:
    *   Boardfarm cannot connect to `/dev/ttyUSB0`.
    *   Test fails with connection error.

*   **5.a Boot Sequence Failure**:
    *   Device fails to come back online after reboot.
    *   Test fails with boot timeout.

*   **7.a TR-181 Access Failure**:
    *   Device comes online but `ubus-cli` is not responsive.
    *   Test fails with configuration error.

*   **8.a ACS Registration Failure**:
    *   Device fails to contact ACS (network issue or wrong URL).
    *   Test fails with registration timeout.
