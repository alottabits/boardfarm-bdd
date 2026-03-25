# Architecture Overview — WAN Edge Appliance Testing Framework

| Field        | Value                                    |
| ------------ | ---------------------------------------- |
| Status       | Approved                                 |
| Author(s)    | rjvisser                                 |
| Date         | 2026-03-20                               |
| Stakeholders | Test engineers, architects, contributors |

## 1. Introduction and Goals

This document describes the architecture of the WAN Edge Appliance Testing Framework — a Boardfarm-based system for validating SD-WAN and SASE appliances through automated QoE, path steering, and security testing.

The framework uses a **Linux Router "digital twin"** as a reference DUT, providing a fully containerised testbed that validates test logic before commercial hardware is involved. The template-based architecture ensures test portability: test scenarios depend on abstract interfaces, not vendor-specific implementations.

### Requirements Overview

1. **QoE Verification:** Measure end-user experience (page load, streaming, conferencing) under controlled network conditions.
2. **Path Steering Validation:** Verify the DUT selects the optimal WAN path based on real-time link quality.
3. **Failover Convergence:** Measure and assert sub-second failover between WAN paths.
4. **Testbed Portability:** Swap the DUT (Linux Router → commercial appliance) without modifying test scenarios.
5. **Deterministic Impairment:** Apply calibrated network profiles (latency, loss, jitter, bandwidth) to WAN links.
6. **VPN/Overlay Encryption:** Validate IPsec tunnel establishment and integrity.

### Quality Goals

| Priority | Quality attribute | Scenario |
| --- | --- | --- |
| 1 | Portability | Replacing the Linux Router DUT with a commercial appliance requires only a new device class and inventory config — zero test scenario changes |
| 2 | Repeatability | Running the same test suite three consecutive times produces consistent pass/fail results |
| 3 | Isolation | Each test scenario starts from a known baseline; teardown restores all device state automatically |

### Stakeholders

| Role | Concern |
| --- | --- |
| Test engineer | Writing and running WAN Edge test scenarios |
| Framework architect | Maintaining template interfaces and the five-layer architecture |
| DevOps / Lab engineer | Deploying and maintaining the Raikou-orchestrated testbed |

### Scope Decision

The framework has been realized through Phase 3.5 (Digital Twin Hardening). The `TrafficGenerator` (iPerf3 background load) has since been implemented — see [traffic-generator.md](traffic-generator.md). Remaining items from Phases 4 (QoS shaping, firewall, security tooling, MaliciousHost) and 5 (commercial DUT integration) are not pursued at this time. See [ADR-0001](../../adr/0001-scope-to-digital-twin-phase-3.5.md) for the full rationale and deliverable inventory.

### Related Documents

**Component Design References**

| Document | Description |
| :--- | :--- |
| [Linux SD-WAN Router](linux-sdwan-router.md) | Linux-based DUT: FRR routing, BFD echo-mode failover, PBR, StrongSwan IPsec |
| [QoE Client](qoe-client.md) | Playwright-based QoE measurement client: `QoEResult`, MOS calculation, HTTPS/H3 |
| [Application Services](application-services.md) | North-side target services (Productivity, Streaming, Conferencing) with TLS |
| [Traffic Management](traffic-management.md) | `TrafficController`, `ImpairmentProfile`, `inject_transient()`, and the `tc netem` interface |

**Testbed Configuration & Operations**

| Document | Description |
| :--- | :--- |
| [Testbed Configuration](testbed-configuration.md) | Raikou config, Docker Compose, OVS topology, IP addressing, Boardfarm config, startup |
| [Testbed CA Setup](testbed-ca-setup.md) | Root CA generation and certificate distribution for HTTPS, HTTP/3, WSS, StrongSwan IKEv2 |

**Framework Architecture**

| Document | Description |
| :--- | :--- |
| [Boardfarm Five-Layer Model](../../architecture/boardfarm-five-layer-model.md) | Five-layer Boardfarm framework: System Use Cases → Test Definitions → Step Defs/Keywords → Boardfarm Use Cases → Templates |

