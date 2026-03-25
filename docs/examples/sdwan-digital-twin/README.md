# Dockerized SD-WAN Testing (Digital Twin)

This example demonstrates automated testing of SD-WAN / WAN Edge appliances
using a fully containerized "digital twin" testbed. A Linux Router with
FRR + StrongSwan acts as the reference DUT, validating test logic before
commercial hardware is involved. The template-based architecture ensures
test portability across vendors.

## What It Demonstrates

- **QoE verification** — end-user experience measurement (page load, streaming, conferencing) under controlled WAN conditions
- **Path steering validation** — DUT selects the optimal WAN path based on real-time link quality
- **Failover convergence** — sub-second failover between dual WAN links
- **VPN/overlay encryption** — IPsec IKEv2 tunnel establishment and integrity
- **Deterministic impairment** — calibrated `tc netem` profiles (latency, loss, jitter, bandwidth)
- **QoS contention** — iPerf3 background load injection for QoS priority validation under WAN saturation
- **TLS everywhere** — testbed CA/PKI, HTTPS/HTTP3, WSS conferencing

## Testbed Components

| Component | Description | Image |
|---|---|---|
| **LinuxSDWANRouter** | Digital twin DUT — FRR routing, BFD, PBR, StrongSwan IPsec | `sdwan-router:0.03` |
| **WAN1-TC / WAN2-TC** | Traffic controllers — dual-port `tc netem` impairment per WAN link | `traffic-controller:0.02` |
| **App Router** | North-side traffic routing between WAN links and application servers | `app-router:0.01` |
| **LAN QoE Client** | Playwright/Chromium browser for QoE measurement | `qoe-client:0.02` |
| **Productivity Server** | Nginx — HTTPS/HTTP3 web application server | `productivity-server:0.02` |
| **Streaming Server** | Nginx + MinIO — HLS/DASH video streaming | `streaming-server:0.02` |
| **Conferencing Server** | Node.js WebRTC/WSS conferencing simulation | `conf-server:0.02` |
| **IPsec Hub** | StrongSwan hub for IKEv2 tunnel termination | `ipsec-hub:0.01` |
| **MinIO** | S3-compatible object store for streaming content | `minio:latest` |
| **LAN Traffic Generator** | iPerf3 background load — LAN side | `traffic-gen:0.01` |
| **North Traffic Generator** | iPerf3 background load — north side (server) | `traffic-gen:0.01` |
| **Log Collector** | Centralized test log aggregation | `log-collector:0.01` |

## Network Topology

![Dual-WAN SD-WAN Testbed Topology](../../../Excalidraw/dual-wan-testbed-topology.svg)

All test traffic flows through **Raikou OVS bridges** (not Docker networks).
The default Docker network is management-only.

## Use Cases Exercised

| Use Case | Feature File |
|---|---|
| [UC-SDWAN-01 WAN Failover](../../../requirements/UC-SDWAN-01%20WAN%20Failover%20Maintains%20Application%20Continuity.md) | `tests/features/WAN Failover Maintains Application Continuity.feature` |
| [UC-SDWAN-02 Remote Worker Cloud App](../../../requirements/UC-SDWAN-02%20Remote%20Worker%20Accesses%20Cloud%20Application.md) | — (planned) |
| [UC-SDWAN-03 Video Conference QoE](../../../requirements/UC-SDWAN-03%20Video%20Conference%20Quality%20Under%20WAN%20Degradation.md) | — (planned) |
| [UC-SDWAN-04 Encrypted Overlay Tunnel](../../../requirements/UC-SDWAN-04%20SD-WAN%20Appliance%20Establishes%20Encrypted%20Overlay%20Tunnel.md) | — (planned) |
| [UC-SDWAN-05 Tunnel Survives Failover](../../../requirements/UC-SDWAN-05%20Encrypted%20Tunnel%20Survives%20WAN%20Failover.md) | — (planned) |
| [UC-SDWAN-06 QoS Priority Under WAN Contention](../../../requirements/UC-SDWAN-06%20QoS%20Priority%20Under%20WAN%20Contention.md) | `tests/features/QoS Priority Under WAN Contention.feature` |

## Quick Start

```bash
# 1. Generate testbed CA certificates (one-time)
(cd raikou/testbed-ca && ./generate-certs.sh)

# 2. Start the testbed
docker compose -p boardfarm-bdd-sdwan -f raikou/docker-compose-sdwan.yaml up -d

# 3. Install dependencies
pip install -e ".[all]"

# 4. Run tests
pytest --board-name sdwan-digital-twin \
       --env-config bf_config/boardfarm_env_sdwan.json \
       --inventory-config bf_config/boardfarm_config_sdwan.json \
       tests/
```

## Configuration

- **Raikou config:** `raikou/config_sdwan.json`
- **Docker Compose:** `raikou/docker-compose-sdwan.yaml`
- **Testbed CA:** `raikou/testbed-ca/` (see [Testbed CA Setup](testbed-ca-setup.md))
- **Boardfarm inventory:** `bf_config/boardfarm_config_sdwan.json`

## Scope

The framework is realized through Phase 3.5 (Digital Twin Hardening). See
[ADR-0001](../../adr/0001-scope-to-digital-twin-phase-3.5.md) for the scope
decision and deliverable inventory.

## Related Documentation

| Document | Description |
|---|---|
| [Architecture](architecture.md) | Full architecture overview and five-layer mapping |
| [Testbed Configuration](testbed-configuration.md) | Raikou/Docker Compose setup details |
| [Testbed CA Setup](testbed-ca-setup.md) | Certificate generation procedure |
| [Linux SD-WAN Router](linux-sdwan-router.md) | Digital twin DUT design (FRR + StrongSwan) |
| [QoE Client](qoe-client.md) | Playwright-based QoE measurement client |
| [Application Services](application-services.md) | North-side server designs |
| [Traffic Management](traffic-management.md) | TrafficController architecture |
| [Traffic Generator](traffic-generator.md) | iPerf3 background load generator |
| [App Router](app-router.md) | Split north-segment topology |
| [QoE Verification Brief](qoe-verification-brief.md) | Automated QoE verification approach |
| [Cross-Vendor API Analysis](cross-vendor-api-analysis.md) | WANEdgeDevice vendor mappings |

### Future Designs (Descoped)

| Document | Description |
|---|---|
| [Security Testing](future/security-testing.md) | MaliciousHost and security test scenarios |
