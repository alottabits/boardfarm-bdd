# TR-069 MITM Proxy Implementation

## Overview

This directory contains a TR-069 MITM (Man-in-the-Middle) proxy implementation that intercepts TR-069 traffic between the CPE and ACS (GenieACS).

## Current Implementation: Pass-Through Mode

The initial implementation (`tr069-proxy.py`) is a **pass-through proxy** that:
- Intercepts all TR-069 traffic (port 7547) destined for ACS
- Forwards messages without modification
- Logs all traffic for debugging

This allows testing that the proxy infrastructure works correctly before implementing message modification.

## Files

- `tr069-proxy.py`: Python HTTP proxy script
- `init`: Modified router initialization script (starts proxy and configures iptables)

## Network Flow

```
CPE (10.1.1.x) 
  → Router (NAT) 
  → iptables DNAT redirects to proxy (127.0.0.1:8754)
  → Proxy forwards to ACS (172.25.1.40:7547)
```

## Configuration

- **Proxy Port**: 8754 (changed from 87547 to avoid iptables-legacy port validation issues)
- **ACS Host**: 172.25.1.40
- **ACS Port**: 7547
- **Proxy Log**: `/var/log/tr069-proxy.log` in router container

## Deployment

The proxy is automatically deployed when the router container starts:

1. Proxy script is copied to `/opt/tr069-proxy.py` during container build
2. Init script starts the proxy in background
3. iptables DNAT rule redirects TR-069 traffic to proxy

## Testing

### Verify Proxy is Running

```bash
# Check if proxy process is running
docker exec router ps aux | grep tr069-proxy

# Check proxy logs
docker exec router tail -f /var/log/tr069-proxy.log

# Check if proxy is listening on port 8754
docker exec router netstat -tlnp | grep 8754
```

### Verify iptables Rule

```bash
# Check DNAT rule
docker exec router iptables -t nat -L PREROUTING -n -v | grep 7547
```

### Test TR-069 Communication

1. **Trigger CPE Inform**: Restart CPE or wait for periodic inform
2. **Check Proxy Logs**: Should see requests being forwarded
3. **Verify ACS Receives Messages**: Check GenieACS logs
4. **Test Download Task**: Create a download task via GenieACS UI/API

### Expected Behavior (Pass-Through Mode)

- All TR-069 messages should pass through unchanged
- Proxy logs should show requests and responses
- CPE should receive responses normally
- No errors should occur

## Next Steps: Message Modification

Once pass-through mode is verified, implement message modification:

1. Modify `remove_empty_targetfilename()` function in `tr069-proxy.py`
2. Parse SOAP XML in ACS responses
3. Remove empty `<TargetFileName></TargetFileName>` tags
4. Forward modified messages to CPE

## Troubleshooting

### Proxy Not Starting

- Check Python3 is available: `docker exec router python3 --version`
- Check script permissions: `docker exec router ls -l /opt/tr069-proxy.py`
- Check logs: `docker exec router cat /var/log/tr069-proxy.log`

### Traffic Not Being Redirected

- Verify iptables rule exists: `docker exec router iptables -t nat -L PREROUTING -n`
- Check proxy is listening: `docker exec router netstat -tlnp | grep 8754`
- Verify DNAT target is correct (should be 127.0.0.1:8754)

### Proxy Can't Reach ACS

- Test connectivity: `docker exec router ping -c 2 172.25.1.40`
- Test HTTP connection: `docker exec router curl -v http://172.25.1.40:7547`

### TR-069 Communication Broken

- Disable proxy temporarily: Comment out iptables rule and restart router
- Check if direct communication works without proxy
- Review proxy logs for errors