**Decision Records**

| ID | Decision | Status |
| --- | --- | --- |
| [ADR-0001](../../adr/0001-scope-to-digital-twin-phase-3.5.md) | Scope to Digital Twin (Phase 3.5) | Accepted |

**Implemented Design Documents**

| Document | Description |
| :--- | :--- |
| [Traffic Generator](traffic-generator.md) | iPerf3 background load generator — `lan-traffic-gen` and `north-traffic-gen` containers deployed for QoS contention (UC-SDWAN-06) |

**Retained Design Documents (not pursued, kept for reference)**

| Document | Description |
| :--- | :--- |
| [Security Testing](future/security-testing.md) | `MaliciousHost` template, `LinuxMaliciousHost` container, `security_use_cases.py`, and security test scenarios (descoped — see ADR-0001) |

---

## 2. Constraints

- **No commercial DUT hardware available.** All validation uses the Linux Router digital twin.
- **Container-only testbed.** All components run as Docker containers orchestrated by Raikou with OVS bridges. No KVM or bare-metal required.
- **Linux `tc` egress-only constraint.** `tc netem` operates on egress only. The `LinuxTrafficController` avoids this limitation by design: each TrafficController container has two ports (one facing the DUT, one facing the north-side network). Applying `tc netem` on the egress of each port impairs traffic in both directions without requiring IFB (Intermediate Functional Block) devices.
- **Chromium QUIC trust.** Chromium's `--ignore-certificate-errors` flag does not apply to the BoringSSL QUIC stack. HTTP/3 requires proper CA trust via the NSS database.

---

## 3. Context and Scope

### Business Context

The enterprise WAN edge has evolved from simple routing to intelligent SD-WAN and SASE. Verification must move beyond basic connectivity to encompass application performance, traffic intelligence, security efficacy, and user experience.

The framework targets market-leading WAN Edge platforms:

- **Cisco Catalyst 8000 Series (Viptela):** IOS-XE based SD-WAN stack.
- **Fortinet FortiGate:** ASIC-accelerated path steering and NGFW convergence.
- **VMware SD-WAN (Velocloud):** Dynamic Multi-Path Optimization (DMPO).
- **Palo Alto ION (Prisma SD-WAN):** App-defined networking (Layer 7 focus).
- **HPE Aruba EdgeConnect (Silver Peak):** Path conditioning (FEC, Packet Order Correction).

Before validating commercial appliances, the testbed validates itself using a Linux Router digital twin.

### Technical Context

The testing strategy is built on four pillars:

1. **Quality of Experience (Outcome):** Does the user perceive the network as good?
2. **Quality of Service (Mechanism):** Is traffic prioritized correctly?
3. **Path Steering (Intelligence):** Is the best link chosen dynamically?
4. **Security (Protection):** Is the edge secure against threats without compromising performance?

The current implementation covers QoE, Path Steering, and VPN/Overlay Encryption. QoS contention testing and active security threat emulation are designed but not implemented (see [ADR-0001](../../adr/0001-scope-to-digital-twin-phase-3.5.md)).

---

## 4. Solution Strategy

Portability across DUTs is enforced by the **`WANEdgeDevice` Boardfarm template**, which is the single abstraction boundary between test logic and vendor-specific implementations. All other testbed components follow the same pattern: abstract template → concrete device class.

Key architectural decisions:

- **Container-first development.** Each component is built and validated as a Docker container before integration into the Raikou topology.
- **Five-layer Boardfarm architecture.** System Use Cases (Layer 0) → Test Definitions (Layer 1) → Step Defs/Keywords (Layer 2, thin wrappers) → Boardfarm Use Cases (Layer 3, business logic) → Device Templates (Layer 4). Business logic lives exclusively in Layer 3 use cases.
- **Dual WAN topology.** Two independent WAN paths with per-link impairment control via dedicated `TrafficController` containers.
- **Testbed CA/PKI.** A shared `easy-rsa` root CA enables HTTPS, HTTP/3, WSS, and IKEv2 across all testbed components.

---

## 5. Building Block View

### Level 1 — System Components

