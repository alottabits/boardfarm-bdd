# GenieACS Reboot Button Functionality Analysis

## Overview

This document explains what happens when the "Reboot" button is clicked in the GenieACS UI and what TR-069 RPC calls are made to the CPE.

## Flow Diagram

```
User clicks "Reboot" button in GenieACS UI
    ↓
GenieACS UI → NBI API: POST /devices/{cpe_id}/tasks?connection_request=
    ↓
GenieACS creates reboot task: {"name": "reboot", "commandKey": "reboot"}
    ↓
GenieACS sends ConnectionRequest to CPE (via TR-069 ConnectionRequest mechanism)
    ↓
CPE receives ConnectionRequest and initiates TR-069 session
    ↓
CPE → ACS: Inform message (with event codes)
    ↓
ACS → CPE: Reboot RPC (SOAP message)
    ↓
CPE → ACS: RebootResponse (acknowledgment)
    ↓
CPE executes reboot command
    ↓
[CPE reboots...]
    ↓
CPE reconnects to ACS after boot
    ↓
CPE → ACS: Inform message (with event codes: "1 BOOT", "M Reboot")
    ↓
ACS → CPE: InformResponse
    ↓
[Optional] ACS → CPE: GetParameterValues (to verify device state)
```

## Detailed Step-by-Step Process

### Step 1: UI Button Click

When a user clicks the "Reboot" button in the GenieACS UI (typically in the device details page), the UI makes an HTTP POST request to the GenieACS NBI (Northbound Interface) API.

### Step 2: NBI API Call

**Endpoint:** `POST /devices/{cpe_id}/tasks?connection_request=`

**Request Body:**
```json
{
  "name": "reboot",
  "commandKey": "reboot"
}
```

**Key Parameters:**
- `name`: Task type, set to `"reboot"` for reboot operations
- `commandKey`: String that will be returned in the CommandKey element of the InformStruct when the CPE reboots (default: `"reboot"`)
- `?connection_request=`: Query parameter that triggers GenieACS to immediately send a ConnectionRequest to the CPE

**Implementation Reference:**
```460:495:boardfarm/boardfarm3/devices/genie_acs.py
    def Reboot(
        self,
        CommandKey: str = "reboot",
        cpe_id: str | None = None,
    ) -> list[dict]:
        """Execute Reboot RPC via GenieACS NBI API.

        Creates a reboot task that will be executed when the CPE checks in.

        :param CommandKey: reboot command key, defaults to "reboot"
        :type CommandKey: str
        :param cpe_id: cpe identifier, defaults to None
        :type cpe_id: str | None
        :return: reboot task creation response (empty list for compatibility)
        :rtype: list[dict]
        """
        if not cpe_id:
            raise ValueError("cpe_id is required for Reboot operation")

        # Create reboot task via GenieACS NBI API
        reboot_task = {
            "name": "reboot",
            "commandKey": CommandKey,
        }

        self._request_post(
            endpoint=f"/devices/{cpe_id}/tasks",
            data=reboot_task,
            conn_request=True,
            timeout=30,
        )

        _LOGGER.info("Reboot task created for CPE %s", cpe_id)

        # Return empty list for compatibility with ACS template interface
        return []
```

### Step 3: Connection Request Mechanism

The `conn_request=True` parameter (which adds `?connection_request=` to the URL) causes GenieACS to immediately send a **ConnectionRequest** to the CPE. This is a TR-069 mechanism that tells the CPE to check in with the ACS immediately, rather than waiting for the next periodic check-in.

**Connection Request Implementation:**
```378:414:boardfarm/boardfarm3/devices/genie_acs.py
    def _request_post(
        self,
        endpoint: str,
        data: dict[str, Any] | list[Any],
        conn_request: bool = True,
        timeout: int | None = None,
    ) -> Any:  # noqa: ANN401
        if conn_request:
            # GenieACS requires '?connection_request=' (with equals) to trigger immediate connection
            request_url = urljoin(self._base_url, f"{endpoint}?connection_request=")
        else:
            err_msg = (
                "It is unclear how the code would work without 'conn_request' "
                "being True. /FC"
            )
            raise ValueError(err_msg)
        try:
            timeout = timeout if timeout else GenieACS.CPE_wait_time
            response = self._client.post(request_url, json=data, timeout=timeout)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            # Capture error details from response body
            error_msg = f"HTTP {exc.response.status_code}"
            try:
                error_body = exc.response.json()
                if isinstance(error_body, dict):
                    error_detail = error_body.get("error") or error_body.get("message") or str(error_body)
                    error_msg = f"{error_msg}: {error_detail}"
                else:
                    error_msg = f"{error_msg}: {error_body}"
            except Exception:  # noqa: BLE001
                error_msg = f"{error_msg}: {exc.response.text[:200]}"
            _LOGGER.error("GenieACS API error: %s", error_msg)
            raise ConnectionError(error_msg) from exc
        except (httpx.ConnectError, httpx.HTTPError) as exc:
            raise ConnectionError from exc
        return response.json()
```

