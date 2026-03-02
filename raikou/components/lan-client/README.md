# QoE Client Component

**Version:** qoe_client_0.01  
**Maintainer:** rjvisser@alottabits.com

Playwright-based QoE measurement container for the SD-WAN testbed. Simulates end-user behavior (browsing, streaming, conferencing) and measures perceived quality.

**Networking:** Test traffic via Raikou OVS (eth1 on lan-segment). Docker eth0 is management-only (SSH, port mapping).

**Reference:** `docs/QoE_Client_Implementation_Plan.md`, `docs/SDWAN_Testbed_Configuration.md`

## Features

- **Base:** `mcr.microsoft.com/playwright:v1.50.0-jammy` (Chromium, Firefox, WebKit)
- **SSH:** Boardfarm access on port 5003
- **Dante SOCKS v5:** Port 8080 (host 18090) — developer browser debugging via LAN path
- **Interface:** eth1 on lan-segment (192.168.10.10/24), gateway 192.168.10.1 — Raikou OVS
- **Passwords:** root/boardfarm, boardfarm/boardfarm (non-root user for browser execution)

## Build

```bash
cd raikou
docker build -t lan-client:qoe_client_0.01 -f components/lan-client/Dockerfile components/lan-client
```

## Usage

Requires Raikou to inject eth1. Use with `docker-compose-sdwan.yaml`:

```bash
docker compose -p boardfarm-bdd-sdwan -f docker-compose-sdwan.yaml up -d
```

**SSH access:** `ssh -p 5003 root@localhost` (password: boardfarm). The `PlaywrightQoEClient` driver should run Playwright scripts as user `boardfarm` (e.g. `su - boardfarm -c "..."`) since browsers dislike running as root.

**SOCKS proxy:** Configure browser to use `127.0.0.1:18090` as SOCKS v5 proxy to route traffic through the testbed LAN path.

## Files

| File              | Purpose                                      |
|-------------------|----------------------------------------------|
| `Dockerfile`      | Playwright + SSH + Dante + iperf3            |
| `resources/init`  | Wait for eth1, configure Dante, start SSH    |