| Component | Boardfarm Template | Implementation | Purpose |
| :--- | :--- | :--- | :--- |
| **Linux SD-WAN Router** | `WANEdgeDevice` | `LinuxSDWANRouter` | DUT: FRR routing, BFD failover, PBR, StrongSwan IPsec |
| **WAN1 Traffic Controller** | `TrafficController` | `LinuxTrafficController` | `tc netem` impairment on WAN1 path |
| **WAN2 Traffic Controller** | `TrafficController` | `LinuxTrafficController` | `tc netem` impairment on WAN2 path |
| **LAN QoE Client** | `QoEClient` | `PlaywrightQoEClient` | Playwright browser automation for QoE measurement |
| **Productivity Server** | `ProductivityServer` | `NginxProductivityServer` | Mock SaaS (HTTPS/H3) |
| **Streaming Server** | `StreamingServer` | `NginxStreamingServer` | HLS video via MinIO content origin |
| **Conferencing Server** | `ConferencingServer` | `WebRTCConferencingServer` | pion WebRTC Echo (WSS) |
| **MinIO Content Store** | — | MinIO S3 | HLS manifest and segment storage |
| **App-Router** | — | CONNMARK policy router | Symmetric return routing across per-WAN north-side networks |
| **IPsec Hub** | — | StrongSwan | IKEv2 responder for DUT VPN tunnel |
| **Log Collector** | — | Fluent Bit | Unified timestamped logging from all containers |

### Level 2 — Boardfarm Device Templates

All SD-WAN test cases depend on abstract template interfaces. Test cases import templates only — never concrete device classes.

#### `WANEdgeDevice` Template

**Location:** `boardfarm3/templates/wan_edge.py`

The central DUT abstraction. Enables the Linux Router to serve as a drop-in placeholder for commercial SD-WAN appliances.

```python
@dataclass
class PathMetrics:
    latency_ms: float
    jitter_ms: float
    loss_percent: float
    link_name: str

@dataclass
class LinkStatus:
    name: str
    state: str          # "up" | "down" | "degraded"
    ip_address: str

@dataclass
class RouteEntry:
    destination: str
    gateway: str
    interface: str
    metric: int

class WANEdgeDevice(ABC):
    """Abstract interface for WAN Edge / SD-WAN appliances.

    Implementations: LinuxSDWANRouter.
    Designed for: CiscoC8000DUT, FortiGateDUT, VelocloudDUT.
    """

    @property
    @abstractmethod
    def nbi(self): ...

    @property
    @abstractmethod
    def gui(self): ...

    @property
    @abstractmethod
    def console(self): ...

    @abstractmethod
    def get_active_wan_interface(self, flow_dst: str | None = None, via: str = "console") -> str:
        """Return the logical WAN label currently forwarding traffic.

        Returns a key from the inventory wan_interfaces mapping (e.g. "wan1"),
        never a physical interface name. The device class performs the
        physical-to-logical reverse lookup.
        """

    @abstractmethod
    def get_wan_path_metrics(self, via: str = "console") -> dict[str, PathMetrics]:
        """Return per-link quality metrics as measured by the device."""

    @abstractmethod
    def get_wan_interface_status(self, via: str = "console") -> dict[str, LinkStatus]:
        """Return UP/DOWN/degraded state for each WAN interface."""

    @abstractmethod
    def get_routing_table(self, via: str = "console") -> list[RouteEntry]:
        """Return the current forwarding/routing table."""

    @abstractmethod
    def apply_policy(self, policy: dict, via: str = "nbi") -> None:
        """Apply a routing or SD-WAN policy (PBR rule, SLA threshold)."""

    @abstractmethod
    def remove_policy(self, name: str, via: str = "nbi") -> None:
        """Remove a previously applied policy by name."""

    @abstractmethod
    def bring_wan_down(self, label: str, via: str = "console") -> None:
        """Bring a WAN interface down (cable unplug simulation)."""

    @abstractmethod
    def bring_wan_up(self, label: str, via: str = "console") -> None:
        """Bring a WAN interface up (restore after bring_wan_down)."""

    @abstractmethod
    def power_cycle(self) -> None:
        """Power cycle (reboot) the device."""

    @abstractmethod
    def get_telemetry(self, via: str = "nbi") -> dict:
        """Return a snapshot of device telemetry (uptime, CPU, etc.)."""
```

