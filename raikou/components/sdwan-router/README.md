# SD-WAN Router Component

**Version:** sdwan_frr_0.01  
**Maintainer:** rjvisser@alottabits.com

Dual-WAN router container for the SD-WAN testbed. Extends the router pattern (FRR + SSH) with BFD echo-mode failover and metric-based static routes. All interfaces from Raikou OVS (`eth-lan`, `eth-wan1`, `eth-wan2`), NOT Docker network. Uses `network_mode: none`.

**Reference:** `docs/LinuxSDWANRouter_Implementation_Plan.md`, `docs/SDWAN_Testbed_Configuration.md`

## Features

- **Interfaces:** eth-lan (192.168.10.1/24), eth-wan1 (10.10.1.1/30), eth-wan2 (10.10.2.1/30)
- **FRR:** zebra, staticd, bfdd (BFD echo mode for sub-second failover)
- **BFD:** echo-receive-interval 100 ms, detect-multiplier 3 (~300 ms detection)
- **Static routes:** WAN1 metric 10 (primary), WAN2 metric 20 (backup)
- **Base:** ssh:v1.2.0
- **Password:** boardfarm

## Build

Requires the `ssh:v1.2.0` base image. Build from the `raikou` directory:

```bash
# Build ssh base first (if not already built)
docker compose -f docker-compose-openwrt.yaml build ssh_service

# Build sdwan-router
docker build -t sdwan-router:sdwan_frr_0.01 -f components/sdwan-router/Dockerfile components/sdwan-router
```

Or with docker compose (when `docker-compose-sdwan.yaml` exists):

```bash
docker compose -p boardfarm-bdd-sdwan -f docker-compose-sdwan.yaml build linux-sdwan-router
```

## Usage

The container expects Raikou to inject `eth-lan`, `eth-wan1`, and `eth-wan2`. It uses `network_mode: none` — no Docker management interface. Boardfarm accesses it via `docker exec`.

**Standalone test** (interfaces must be provided by the host or another mechanism):

```bash
docker run --rm -it --privileged --network none \
  -e LAN_IFACE=eth-lan -e WAN1_IFACE=eth-wan1 -e WAN2_IFACE=eth-wan2 \
  sdwan-router:sdwan_frr_0.01
```

For full testbed topology, use `docker-compose-sdwan.yaml` and `config_sdwan.json` (Phase 2).

## Interface Overrides

| Env var      | Default   | Description        |
|--------------|-----------|--------------------|
| `LAN_IFACE`  | eth-lan   | LAN interface name |
| `WAN1_IFACE` | eth-wan1  | WAN1 interface     |
| `WAN2_IFACE` | eth-wan2  | WAN2 interface     |

## Files

| File              | Purpose                                      |
|-------------------|----------------------------------------------|
| `Dockerfile`      | Image build (FRR, iproute2, iptables, etc.)   |
| `resources/frr.conf` | FRR config (interfaces, BFD, static routes) |
| `resources/daemons`  | FRR daemons (zebra, staticd, bfdd)          |
| `resources/init`    | Entrypoint: wait for interfaces, start FRR, sshd |
