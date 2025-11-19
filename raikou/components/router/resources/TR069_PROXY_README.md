# TR-069 MITM Proxy Implementation

## Overview

This directory contains a TR-069 MITM (Man-in-the-Middle) proxy implementation that intercepts TR-069 traffic between the CPE and ACS (GenieACS) for debugging purposes.

## Current Implementation: Logging-Only Pass-Through

The proxy (`tr069-proxy.py`) is a **logging-only pass-through proxy** that:
- Intercepts all TR-069 traffic (port 7547) destined for ACS
- Forwards all messages without modification (pure pass-through)
- Logs all TR-069 RPCs and traffic for debugging purposes
- Identifies RPC types (Inform, Reboot, GetParameterValues, etc.) in logs

This proxy is useful for debugging TR-069 communication issues and monitoring traffic flow between CPE and ACS.

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
2. **Check Proxy Logs**: Should see requests being forwarded with RPC type identification
3. **Verify ACS Receives Messages**: Check GenieACS logs
4. **Test Reboot RPC**: Issue a Reboot RPC from ACS and verify it's logged

### Expected Behavior (Logging-Only Mode)

- All TR-069 messages should pass through unchanged
- Proxy logs should show:
  - Connection events
  - RPC types (Inform, Reboot, GetParameterValues, etc.)
  - Request/response sizes
  - Message previews (first 500 chars) at DEBUG level
- CPE should receive responses normally
- No message modification occurs
- No errors should occur

### Log Format

The proxy logs include:
- `INFO`: Connection events, RPC types, message sizes
- `DEBUG`: Message previews (first 500 chars of SOAP messages)
- `ERROR`: Connection errors, HTTP errors, proxy failures

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