`LinuxSDWANRouter` implements this via `ip route get`, `ip -j link show`, `ping`, FRR `vtysh`, and `ip -j route show` over SSH. All methods resolve physical interface names to logical labels via the `wan_interfaces` inventory mapping.

#### `QoEClient` Template

**Location:** `boardfarm3/templates/qoe_client.py`

Abstracts application-level measurement. The `QoEResult` dataclass lives in `boardfarm3/lib/qoe.py` (shared schema layer).

```python
@dataclass
class QoEResult:
    ttfb_ms: float | None = None
    load_time_ms: float | None = None
    startup_time_ms: float | None = None
    rebuffer_ratio: float | None = None
    latency_ms: float | None = None
    jitter_ms: float | None = None
    packet_loss_pct: float | None = None
    mos_score: float | None = None
    protocol: str | None = None       # "http/1.1", "h2", "h3"
    success: bool = True

class QoEClient(ABC):
    @property
    @abstractmethod
    def ip_address(self) -> str: ...

    @abstractmethod
    def measure_productivity(self, url: str, scenario: str = "page_load") -> QoEResult: ...

    @abstractmethod
    def measure_streaming(self, stream_url: str, duration_s: int = 30) -> QoEResult: ...

    @abstractmethod
    def measure_conferencing(self, session_url: str, duration_s: int = 60) -> QoEResult: ...
```

`PlaywrightQoEClient` uses Playwright navigation timing API and WebRTC `getStats()`. MOS R-Factor calculation lives in `lib/qoe.py`.

#### `TrafficController` Template

**Location:** `boardfarm3/templates/traffic_controller.py`

See [Traffic_Management_Components_Architecture.md](traffic-management.md) for the full interface. Key methods: `set_impairment_profile()`, `clear()`, `inject_transient()`, and per-interface variants.

#### Application Server Templates

**`ProductivityServer`** (`boardfarm3/templates/productivity_server.py`): `get_service_url()`, `set_response_delay()`, `set_content_size()`.

**`StreamingServer`** (`boardfarm3/templates/streaming_server.py`): `get_manifest_url()`, `list_available_bitrates()`, `ensure_content_available()`.

**`ConferencingServer`** (`boardfarm3/templates/conferencing_server.py`): `start_session()`, `get_session_stats()`.

See [application-services-design.md](application-services.md) for implementation details.

---

## 6. Runtime View

### QoE Measurement Flow

```
Feature File (Gherkin)
  └─► Step Definition (thin wrapper)
        └─► use_cases/qoe.py  (SLO assertions, R-Factor calculation)
              └─► QoEClient template
                    └─► PlaywrightQoEClient (device class)
```

MOS R-Factor calculation and SLO threshold comparisons live in `lib/qoe.py` and `use_cases/qoe.py`. Step definitions never contain QoE math.

### Failover Convergence Measurement

Sub-second failover validation correlates four timestamps:

- **T0:** Impairment injected on the primary WAN link
- **T1:** DUT detects failure (BFD timeout at 300 ms)
- **T2:** DUT switches active path to backup link
- **T3 - T0:** Total convergence time (the asserted metric)

Implemented in `use_cases/wan_edge.py` via `measure_failover_convergence()`, which combines `inject_blackout()` with polling of `WANEdgeDevice.get_active_wan_interface()`.

### WAN Edge Use Case Architecture

```
Feature File (Gherkin)
  └─► Step Definition (thin wrapper)
        └─► use_cases/wan_edge.py  (path assertions, policy verification)
              └─► WANEdgeDevice template
                    └─► LinuxSDWANRouter (device class)
```

Key use-case functions in `wan_edge.py`:

