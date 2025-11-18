# ACS-CPE Compatibility Investigation: Consolidated Findings

## Executive Summary

This document describes the incompatibility issues between GenieACS (Auto Configuration Server) and PrplOS CPE (Customer Premises Equipment) when using TR-069 Download RPCs, and the solution implemented using a Man-in-the-Middle (MITM) proxy.

**Status**: ✅ **RESOLVED** - MITM proxy successfully enables TR-069 communication between GenieACS and PrplOS CPE.

## Core Problem Statement

The testbed encountered failures when attempting to trigger firmware downloads via TR-069 Download RPCs. The failures manifested as:

1. **Download RPC Rejected**: GenieACS sends Download RPCs with optional parameters (e.g., empty `TargetFileName`, `FileSize`, `SuccessURL`, `FailureURL`), which PrplOS rejects due to strict validation, resulting in `FaultCode: 9002` (Invalid arguments).

## Key Incompatibility Issues

### 1. TargetFileName Parameter Conflict

**Issue**: GenieACS consistently includes the `TargetFileName` parameter in Download RPCs, even when empty (`<TargetFileName></TargetFileName>`). PrplOS's `cwmpd` binary performs strict validation and rejects RPCs with empty optional parameters.

**Root Cause**:
- GenieACS uses defensive coding (`|| ""`) to ensure `TargetFileName` is never undefined before XML serialization
- PrplOS interprets the presence of an empty `<TargetFileName>` tag as invalid, expecting either a non-empty value or complete omission
- TR-069 standard defines `TargetFileName` as optional, but implementations vary in handling empty values

### 2. PrplOS Parameter Support Limitations

**Supported Parameters** (via `tr069/ScheduleDownload` UBUS method):
- `CommandKey` (required)
- `FileType` (required)
- `URL` (required)
- `Username` (optional)
- `Password` (optional)
- `DelaySeconds` (optional)

**Not Supported**:
- `TargetFileName` (rejected if empty)
- `FileSize` (rejected if present)
- `SuccessURL` (rejected if empty)
- `FailureURL` (rejected if empty)

**Finding**: PrplOS's TR-069 implementation only supports a subset of the standard Download RPC parameters. The validation logic is hardcoded in the `cwmpd` binary with no configuration override available.

### 3. No Configuration Workaround

After thorough investigation of GenieACS source code, **no configuration option, preset, provision script, or virtual parameter exists** to prevent GenieACS from including empty `TargetFileName`:

- **Provision Scripts**: While provision scripts can omit the 4th argument (TargetFileName), GenieACS still passes `task.targetFileName || ""` from task creation code, ensuring it's always an empty string.
- **Virtual Parameters**: No virtual parameter exists to control Download RPC serialization behavior.
- **Presets**: Presets only control when provision scripts run, not how RPCs are serialized.
- **Configuration**: No GenieACS configuration option exists to control optional parameter serialization.

**Conclusion**: Source code modification or message interception is required to prevent empty `TargetFileName` from being included in Download RPCs.

## Mitigation Strategies Considered

### Strategy 1: CPE Adaptation
**Approach**: Modify PrplOS source code to tolerate empty optional parameters per TR-069 standard.

**Status**: Not suitable for testbed scenarios where we want to test PrplOS behavior as-is.

### Strategy 2: ACS Control via NBI API
**Approach**: Use GenieACS NBI API directly to create Download tasks with minimal payload.

**Status**: Still includes empty parameters due to GenieACS serialization logic.

### Strategy 3: GenieACS Source Code Modification
**Approach**: Directly modify GenieACS source code to conditionally include `TargetFileName` only when non-empty.

**Status**: High operational risk, breaks upgrade path, creates maintenance debt. Not recommended.

### Strategy 4: Man-in-the-Middle (MITM) Proxy ✅ **SELECTED**

**Approach**: Deploy an HTTP proxy between GenieACS and the CPE that intercepts TR-069 SOAP messages, removes empty/unsupported parameters, and forwards the modified messages.

**Status**: ✅ **IMPLEMENTED AND VERIFIED** - Successfully resolves TR-069 compatibility issues.

## Solution: MITM Proxy Implementation

### Overview

A Python HTTP proxy deployed on the router container intercepts TR-069 traffic between the CPE and ACS, modifies Download RPCs to remove unsupported parameters, and forwards the cleaned messages. This approach:

