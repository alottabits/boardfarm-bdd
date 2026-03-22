# Physical CPE Testing

This example demonstrates automated testing of a **physical Raspberry Pi**
running prplOS as the home gateway device. All other testbed components
(router, ACS, DHCP, SIP, WAN, LAN) remain dockerized and orchestrated by
Raikou. The physical CPE connects to the Raikou OVS bridges via USB-Ethernet
dongles on the host machine.

## What It Demonstrates

- **Physical device integration** — real hardware CPE in an otherwise containerized testbed
- **Raikou OVS bridging to physical interfaces** — USB-Ethernet dongles patched into OVS
- **Same test interface** — identical Boardfarm use_cases and test scenarios as the dockerized CPE
- **TR-069/ACS management** — native prplOS TR-069 client with full TR-181 data model

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│                    rtr-wan (172.25.1.x)                     │
│   ┌──────┐  ┌──────┐  ┌──────┐  ┌────────┐                │
│   │ DHCP │  │ ACS  │  │ WAN  │  │ Router │                │
│   └──────┘  └──────┘  └──────┘  └───┬────┘                │
└──────────────────────────────────────┼─────────────────────┘
                                       │ cpe-rtr bridge
                              ┌────────┴────────┐
                              │  USB-Ethernet    │
                              │  (host dongle)   │
                              └────────┬────────┘
                                       │ WAN
                              ┌────────┴────────┐
                              │  Raspberry Pi   │
                              │  prplOS / OpenWrt│
                              └────────┬────────┘
                                       │ LAN
                              ┌────────┴────────┐
                              │  USB-Ethernet    │
                              │  (host dongle)   │
                              └────────┬────────┘
                              │ lan-cpe bridge   │
                              ┌────────┴────────┐
                              │  LAN container  │
                              └─────────────────┘
```

## Hardware Requirements

- Raspberry Pi 4 (4GB+ RAM recommended)
- prplOS firmware image (see [build guide](prplos-rpi-build-guide.md))
- **Two USB-Ethernet dongles** on the host machine:
  - One for the CPE WAN side → patched into `cpe-rtr` OVS bridge
  - One for the CPE LAN side → patched into `lan-cpe` OVS bridge

## Use Cases Exercised

The CPE use cases (UC-12347, UC-12348) run against the physical device once
the device class is configured. See `cpe-deviceclass-development.md` for the
RPi prplOS device class development plan.

## Quick Start

```bash
# 1. Identify USB-Ethernet dongles on the host
ip link show | grep enx

# 2. Start the testbed (uses config_openwrt.json for Raikou)
cd raikou
docker compose -f docker-compose-openwrt.yaml up -d

# 3. Install dependencies
pip install -e ".[all]"

# 4. Run tests
pytest --board-name prplos-rpi-1 \
       --env-config bf_config/boardfarm_env_example.json \
       --inventory-config bf_config/boardfarm_config_prplos_rpi.json \
       tests/
```

## Configuration

- **Raikou config:** `raikou/config_openwrt.json`
- **Docker Compose:** `raikou/docker-compose-openwrt.yaml`
- **USB dongle mapping:** Configured in `docker-compose-openwrt.yaml` under the `router` service (`ENABLE_NAT_ON=eth1,aux0`)

## Related Documentation

| Document | Description |
|---|---|
| [Testbed Topology](testbed-topology.md) | Network topology, OVS bridges, USB dongle mapping, and troubleshooting |
| [prplOS RPi Implementation](prplos-rpi-implementation.md) | RPi4 integration plan and completion status |
| [prplOS RPi Build Guide](prplos-rpi-build-guide.md) | Step-by-step prplOS firmware build for RPi4 |
| [prplOS RPi Console API](prplos-rpi-console-api.md) | Console API for Boardfarm device class |
| [CPE Device Class Development](cpe-deviceclass-development.md) | RPiPrplOSCPE device class plan |