| Function | Purpose |
| :--- | :--- |
| `assert_active_path()` | Verify DUT forwards on the expected WAN interface |
| `assert_path_steers_on_impairment()` | Inject blackout and verify fallback path selection |
| `assert_policy_steered_path()` | Apply PBR policy and verify flow routing |
| `assert_wan_interface_status()` | Check interface operational state (up/down/degraded) |
| `assert_path_metrics_within_slo()` | Assert per-link latency, jitter, loss thresholds |
| `measure_failover_convergence()` | Measure time from blackout to path switch |

### Testbed Reset & Teardown

Each test scenario records state changes in `bf_context` during execution. An `autouse` teardown fixture reverts every change in reverse order:

| Template method called | Teardown action |
| :--- | :--- |
| `TrafficController.set_impairment_profile()` | Restore saved original profile |
| `TrafficController.inject_transient()` | Automatic — background thread restores after `duration_ms` |
| `WANEdgeDevice.apply_policy()` | `remove_policy()` for each applied policy |
| `WANEdgeDevice.bring_wan_down()` | `bring_wan_up()` for each downed interface |

A session-scoped setup fixture establishes the default state once per pytest session: pristine impairment profiles, no PBR overrides, streaming content available in MinIO.

---

## 7. Deployment View

### Testbed Topology: Dual WAN

**Connections:**

1. **LAN Side:** Playwright QoE Client container on `lan-segment` (192.168.10.0/24).
2. **DUT:** Linux SD-WAN Router with two WAN interfaces:
   - WAN1 (MPLS/Fiber) on `dut-wan1` (10.10.1.0/30)
   - WAN2 (Internet/Cable) on `dut-wan2` (10.10.2.0/30)
3. **WAN Emulators:** Dedicated TrafficController containers on each WAN link.
4. **North Side:** Application servers on `north-segment` (172.16.0.0/24), reached via `app-router` for symmetric return routing.

See [SDWAN_Testbed_Configuration.md](testbed-configuration.md) for the complete topology, OVS bridge configuration, Docker Compose, and IP addressing.

### Canonical Impairment Profiles

| Profile Name | Latency | Jitter | Packet Loss | Bandwidth | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `pristine` | 5 ms | 1 ms | 0% | 1 Gbps | Ideal conditions |
| `cable_typical` | 15 ms | 5 ms | 0.1% | 100 Mbps | Typical subscriber |
| `4g_mobile` | 80 ms | 30 ms | 1% | 20 Mbps | Mobile/LTE failover |
| `satellite` | 600 ms | 50 ms | 2% | 10 Mbps | High latency link |
| `congested` | 25 ms | 40 ms | 3% | Variable | Peak hour congestion |

All five presets are defined in `bf_config/bf_env_sdwan.json` under `environment_def.impairment_presets`.

### QoE Service Level Objectives

| Category | Key Metrics (SLOs) |
| :--- | :--- |
| **Productivity (SaaS)** | Page Load Time < 2.5 s (Good), < 4 s (Acceptable); TTFB < 200 ms; Transaction Success > 99.9% |
| **Streaming** | Startup Time < 2 s; Rebuffer Ratio < 1%; Resolution: Sustained 1080p/4K |
| **Conferencing** | MOS > 4.0 (Good), > 3.5 (Acceptable); One-Way Latency < 150 ms; Jitter < 30 ms |

---

## 8. Crosscutting Concepts

### Five-Layer Architecture Compliance

All test pillars follow the five-layer Boardfarm architecture:

| Layer | SD-WAN Mapping |
| :--- | :--- |
| **0 — System Use Cases** | Requirement use cases in `docs/` (QoE SLOs, path steering scenarios, security policies) |
| **1 — Test Definitions** | Gherkin feature files and Robot test cases |
| **2 — Step Defs / Keywords** | Thin wrappers in `tests/step_defs/` and `robot/libraries/` — no business logic |
| **3 — Boardfarm Use Cases** | `use_cases/qoe.py`, `use_cases/wan_edge.py`, `use_cases/traffic_control.py` — single source of truth |
| **4 — Device Templates** | `WANEdgeDevice`, `QoEClient`, `TrafficController` — device contracts only |