### Step 4: CPE Initiates TR-069 Session

Upon receiving the ConnectionRequest, the CPE initiates a TR-069 session by sending an **Inform** message to the ACS.

**Inform Message Structure:**
- Contains device identification (OUI, ProductClass, SerialNumber)
- Contains event codes indicating why the CPE is connecting
- Contains current time and other device information

### Step 5: ACS Sends Reboot RPC

After receiving the Inform message, GenieACS responds with an **InformResponse**, and then sends the **Reboot RPC** to the CPE.

**Reboot RPC (SOAP Message):**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" 
               xmlns:soap-enc="http://schemas.xmlsoap.org/soap/encoding/" 
               xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
               xmlns:xsd="http://www.w3.org/2001/XMLSchema" 
               xmlns:cwmp="urn:dslforum-org:cwmp-1-4">
  <soap:Header>
    <cwmp:ID>12345</cwmp:ID>
  </soap:Header>
  <soap:Body>
    <cwmp:Reboot>
      <CommandKey>reboot</CommandKey>
    </cwmp:Reboot>
  </soap:Body>
</soap:Envelope>
```

**Key Elements:**
- `<cwmp:Reboot>`: The RPC method name
- `<CommandKey>`: The command key string (default: "reboot") that will be returned in the post-reboot Inform message

### Step 6: CPE Acknowledges Reboot RPC

The CPE responds with a **RebootResponse** message:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" 
               xmlns:cwmp="urn:dslforum-org:cwmp-1-4">
  <soap:Header>
    <cwmp:ID>12345</cwmp:ID>
  </soap:Header>
  <soap:Body>
    <cwmp:RebootResponse/>
  </soap:Body>
</soap:Envelope>
```

### Step 7: CPE Executes Reboot

After sending the RebootResponse, the CPE:
1. Completes the current TR-069 session
2. Executes the reboot command (typically `reboot` or `systemctl reboot`)
3. Shuts down gracefully and restarts

### Step 8: Post-Reboot Reconnection

After the CPE completes its boot sequence, it reconnects to the ACS and sends a new **Inform** message with specific event codes:

**Post-Reboot Inform Event Codes:**
- `"1 BOOT"`: Indicates the device has restarted
- `"M Reboot"`: Indicates the reboot was triggered by the ACS's Reboot RPC

**Inform Message Example:**
```xml
<soap:Body>
  <cwmp:Inform>
    <DeviceId>
      <Manufacturer>...</Manufacturer>
      <OUI>...</OUI>
      <ProductClass>...</ProductClass>
      <SerialNumber>...</SerialNumber>
    </DeviceId>
    <Event>
      <EventStruct>
        <EventCode>1 BOOT</EventCode>
        <CommandKey>reboot</CommandKey>
      </EventStruct>
      <EventStruct>
        <EventCode>M Reboot</EventCode>
        <CommandKey>reboot</CommandKey>
      </EventStruct>
    </Event>
    <MaxEnvelopes>1</MaxEnvelopes>
    <CurrentTime>2024-01-01T12:00:00Z</CurrentTime>
    <RetryCount>0</RetryCount>
    <!-- ... other parameters ... -->
  </cwmp:Inform>
</soap:Body>
```

### Step 9: ACS Verification (Optional)

After receiving the post-reboot Inform, the ACS may send follow-up RPCs to verify device state:

- **GetParameterValues**: To verify device parameters are correct
- **GetParameterNames**: To discover device capabilities
- **SetParameterValues**: To apply any pending configuration changes

## TR-069 Protocol Details

### Connection Request Mechanism

The ConnectionRequest is a TR-069 mechanism that allows the ACS to trigger an immediate CPE check-in. It can be implemented via:

1. **HTTP GET Request**: ACS sends HTTP GET to a CPE endpoint (if CPE supports HTTP server)
2. **STUN**: Using STUN (Session Traversal Utilities for NAT) protocol
3. **Other Mechanisms**: Vendor-specific implementations

In GenieACS, the `?connection_request=` parameter triggers GenieACS's internal ConnectionRequest mechanism, which then contacts the CPE to initiate an immediate session.

### Reboot RPC Specification

According to TR-069 specification (CWMP-1-4):

- **RPC Name**: `Reboot`
- **Parameters**: 
  - `CommandKey` (string): A string that identifies the command. This value is returned in the CommandKey element of the InformStruct when the CPE reboots.
- **Response**: `RebootResponse` (empty body)
- **Behavior**: The CPE must reboot within a reasonable time after sending the RebootResponse

### Inform Event Codes

TR-069 defines standard event codes:

- `"0 BOOTSTRAP"`: Initial connection after factory reset
- `"1 BOOT"`: Device boot/restart
- `"2 PERIODIC"`: Periodic inform
- `"M Reboot"`: Reboot method/trigger (indicates ACS-initiated reboot)
- `"M Download"`: Download method/trigger
- `"M ScheduleInform"`: ScheduleInform method/trigger
- `"M ValueChange"`: Value change notification
- `"M Reboot"`: Reboot method/trigger

## Implementation in Boardfarm

The boardfarm codebase implements the Reboot functionality through:

1. **GenieACS Device Class**: `boardfarm/boardfarm3/devices/genie_acs.py`
   - `Reboot()` method creates reboot tasks via NBI API

2. **Use Case Implementation**: `boardfarm-docsis/boardfarm3_docsis/use_cases/tr069.py`
   - `reboot()` function wraps the ACS Reboot call and waits for device to come back online

3. **BDD Step Definitions**: `boardfarm-bdd/tests/step_defs/reboot_steps.py`
   - Step definitions for BDD test scenarios

## Monitoring and Debugging

### GenieACS Logs

GenieACS logs can be found in:
- CWMP access logs: `/var/log/genieacs/genieacs-cwmp-access.log`
- NBI access logs: `/var/log/genieacs/genieacs-nbi-access.log`
- Debug logs: `/var/log/genieacs/genieacs-debug.yaml`

### TR-069 Proxy

A TR-069 MITM proxy is available at `boardfarm-bdd/raikou/components/router/resources/tr069-proxy.py` that can be used to monitor all TR-069 traffic between CPE and ACS.

**Usage:**
```bash
# The proxy logs all TR-069 messages:
# - CPE → ACS: Inform, TransferComplete, RebootResponse, etc.
# - ACS → CPE: Reboot, GetParameterValues, SetParameterValues, etc.
```

### Key Log Messages

When monitoring TR-069 traffic, you should see:

1. **CPE → ACS**: `Inform` RPC (initial connection)
2. **ACS → CPE**: `Reboot` RPC
3. **CPE → ACS**: `RebootResponse` RPC
4. **[CPE reboots...]**
5. **CPE → ACS**: `Inform` RPC (with event codes "1 BOOT" and "M Reboot")
6. **ACS → CPE**: `InformResponse` RPC
7. **[Optional] ACS → CPE**: `GetParameterValues` RPC (verification)

## Summary

When the "Reboot" button is clicked in the GenieACS UI:

1. **NBI API Call**: Creates a reboot task via `POST /devices/{cpe_id}/tasks?connection_request=`
2. **Connection Request**: GenieACS sends ConnectionRequest to CPE
3. **CPE Check-in**: CPE sends Inform message
4. **Reboot RPC**: ACS sends Reboot RPC with CommandKey
5. **Acknowledgment**: CPE responds with RebootResponse
6. **Reboot Execution**: CPE reboots
7. **Post-Reboot**: CPE reconnects and sends Inform with event codes "1 BOOT" and "M Reboot"
8. **Verification**: ACS may send follow-up RPCs to verify device state

The key TR-069 RPCs involved are:
- **ConnectionRequest** (triggered by `?connection_request=` parameter)
- **Inform** (from CPE to ACS)
- **Reboot** (from ACS to CPE)
- **RebootResponse** (from CPE to ACS)
- **Inform** (post-reboot, with event codes)
- **GetParameterValues** (optional, for verification)