- ✅ **No GenieACS modification required** - Works with standard GenieACS distribution
- ✅ **No CPE configuration changes** - Transparent to PrplOS CPE
- ✅ **No source code changes** - Maintains testbed integrity
- ✅ **Verified working** - Download RPCs are accepted by PrplOS (`Status>1</Status>`)

### Network Topology

```text
CPE (10.1.1.x) → Router (NAT) → MITM Proxy (172.25.1.1:8754) → ACS (172.25.1.40:7547)
```

### Implementation Details

**Location**: `/opt/tr069-proxy.py` in router container

**Functionality**:
1. Intercepts HTTP POST requests (TR-069 uses POST for all RPCs)
2. Forwards CPE-initiated requests (Inform, TransferComplete) unchanged
3. Modifies ACS responses containing Download RPCs:
   - Removes empty `<TargetFileName>` tags (handles both namespace-qualified and unqualified)
   - Removes `<FileSize>` tags completely (PrplOS doesn't support this parameter)
   - Removes empty `<SuccessURL>` and `<FailureURL>` tags
   - Removes empty `<Username>` and `<Password>` tags (optional cleanup)
4. Forwards modified responses to CPE

**Traffic Redirection**: Uses `iptables` DNAT to redirect TR-069 traffic (port 7547) destined for ACS to the proxy (port 8754).

**Logging**: Comprehensive logging to `/var/log/tr069-proxy.log` including:
- Original and modified Download RPCs
- CPE responses (including fault codes)
- Connection details

### Verification

Proxy logs confirm successful modification:

```
ORIGINAL Download RPC:
<cwmp:Download>...<TargetFileName></TargetFileName><FileSize>153387270</FileSize>...</cwmp:Download>

MODIFIED Download RPC:
<cwmp:Download>...<CommandKey>...</CommandKey><FileType>...</FileType><URL>...</URL><DelaySeconds>0</DelaySeconds></cwmp:Download>

CPE RESPONSE:
<cwmp:DownloadResponse><Status>1</Status>...</cwmp:DownloadResponse>
```

The CPE accepts the modified Download RPC (`Status>1</Status>` indicates acceptance).

### Enabling/Disabling the MITM Proxy

#### Current Implementation (Always Enabled)

The MITM proxy is currently enabled by default in the router container's initialization script (`/opt/init`). The proxy starts automatically when the router container starts.

#### To Disable the MITM Proxy

**Option 1: Comment out proxy startup in init script**

Edit `/home/rjvisser/projects/req-tst/boardfarm-bdd/raikou/components/router/resources/init`:

```bash
# Comment out these lines (around line 127-149):
# # Start TR-069 MITM Proxy
# echo "Starting TR-069 MITM Proxy..."
# /opt/tr069-proxy.py > /var/log/tr069-proxy.log 2>&1 &
# PROXY_PID=$!
# echo "TR-069 MITM Proxy started with PID: $PROXY_PID"
# sleep 2
# # Configure iptables...
# if iptables -t nat -A PREROUTING ...; then
#     ...
# fi
```

Then rebuild the router container:
```bash
cd raikou
docker compose build router --no-cache
docker compose restart router
```

**Option 2: Stop proxy and remove iptables rule at runtime**

```bash
# Stop the proxy process
docker exec router pkill -f tr069-proxy.py

# Remove iptables DNAT rule
docker exec router iptables -t nat -D PREROUTING -p tcp --dport 7547 -d 172.25.1.40 -j DNAT --to-destination 172.25.1.1:8754

# Verify removal
docker exec router iptables -t nat -L PREROUTING -n -v | grep 7547
# Should show no matching rules
```

**Note**: After disabling, TR-069 communication will fail with `FaultCode: 9002` due to the original incompatibility issues.

#### To Re-enable the MITM Proxy

**Option 1: Restore init script and rebuild** (if using Option 1 above)

**Option 2: Start proxy and add iptables rule at runtime** (if using Option 2 above)

```bash
# Start the proxy
docker exec router /opt/tr069-proxy.py > /var/log/tr069-proxy.log 2>&1 &

# Add iptables DNAT rule
ROUTER_WAN_IP=$(docker exec router ip addr show eth1 | grep "inet " | awk '{print $2}' | cut -d/ -f1)
docker exec router iptables -t nat -A PREROUTING -p tcp --dport 7547 -d 172.25.1.40 -j DNAT --to-destination ${ROUTER_WAN_IP}:8754

# Verify
docker exec router ps aux | grep tr069-proxy
docker exec router iptables -t nat -L PREROUTING -n -v | grep 7547
```

#### Future Enhancement: Environment Variable Control

For easier control, the init script could be modified to check an environment variable:

```bash
# In init script:
if [ "${ENABLE_TR069_PROXY:-yes}" = "yes" ]; then
    # Start proxy and configure iptables
fi
```

Then control via docker-compose.yaml:
```yaml
router:
  environment:
    - ENABLE_TR069_PROXY=yes  # or "no" to disable
```

### Monitoring and Debugging

**Check proxy status**:
```bash
docker exec router ps aux | grep tr069-proxy
docker exec router netstat -tlnp | grep 8754
```

**View proxy logs**:
```bash
docker exec router tail -f /var/log/tr069-proxy.log
```

**Check iptables redirection**:
```bash
docker exec router iptables -t nat -L PREROUTING -n -v | grep 7547
```

**Verify TR-069 communication**:
- Check ACS UI for successful Download task completion
- Check CPE logs for Download RPC acceptance
- Monitor proxy logs for modification activity

## Technical Details

### GenieACS Serialization Logic

**Location**: `/opt/genieacs/lib/soap.ts`, function `Download(methodRequest)`

**Current Implementation**:
```typescript
function Download(methodRequest): string {
  return `<cwmp:Download>...
    <TargetFileName>${encodeEntities(methodRequest.targetFileName || "")}</TargetFileName>
    <FileSize>${methodRequest.fileSize || "0"}</FileSize>
    ...
  </cwmp:Download>`;
}
```

The defensive coding (`|| ""`) ensures empty tags are always included, which PrplOS rejects.

### PrplOS Validation

PrplOS's `cwmpd` binary performs strict validation:
- Rejects empty optional parameters
- Rejects unsupported parameters (e.g., `FileSize`)
- Returns `FaultCode: 9002` (Invalid arguments) when validation fails

### Proxy Modification Logic

The proxy uses regex patterns to remove problematic tags:

```python
# Remove empty TargetFileName (handles both namespace-qualified and unqualified)
response_text = re.sub(r'<cwmp:TargetFileName>\s*</cwmp:TargetFileName>', '', response_text)
response_text = re.sub(r'<TargetFileName>\s*</TargetFileName>', '', response_text)

# Remove FileSize completely (PrplOS doesn't support this parameter)
response_text = re.sub(r'<cwmp:FileSize>.*?</cwmp:FileSize>', '', response_text, flags=re.DOTALL)

# Remove empty SuccessURL and FailureURL
response_text = re.sub(r'<cwmp:SuccessURL>\s*</cwmp:SuccessURL>', '', response_text)
response_text = re.sub(r'<cwmp:FailureURL>\s*</cwmp:FailureURL>', '', response_text)
```

## Conclusion

The MITM proxy approach successfully resolves the TR-069 compatibility issues between GenieACS and PrplOS:

1. ✅ **Download RPCs are accepted** - PrplOS responds with `Status>1</Status>` (accepted)
2. ✅ **No source code modifications** - Works with standard GenieACS and PrplOS distributions
3. ✅ **Transparent operation** - No configuration changes required on ACS or CPE
4. ✅ **Easy to enable/disable** - Can be controlled via init script or runtime commands
5. ✅ **Comprehensive logging** - Full visibility into TR-069 message flow

The solution maintains testbed integrity while enabling successful TR-069 communication for firmware upgrades and configuration file transfers.

## References

- TR-069 Standard: ETSI TS 102 824
- GenieACS Documentation: <https://genieacs.com/docs/>
- PrplOS Source: <https://gitlab.com/prpl-foundation/prplos/prplos>
- Implementation: `/home/rjvisser/projects/req-tst/boardfarm-bdd/raikou/components/router/resources/tr069-proxy.py`

## Document History

- **Updated**: 2025-11-18 - Streamlined document, highlighted MITM solution success, added enable/disable instructions
- **Consolidated**: 2025-01-XX - Initial consolidation of multiple investigation documents