Business logic lives exclusively in Layer 3. Step definitions (Layer 2) are thin wrappers. Device-specific CLI/API calls live in device classes behind Layer 4 template interfaces.

### Logical WAN Labels

All `WANEdgeDevice` methods that return or accept interface identifiers use logical labels (`"wan1"`, `"wan2"`), never physical names (`"eth-wan1"`, `"GigabitEthernet0/0/0"`). The `wan_interfaces` inventory mapping provides the translation. This is the primary mechanism for DUT portability.

### Testbed PKI

A shared `easy-rsa` root CA (`CN=SD-WAN Testbed CA`) issues certificates for Nginx TLS, WebRTC WSS, and StrongSwan IKEv2. The Playwright/Chromium trust store includes the CA via both `update-ca-certificates` and `certutil` (NSS database). See [Testbed_CA_Setup.md](testbed-ca-setup.md).

### Centralized Logging

Fluent Bit runs on the Docker management network, reading all container stdout/stderr via the Docker socket. Log traffic never enters the simulated OVS network.

---

## 9. Architecture Decisions

| ID | Decision | Status |
| --- | --- | --- |
| [ADR-0001](../../adr/0001-scope-to-digital-twin-phase-3.5.md) | Scope to Digital Twin (Phase 3.5) — do not pursue QoS/Security tooling or commercial DUT integration | Accepted |

---

## 10. Quality Requirements

### Test Suite Summary (Phase 3.5)

276 tests passing:

| Suite | Count | Scope |
| :--- | :---: | :--- |
| Unit tests | 60 | Library functions, profile parsing, schema validation |
| WAN Edge integration | 22 | 4 pre-hardware validation scenarios |
| QoE impairment integration | 8 | Productivity, Streaming, Conferencing under pristine + cable_typical |
| Traffic Control integration | 186 | `LinuxTrafficController` operations, presets, transients |

All integration tests pass in three consecutive runs.

---

## 11. Risks and Technical Debt

| Risk / Debt | Impact | Mitigation |
| --- | --- | --- |
| Commercial DUT portability unproven | `WANEdgeDevice` template may need adjustments for vendor APIs | Template design follows Boardfarm conventions used successfully for CPE testing |
| QoS contention testing | `TrafficGenerator` deployed; basic QoS contention validated (UC-SDWAN-06). DUT-side QoS shaping (`tc htb`) not yet implemented — DUT cannot actively prioritise DSCP-marked traffic | See [traffic-generator.md](traffic-generator.md) |
| Security pillar partially unvalidated | Active threat emulation (port scan, SYN flood, C2, EICAR) not tested | `MaliciousHost` template and `security_use_cases.py` are designed in the original technical brief |
| `reset_to_default()` not yet implemented | Change-registry teardown requires each test step to record its changes | Natural next step once template implementations are stable |

---

## 12. Glossary

| Term | Definition |
| --- | --- |
| **BFD** | Bidirectional Forwarding Detection — sub-second failure detection protocol |
| **Digital Twin** | Linux Router testbed that functionally mirrors a commercial SD-WAN appliance |
| **DUT** | Device Under Test — the WAN Edge appliance being validated |
| **FRR** | Free Range Routing — open-source routing suite used in the Linux Router |
| **IFB** | Intermediate Functional Block — Linux virtual device for ingress traffic shaping |
| **MOS** | Mean Opinion Score — 1.0–5.0 quality rating calculated via ITU-T G.107 E-model |
| **OVS** | Open vSwitch — virtual switch used by Raikou for testbed network topology |
| **PBR** | Policy Based Routing — forwarding decisions based on match criteria (DSCP, destination) |
| **QoE** | Quality of Experience — end-user perceived quality of network services |
| **QoS** | Quality of Service — traffic classification and prioritization mechanisms |
| **Raikou** | Container orchestrator providing OVS-based network-in-a-box infrastructure |
| **SASE** | Secure Access Service Edge — convergence of SD-WAN and cloud security |
| **SLO** | Service Level Objective — measurable quality threshold for pass/fail determination |
