# TrafficGenerator Component

**Date:** March 25, 2026
**Status:** Implemented (Phase 1–3 complete)
**Related:** [SD-WAN testing architecture](architecture.md), [Traffic management components](traffic-management.md)

---

## 1. Overview

### Purpose

The **Traffic Generator** injects calibrated background load into the testbed to create the traffic contention required for QoS validation. Without a controlled background load, queue pressure cannot be created and QoS tests (DSCP prioritisation, LLQ effectiveness, shaper/policer verification) cannot produce meaningful results.

The Traffic Generator is used exclusively as a **background load source** — it does not measure application quality (that is the `QoEClient`'s role). It answers: *"Is the correct amount of traffic, at the correct DSCP marking, flowing across the path?"*

### Key Design Principles

1. **Test Portability:** Use cases depend on the `TrafficGenerator` template only. They never call iPerf3 or Trex CLIs directly.
2. **Async Model:** `start_traffic()` is non-blocking and returns a `flow_id`. The test injects load, performs QoE measurement, then calls `stop_traffic(flow_id)` to retrieve results and tear down.
3. **Multi-flow per Instance:** Each `TrafficGenerator` device can manage multiple concurrent traffic flows tracked by `flow_id`, enabling complex contention scenarios.
4. **Self-contained Containers:** Each `traffic-gen` container runs its own iPerf3 server pool (ports 5201–5210) and client capabilities. No dependency on other containers for traffic reception.
5. **DSCP Transparency:** The generator marks traffic with a caller-specified DSCP value. The DUT's QoS policy is what re-marks or preserves it.

### Current Topology

Two `traffic-gen` containers are deployed:

```
                          ┌────────────┐
                          │ linux-sdwan│
[lan-traffic-gen] ──eth1──│   -router  │──eth-wan1──[wan1-tc]──[app-router]──[north-traffic-gen]
  192.168.10.20           │ (DUT)      │                                        172.16.0.25
  lan-segment             └────────────┘                                       north-segment
```

- **`lan-traffic-gen`** — LAN-side, generates upstream traffic through the DUT
- **`north-traffic-gen`** — North of the app-router, receives upstream traffic and can send downstream

This setup supports UC-SDWAN-06 (QoS Priority Under WAN Contention) where LAN-generated traffic saturates the WAN link while the QoE client measures application quality.

> **Scope note:** The current topology supports LAN-initiated upstream contention. North-initiated downstream traffic to the LAN is not supported because the app-router uses CONNMARK-based policy routing designed for symmetric return traffic only. For future use cases requiring per-WAN saturation or downstream injection, additional `traffic-gen` instances can be placed on the `north-wan1` and `north-wan2` segments.

---

## 2. Architecture & Components

### 2.1 Boardfarm Template

**Location:** `boardfarm3/templates/traffic_generator.py`

```python
@dataclass
class TrafficSpec:
    destination: str
    bandwidth_mbps: float
    protocol: str = "udp"
    dscp: int = 0
    duration_s: int = 30
    parallel_streams: int = 1
    port: int | None = None  # auto-assigned from server pool when None

@dataclass
class TrafficResult:
    sent_mbps: float = 0.0
    received_mbps: float = 0.0
    loss_percent: float = 0.0
    jitter_ms: float | None = None
    dscp_marking: int = 0

class TrafficGenerator(ABC):
    @abstractmethod
    def start_traffic(self, spec: TrafficSpec) -> str: ...  # returns flow_id
    @abstractmethod
    def stop_traffic(self, flow_id: str) -> TrafficResult: ...
    @abstractmethod
    def stop_all_traffic(self) -> dict[str, TrafficResult]: ...
    @abstractmethod
    def run_traffic(self, spec: TrafficSpec) -> TrafficResult: ...
    @property
    @abstractmethod
    def server_ip(self) -> str: ...
    @property
    @abstractmethod
    def active_flows(self) -> list[str]: ...
```

### 2.2 Implementation Types

| Testbed Type | Implementation Class | Underlying Tool | Connection |
| :--- | :--- | :--- | :--- |
| **Functional (Docker/Raikou)** | `IperfTrafficGenerator` | iPerf3 | SSH into container |
| **External Linux host (VM or physical)** | `IperfTrafficGenerator` | iPerf3 | SSH into host |
| **Dedicated appliance (pre-production)** | `TrexTrafficGenerator` | Cisco TRex | REST API |

### 2.3 iPerf3 Server Pool

Each `traffic-gen` container runs **10 iPerf3 server instances** on ports 5201–5210. This overcomes iPerf3's limitation of one client per server process and enables multiple concurrent inbound flows.

The server pool is started by the container init script at boot and verified by `IperfTrafficGenerator._ensure_server_pool()` during Boardfarm device boot.

---

## 3. Implementation Details

### 3.1 Docker Container (`traffic-gen`)

**Location:** `boardfarm-bdd-components/components/traffic-gen/`

**Dockerfile** — based on the `ssh:v1.3.0` base image:

```dockerfile
FROM ghcr.io/alottabits/test-components/ssh:v1.3.0
RUN apt-get update && apt-get install -y --no-install-recommends \
        iperf3 iproute2 iputils-ping net-tools \
    && rm -rf /var/lib/apt/lists/*
EXPOSE 22 5201-5210
COPY resources/init /usr/local/bin/init
RUN chmod +x /usr/local/bin/init
CMD ["/usr/local/bin/init"]
```

**Init script** waits for the Raikou-injected OVS interface (`eth1`), adds static routes for remote testbed subnets via the OVS gateway, starts the iPerf3 server pool, and launches SSHD.

### 3.2 Network Connectivity Pattern

The containers use Docker networking for **SSH management** (Boardfarm connects via mapped SSH ports) and Raikou OVS bridges for **test traffic**. The init script ensures test traffic uses the OVS path by adding explicit routes:

```bash
# Environment variables from docker-compose:
#   TG_GATEWAY      — OVS-side gateway for test traffic routing
#   TG_REMOTE_NETS  — comma-separated remote subnets to route via TG_GATEWAY

IFS=',' read -ra NETS <<< "$TG_REMOTE_NETS"
for net in "${NETS[@]}"; do
    ip route add "$net" via "$TG_GATEWAY" dev "$IFACE"
done
```

### 3.3 Driver Implementation

**Location:** `boardfarm3/devices/iperf_traffic_generator.py`

Key features of `IperfTrafficGenerator`:
- Inherits `LinuxDevice` (SSH console) and `TrafficGenerator` (abstract interface)
- Manages multiple concurrent flows via `_flows` dict keyed by `flow_id`
- Auto-allocates iPerf3 server ports from the pool (5201–5210)
- Starts iPerf3 clients in background with `nohup` and JSON logging
- Parses iPerf3 JSON output for `TrafficResult`

### 3.4 DSCP Marking

iPerf3 sets the **IP ToS byte** via `--tos`. The DSCP value occupies the top 6 bits:

```
ToS = DSCP << 2
```

| DSCP Name | DSCP Value | ToS Value | Traffic Class |
| :--- | :--- | :--- | :--- |
| Best Effort (BE) | 0 | 0 | Default |
| AF41 | 34 | 136 | Video (bulk background) |
| EF | 46 | 184 | Voice (priority) |

### 3.5 Async Traffic Model

`start_traffic()` is non-blocking by design:

```python
flow_id = tg_use_cases.saturate_wan_link(
    source=lan_traffic_gen,
    destination=north_traffic_gen,
    link_bandwidth_mbps=100,
    dscp=0,
)
# QoE measurement while background load is active
result = qoe_use_cases.measure_conferencing(client, conf_server)
assert result.mos >= 3.5
# Stop and collect traffic results
tg_result = tg_use_cases.stop_traffic(lan_traffic_gen, flow_id)
```

---

## 4. Configuration

### 4.1 Boardfarm Inventory (`bf_config_sdwan.json`)

```json
{
    "name": "lan_traffic_gen",
    "type": "iperf_traffic_generator",
    "connection_type": "authenticated_ssh",
    "ipaddr": "localhost",
    "port": 5008,
    "username": "root",
    "password": "boardfarm",
    "simulated_ip": "192.168.10.20"
},
{
    "name": "north_traffic_gen",
    "type": "iperf_traffic_generator",
    "connection_type": "authenticated_ssh",
    "ipaddr": "localhost",
    "port": 5009,
    "username": "root",
    "password": "boardfarm",
    "simulated_ip": "172.16.0.25"
}
```

### 4.2 Raikou Network (`raikou/config_sdwan.json`)

```json
"lan-traffic-gen": [
    { "bridge": "lan-segment", "iface": "eth1", "ipaddress": "192.168.10.20/24", "gateway": "192.168.10.1" }
],
"north-traffic-gen": [
    { "bridge": "north-segment", "iface": "eth1", "ipaddress": "172.16.0.25/24", "gateway": "172.16.0.254" }
]
```

### 4.3 Docker Compose (`docker-compose-sdwan.yaml`)

Both containers use SSH port mapping and environment variables for OVS routing:

```yaml
lan-traffic-gen:
    image: ghcr.io/alottabits/test-components/traffic-gen:0.01
    ports: ["5008:22"]
    environment:
        - TG_GATEWAY=192.168.10.1
        - TG_REMOTE_NETS=172.16.0.0/24
    privileged: true
```

### 4.4 Use Cases (`boardfarm3/use_cases/traffic_generator.py`)

| Function | Description |
| :--- | :--- |
| `get_traffic_generator(name)` | Discover a TrafficGenerator by name from the device manager |
| `start_traffic(gen, spec)` | Start a non-blocking flow, returns `flow_id` |
| `stop_traffic(gen, flow_id)` | Stop a flow and return `TrafficResult` |
| `stop_all_traffic(gen)` | Stop all flows on a generator |
| `saturate_wan_link(source, dest, bw, ...)` | Convenience: start background saturation flow |
| `start_asymmetric_load(up, down, ...)` | Start bidirectional flows |
| `stop_all_generators(*gens)` | Bulk teardown across generators |

---

## 5. BDD Integration

### 5.1 Feature File

**Location:** `tests/features/QoS Priority Under WAN Contention.feature`

The feature implements UC-SDWAN-06 with reusable steps:

- `Given traffic generators are available on both sides of the appliance`
- `When network operations starts {bandwidth} Mbps of best-effort upstream background traffic through the appliance`
- `When network operations stops the upstream background traffic`

These steps complement existing SD-WAN steps (appliance operational, network conditions, QoE session, SLO assertion).

### 5.2 Step Definitions

**Location:** `tests/step_defs/sdwan_steps.py`

Three new step definitions delegate to `boardfarm3.use_cases.traffic_generator`:

| Step | Use Case Function |
| :--- | :--- |
| `traffic generators are available...` | `get_traffic_generator("lan_traffic_gen")`, `get_traffic_generator("north_traffic_gen")` |
| `starts {N} Mbps of best-effort upstream...` | `saturate_wan_link(source, dest, ...)` |
| `stops the upstream background traffic` | `stop_traffic(gen, flow_id)` |

### 5.3 Cleanup Fixture

An autouse fixture `cleanup_traffic_generators_after_scenario` in `tests/conftest.py` stops all active flows on both traffic generators after each scenario, ensuring clean state even if the test fails mid-scenario.

---

## 6. Future Expansion

### Per-WAN Traffic Generators

For use cases requiring directional WAN saturation (e.g., saturating WAN1 while WAN2 remains clear), additional `traffic-gen` instances can be placed on:

- `north-wan1` segment (between WAN1 TC and app-router)
- `north-wan2` segment (between WAN2 TC and app-router)

This would enable scenarios like:
- Selective WAN path degradation via traffic (not impairment)
- Asymmetric per-WAN contention profiles
- North-initiated downstream traffic to the LAN (requires app-router routing changes)

### VM Migration

`IperfTrafficGenerator` requires no code changes for VM deployment — only the inventory config changes (real IP address instead of `localhost`, direct SSH port instead of mapped port).
