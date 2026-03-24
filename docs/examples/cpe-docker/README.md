# Dockerized CPE Testing

This example demonstrates automated testing of a containerized home gateway
(PrplOS CPE) using Boardfarm with a fully dockerized testbed orchestrated by
Raikou.

## What It Demonstrates

- **TR-069/ACS management** — remote CPE configuration and monitoring via GenieACS
- **SIP voice testing** — one-way and two-way VoIP calls through the gateway
- **GUI testing** — automated ACS web interface testing with Playwright and StateExplorer
- **Configuration cleanup** — automatic restoration of device state after tests

## Testbed Components

| Component | Description | Image |
|---|---|---|
| **CPE** | PrplOS home gateway (TR-069 client) | `cpe-prplos:v1.2.0` |
| **Router** | ISP edge gateway with FRR routing and NAT | `router:v1.2.0` |
| **WAN** | Network services (HTTP, TFTP, FTP, DNS, proxy) | `wan:v1.2.0` |
| **ACS** | GenieACS TR-069 management server | `acs:v1.2.0` |
| **DHCP** | Kea DHCP server for network provisioning | `dhcp:v1.2.0` |
| **SIP Center** | Asterisk SIP server for voice testing | `sip:v1.2.0` |
| **LAN** | Test client device on LAN network | `lan:v1.2.0` |
| **Phones** | LAN phone, WAN phone, WAN phone 2 | `phone:v1.2.0` |

See [testbed-topology.md](testbed-topology.md) for the full network architecture.

## Use Cases Exercised

| Use Case | Feature File | Robot Suite |
|---|---|---|
| [UC-12347 Remote CPE Reboot](../../../requirements/UC-12347%20remote%20cpe%20reboot.md) | `tests/features/Remote CPE Reboot.feature` | `robot/tests/remote_cpe_reboot.robot` |
| [UC-12348 Voice Call](../../../requirements/UC-12348%20User%20makes%20a%20one-way%20call.md) | `tests/features/UC-12348 User makes a one-way call.feature` | `robot/tests/user_makes_one_way_call.robot` |
| [UC-ACS-GUI-01 Device Management](../../../requirements/UC-ACS-GUI-01%20ACS%20GUI%20Device%20Management.md) | `tests/features/ACS GUI Device Management.feature` | — |

## Quick Start

```bash
# 1. Start the testbed
docker compose -f raikou/docker-compose.yaml up -d

# 2. Install dependencies
pip install -e ".[all]"

# 3. Run pytest-bdd tests
pytest --board-name prplos-docker-1 \
       --env-config bf_config/boardfarm_env_example.json \
       --inventory-config bf_config/boardfarm_config_example.json \
       tests/

# 4. Run Robot Framework tests
bfrobot --board-name prplos-docker-1 \
        --env-config bf_config/boardfarm_env_example.json \
        --inventory-config bf_config/boardfarm_config_example.json \
        robot/tests/
```

## Configuration

- **Raikou config:** `raikou/config.json`
- **Docker Compose:** `raikou/docker-compose.yaml`
- **Boardfarm inventory:** `bf_config/boardfarm_config_example.json`
- **Boardfarm environment:** `bf_config/boardfarm_env_example.json`
- **Component configs:** `raikou/components/` (Kea DHCP, etc.)

## Related Documentation

| Document | Description |
|---|---|
| [Testbed Topology](testbed-topology.md) | Network architecture and OVS bridge layout |
| [ACS URL Discovery](acs-url-discovery.md) | How the CPE discovers the ACS URL via DHCP |
| [GenieACS Reboot Analysis](genieacs-reboot-analysis.md) | TR-069 flow for remote CPE reboot |
| [SIP Phone Configuration](sip-phone-configuration.md) | Voice testing setup |
| [ACS GUI Testing](ui-testing-guide.md) | GenieACS-specific GUI testing setup and use cases |
| [Log Locations](log-locations.md) | Where to find GenieACS and TR-069 logs |
| [Password Handling](password-handling.md) | Default password flow and cleanup |
