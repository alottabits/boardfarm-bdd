# Technical Brief: WAN Edge Appliance Testing Framework

**Date:** February 07, 2026
**Version:** 2.0 (Container-First Plan, Linux Router DUT)
**Status:** Draft

---

## 1. Executive Summary

This document defines the scope and implementation plan for a unified testing framework designed to validate **WAN Edge appliances**. As the enterprise edge evolves from simple routing to intelligent SD-WAN and SASE (Secure Access Service Edge), verification must move beyond basic connectivity to encompass application performance, traffic intelligence, security efficacy, and user experience.

### Related Documents

*   `Traffic_Management_Components_Architecture.md`: Detailed design for the TrafficController and ImpairmentProfiles.
*   `LinuxSDWANRouter_Implementation_Plan.md`: Implementation design for the Linux-based DUT (Digital Twin).
*   `QoE_Client_Implementation_Plan.md`: Implementation design for the Playwright-based QoE measurement client.
*   `Application_Services_Implementation_Plan.md`: Implementation design for North-side target services and threat simulation.

The framework is designed to validate market-leading WAN Edge platforms, including:

* **Cisco Catalyst 8000 Series (Viptela):** IOS-XE based SD-WAN stack (Heavyweight routing).
* **Fortinet FortiGate:** ASIC-accelerated path steering and NGFW convergence.
* **VMware SD-WAN (Velocloud):** Dynamic Multi-Path Optimization (DMPO) and packet-level steering.
* **Palo Alto ION (Prisma SD-WAN):** App-defined networking (Layer 7 focus).
* **HPE Aruba EdgeConnect (Silver Peak):** Path conditioning (FEC, Packet Order Correction).

The testing strategy focuses on four core pillars:

1. **Quality of Experience (Outcome):** Does the user perceive the network as good?
2. **Quality of Service (Mechanism):** Is traffic prioritized correctly?
3. **Path Steering (Intelligence):** Is the best link chosen dynamically?
4. **Security (Protection):** Is the edge secure against threats without compromising performance?

Portability across DUTs (Linux Router → commercial appliances) is enforced by the **`WANEdge` Boardfarm template**, which is the single abstraction boundary between test logic and vendor-specific implementations. QoE measurement follows the same four-layer Boardfarm architecture via the **`QoEClient` template**, keeping measurement logic out of step definitions.

---

## 2. Testing Pillars

### 2.1 Quality of Experience (QoE) - The Outcome

QoE verifies the end-user's perspective. It answers: *"Can the user effectively perform their job despite network conditions?"*
This pillar uses the **FSM Three-Mode Architecture** (Functional, Navigation, Visual) to validate specific service categories.

#### Service Categories & Metrics

| Category | Description | Key Metrics (SLOs) |
| :--- | :--- | :--- |
| **Productivity (SaaS)** | Interaction with cloud suites (Office 365, Salesforce). | **Page Load Time:** < 2.5s (Good), < 4s (Acceptable)<br>**Time to First Byte (TTFB):** < 200ms<br>**Transaction Success:** > 99.9% |
| **Streaming** | Video on Demand (Netflix, YouTube, Training). | **Startup Time:** < 2s<br>**Rebuffer Ratio:** < 1%<br>**Resolution:** Sustained 1080p/4K |
| **Conferencing** | Real-time audio/video (Teams, Zoom). | **MOS (Mean Opinion Score):** > 4.0 (Good), > 3.5 (Acceptable)<br>**One-Way Latency:** < 150ms<br>**Jitter:** < 30ms |

#### Canonical Impairment Profiles

To verify resilience, the testbed applies deterministic network profiles. These are the **canonical preset names** used across all tests and env configs (see `Traffic_Management_Components_Architecture.md` for the `impairment_presets` env config block):

| Profile Name | Latency | Jitter | Packet Loss | Bandwidth | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `pristine` | 5ms | 1ms | 0% | 1 Gbps | Ideal conditions |
| `cable_typical` | 15ms | 5ms | 0.1% | 100 Mbps | Typical subscriber |
| `4g_mobile` | 80ms | 30ms | 1% | 20 Mbps | Mobile/LTE failover |
| `satellite` | 600ms | 50ms | 2% | 10 Mbps | High latency link |
| `congested` | 25ms | 40ms | 3% | Variable | Peak hour congestion |

> **Note — Asymmetric Profiles:** SD-WAN devices probe link quality bidirectionally. Tests that target the DUT's path selection algorithm should specify **per-direction impairment** (e.g., uplink pristine / downlink congested) using the `egress_*` / `ingress_*` overrides in `ImpairmentProfile` (see Section 4.5). Symmetric profiles are sufficient for QoE-only tests.

> **Note — Linux `tc` Ingress Limitation:** Linux `tc netem` operates on egress only. Ingress rate-limiting requires an IFB (Intermediate Functional Block) virtual device with an ingress filter redirect. The `LinuxTrafficController` implementation must handle IFB setup when `ingress_bandwidth_limit_mbps` is set. This constraint does not apply to hardware impairment appliances (Spirent, Keysight).

### 2.2 Quality of Service (QoS) - The Mechanism

QoS verifies the underlying mechanisms the DUT uses to manage contention. It answers: *"Is the device correctly classifying and prioritizing traffic?"*

* **Traffic Management:** Verification of Shapers, Policers, and Burst handling.
* **DSCP Tagging:** Ensuring markings are preserved or re-written correctly across the WAN overlay.
* **Rate Limiting:** Verifying SLA enforcement for specific traffic classes.
* **Queuing:** Validating Low Latency Queuing (LLQ) effectiveness under link saturation.

> **Requirement — Background Load:** QoS validation requires **controlled traffic contention** to create queue pressure. Tests use the `TrafficGenerator` Boardfarm template (iPerf3/Trex implementations) to inject calibrated background load at specific DSCP classes before asserting QoE SLOs for priority traffic. See Section 3.4.

### 2.3 Path Steering - The Intelligence

Path Steering verifies the "Brain" of the SD-WAN solution. It answers: *"Is the device making the optimal path decision based on real-time conditions?"*

* **Link Selection:** Choosing the best path based on Latency, Loss, and Jitter measurements.
* **Performance-based Routing (PbR):** Dynamic re-routing of flows when SLA thresholds are breached.
* **Sub-second Failover:** Ensuring session persistence (e.g., Voice calls) during blackout events.
* **Brownout Resilience:** Utilizing features like FEC (Forward Error Correction) or Packet Duplication to mitigate degraded links.

> **Requirement — Convergence Time Measurement:** Sub-second failover assertions require measuring the elapsed time between impairment injection (T0) and traffic switching to the backup path (T1). Tests use `measure_failover_convergence()` from `use_cases/wan_edge.py`, which combines `inject_blackout()` with polling of `WANEdgeDevice.get_active_wan_interface()`. See Section 3.6.

> **Requirement — DUT Path Inspection:** Asserting "traffic is on WAN1" requires reading the DUT's active forwarding state. This is exposed via the `WANEdgeDevice` template (`get_active_wan_interface()`, `get_wan_path_metrics()`). The Linux Router implements `get_active_wan_interface()` via `ip route get` (parsed and translated to a logical label) and `get_wan_path_metrics()` via active `ping` probes to each WAN gateway (the functional proxy for commercial DUTs' built-in SLA probers). Commercial DUT implementations query vendor NETCONF/REST APIs for both. Tests call the template only. See Section 3.4.

### 2.4 Security & Firewalling - The Protection

Security verifies the robustness of the WAN Edge as the first line of defense (SASE/NGFW). It answers: *"Is the network secure, and what is the performance cost of that security?"*

* **Zone-Based Firewalling:** Verification of stateful inspection rules (Allow/Deny) between LAN, WAN, and DMZ zones.
* **Application Control (L7 Filtering):** Blocking specific applications (e.g., BitTorrent, Social Media) regardless of port.
* **Performance Impact:** Measuring "Throughput with Services" vs. "Raw Throughput" to quantify the cost of enabling IPS/IDS and SSL Inspection.
* **Threat Emulation:**
  * **Inbound:** Port scanning detection, DDoS mitigation (rate limiting SYN floods).
  * **Outbound:** Blocking Command & Control (C2) callback attempts (DNS sinkholing).
* **VPN/Overlay Encryption:** Verifying IPsec/WireGuard tunnel establishment and re-keying under load.

#### Boardfarm Component Mapping for Security Tests

Security test cases follow the same four-layer Boardfarm architecture as all other pillars. They must not embed attack logic in step definitions. **Static test payloads (e.g., EICAR files, PCAP files for packet storms, or C2 callback definitions) must be treated as Test Artifacts. They should be stored in the appropriate artifact directory (e.g., `bf_config/security_artifacts/`) and provided to the `MaliciousHost` via paths resolved from the environment configuration.**

> **Design note — single WAN-side component:** All threat infrastructure lives in one `MaliciousHost` container on the WAN (internet) side of the testbed. It handles both *active inbound attacks* (port scans, SYN floods directed at the DUT WAN IP) and *passive target services* (C2 listener, EICAR file server). The LAN-side "compromised host" role for C2 callback tests is fulfilled by the existing `QoEClient` — it attempts an outbound TCP connection to the `MaliciousHost` listener, which the DUT's Application Control policy must block. No separate LAN-side threat container is required.

| Test Goal | Boardfarm Template | Functional Implementation | Use Case Function |
| :--- | :--- | :--- | :--- |
| Port scan detection | `MaliciousHost` (WAN side) | Kali Linux container — `nmap -sS <DUT_WAN_IP>` | `threat_use_cases.run_port_scan()` |
| SYN flood mitigation | `MaliciousHost` (WAN side) | Kali Linux container — `hping3 -S --flood <DUT_WAN_IP>` | `threat_use_cases.inject_syn_flood()` |
| C2 callback blocking | `MaliciousHost` (listener) + `QoEClient` (LAN initiator) | `MaliciousHost` starts `nc` listener; `QoEClient` attempts outbound TCP connection | `security_use_cases.assert_c2_callback_blocked()` |
| EICAR file blocking | `MaliciousHost` (WAN side) | Kali Linux container serving static EICAR file via HTTP | `security_use_cases.assert_download_blocked()` |
| Assert traffic blocked | `WANEdgeDevice` + DUT logs | SSH to DUT / syslog | `security_use_cases.assert_traffic_blocked()` |

---

## 3. Architecture & Tooling

To ensure consistency and portability across different environments (Functional vs. Pre-Production), the framework leverages a decoupled architecture.

### 3.1 Core Components

* **Raikou:** Used to instantiate networked containers for the functional testbed components (Clients, Servers, ISP Routers). Provides the "Network-in-a-Box" infrastructure with OVS bridges.
* **Boardfarm:** The orchestration layer. Configures the testbed, manages device connections (DUT, Clients, Traffic Generators), and provides a consistent test interface (API) regardless of the underlying hardware.
* **`WANEdge` Template:** The central DUT abstraction. All path-steering, QoS, and security test cases interact with the DUT exclusively through this template. Enables a Linux Router → commercial appliance swap without changing test logic. See Section 3.4.
* **`QoEClient` Template:** Abstracts application-level measurement clients (Playwright, iperf, synthetic conferencing). QoE measurement logic lives in `use_cases/qoe.py`, not in step definitions. See Section 3.5.
* **`TrafficGenerator` Template:** Abstracts background load generation (iPerf3, Trex). Required for QoS contention tests. See Section 3.4.
* **`MaliciousHost` Template:** Abstracts the WAN-side threat infrastructure: inbound attack generation (Nmap, hping3) directed at the DUT, and passive target services (C2 listener, EICAR distribution) for outbound blocking tests. Required for Security pillar tests. See Section 3.4.

### 3.2 Testbed Topology: Dual WAN (Initial) → Triple WAN (Expansion)

The initial testbed uses a **Dual WAN** topology to prove the concept. Expansion to **Triple WAN** follows once validation is complete.

![triple_wan_topology](../Excalidraw/triple_wan_topology.excalidraw.svg)

**Connections:**

1. **LAN Side:**
    * **South-Side Clients:** Playwright containers (Browser/App simulation) — exposed via `QoEClient` template. For security tests, the `QoEClient` also simulates a "compromised host" by attempting outbound connections to the `MaliciousHost`.
    * **Traffic Generators:** iPerf3/Trex for background load — exposed via `TrafficGenerator` template.
2. **DUT (WAN Edge Appliance):**
    * **WAN 1 (MPLS/Fiber):** High bandwidth, low latency, high cost.
    * **WAN 2 (Internet/Cable):** High bandwidth, variable latency, low cost.
    * **WAN 3 (LTE/5G):** Metered bandwidth, higher latency, backup path. *(Added in expansion phase.)*
3. **WAN Emulator (Traffic Control):**
    * Injects impairments (Delay, Loss, Jitter, Bandwidth limits) independently on each WAN link — exposed via `TrafficController` template.
4. **Cloud Side:**
    * **North-Side Services:** Productivity, Streaming, and Conferencing servers hosted in the testbed (simulating Cloud/Internet).
    * **Malicious Host:** Single WAN-side Kali Linux container acting as inbound attacker (port scans, SYN floods toward DUT WAN IP) and passive threat server (C2 listener, EICAR distribution) — exposed via `MaliciousHost` template.

### 3.3 Implementation Types

* **Functional Testbed:** All components are containerized implementations, except for the DUT. Traffic control is done via Linux `tc` within Raikou containers.
* **Pre-Production Testbed:** Physical hardware DUTs. Traffic control is handled by dedicated hardware (Spirent, Keysight) or high-performance WAN emulators. Boardfarm abstracts these differences using the `TrafficController` template.

---

### 3.4 Boardfarm Device Templates

This section defines the abstract interfaces (Boardfarm templates) that all SD-WAN test cases depend on. **Test cases import templates only — never concrete device classes.**

#### `WANEdgeDevice` Template

**Location:** `boardfarm3/templates/wan_edge.py`

The central DUT abstraction. Enables the Linux Router (FRR) to serve as a drop-in placeholder for commercial SD-WAN appliances. All path-steering, QoS, and telemetry test logic depends on this interface.

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

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

    Implementations: LinuxRouterDUT, CiscoC8000DUT, FortiGateDUT, VelocloudDUT.
    """

    @property
    @abstractmethod
    def nbi(self):
        """Northbound Interface - Orchestrator REST API."""

    @property
    @abstractmethod
    def gui(self):
        """GUI Interface - Orchestrator Web Dashboard."""

    @property
    @abstractmethod
    def console(self):
        """Console Interface - On-prem CLI/SSH access."""

    @abstractmethod
    def get_active_wan_interface(self, flow_dst: str | None = None, via: str = "console") -> str:
        """Return the logical WAN label currently forwarding traffic.

        The return value is ALWAYS a key from the inventory ``wan_interfaces`` mapping
        (e.g. ``"wan1"``, ``"wan2"``), never a physical OS interface name (e.g. ``"eth2"``
        or ``"GigabitEthernet0/0/0"``). This contract makes test code portable across DUT
        implementations where physical interface names differ between vendors.

        Implementations MUST:
        1. Query the DUT for its active forwarding interface (via CLI, API, or NBI).
        2. Reverse-look up the physical name in the ``wan_interfaces`` inventory mapping
           to obtain the logical label before returning.

        The ``wan_interfaces`` key is **required** in the device inventory config for all
        ``WANEdgeDevice`` implementations. Example::

            "wan_interfaces": {"wan1": "eth2", "wan2": "eth3"}          # Linux
            "wan_interfaces": {"wan1": "GigabitEthernet0/0/0", ...}     # Cisco

        :param flow_dst: Optional destination IP/prefix to select a specific flow.
        :param via: Interface to use ("console" for CLI, "nbi" for API, "gui" for web dashboard).
        :return: Logical WAN label, e.g. ``"wan1"`` or ``"wan2"``.
        :raises KeyError: if the physical interface returned by the DUT is absent from
            the ``wan_interfaces`` mapping.
        """

    @abstractmethod
    def get_wan_path_metrics(self, via: str = "console") -> dict[str, PathMetrics]:
        """Return per-link quality metrics as measured by the DUT.

        :param via: Interface to use.
        :return: Mapping of logical WAN label → PathMetrics (keys match ``wan_interfaces``).
        """

    @abstractmethod
    def get_wan_interface_status(self, via: str = "console") -> dict[str, LinkStatus]:
        """Return UP/DOWN/degraded state for each WAN interface.

        :param via: Interface to use.
        :return: Mapping of logical WAN label → LinkStatus (keys match ``wan_interfaces``).
        """

    @abstractmethod
    def get_routing_table(self, via: str = "console") -> list[RouteEntry]:
        """Return the current forwarding/routing table.
        
        :param via: Interface to use.
        """

    @abstractmethod
    def apply_policy(self, policy: dict, via: str = "nbi") -> None:
        """Apply a routing or SD-WAN policy (PBR rule, SLA threshold, etc.).

        :param policy: Vendor-neutral policy dict; device class translates to CLI/API.
        :param via: Interface to use (defaulting to API for policy changes).
        """

    @abstractmethod
    def get_telemetry(self, via: str = "nbi") -> dict:
        """Return a snapshot of DUT telemetry (uptime, session counts, CPU, etc.).
        
        :param via: Interface to use.
        """
```

**Linux Router implementation** (`LinuxSDWANRouter`): executes `ip route get`, `ip -j link show`, `ping`, and `ip -j route show` via SSH. All methods that return interface identifiers resolve physical names to logical labels via the `wan_interfaces` config mapping. See `LinuxSDWANRouter_Implementation_Plan.md` for the reverse-lookup pattern.

**Commercial implementations** (Phase 5): wrap vendor REST/NETCONF APIs. The test scenarios do not change.

#### `QoEClient` Template

**Location:** `boardfarm3/templates/qoe_client.py`

Abstracts application-level measurement. Keeps QoE measurement logic in `use_cases/qoe.py`, not in step definitions.

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class QoEResult:
    """Structured result from a single QoE measurement."""
    category: str               # "productivity" | "streaming" | "conferencing"
    load_time_ms: float | None
    ttfb_ms: float | None
    rebuffer_ratio: float | None  # 0.0–1.0
    mos_score: float | None       # 1.0–5.0
    resolution: str | None        # e.g. "1080p"
    success: bool
    raw_metrics: dict             # Category-specific extras

class QoEClient(ABC):
    """Abstract measurement client for end-user experience validation."""

    @abstractmethod
    def measure_productivity(self, url: str, scenario: str = "page_load") -> QoEResult:
        """Load a URL and capture navigation timing / TTFB."""

    @abstractmethod
    def measure_streaming(self, stream_url: str, duration_s: int = 30) -> QoEResult:
        """Play a video stream and capture startup time and rebuffer ratio."""

    @abstractmethod
    def measure_conferencing(self, session_url: str, duration_s: int = 60) -> QoEResult:
        """Join a WebRTC session and capture MOS, latency, jitter via getStats()."""
```

**Functional implementation** (`PlaywrightQoEClient`): uses Playwright navigation timing API and WebRTC `getStats()`. MOS R-Factor calculation lives in `lib/qoe.py`.

#### `TrafficGenerator` Template

**Location:** `boardfarm3/templates/traffic_generator.py`

Abstracts background load generation for QoS contention scenarios.

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class TrafficSpec:
    protocol: str           # "tcp" | "udp"
    bandwidth_mbps: int
    dscp: int               # DSCP marking, e.g. 46 for EF (voice)
    duration_s: int
    parallel_streams: int = 1

@dataclass
class TrafficResult:
    sent_mbps: float
    received_mbps: float
    loss_percent: float
    jitter_ms: float | None

class TrafficGenerator(ABC):
    """Abstract background load generator for QoS and contention tests."""

    @abstractmethod
    def start_traffic(self, spec: TrafficSpec) -> None:
        """Start a background traffic flow. Non-blocking."""

    @abstractmethod
    def stop_traffic(self) -> TrafficResult:
        """Stop the flow and return measured results."""

    @abstractmethod
    def run_traffic(self, spec: TrafficSpec) -> TrafficResult:
        """Run a traffic flow to completion and return results."""
```

**Functional implementation** (`IperfTrafficGenerator`): wraps iPerf3 client/server via SSH.

#### `MaliciousHost` Template

**Location:** `boardfarm3/templates/malicious_host.py`

Abstracts the WAN-side threat infrastructure. A single container fulfils two roles:

* **Active inbound attacker** — generates attacks directed at the DUT WAN IP from the internet side (port scans, SYN floods).
* **Passive threat server** — hosts services that LAN clients should be blocked from reaching (C2 listener, EICAR file server).

The LAN-side "compromised host" for C2 callback tests is the existing `QoEClient` — it simply attempts a TCP connection to this host's listener port, which the DUT's Application Control policy must intercept.

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class ScanResult:
    target: str
    open_ports: list[int]
    scan_duration_s: float

class MaliciousHost(ABC):
    """Abstract WAN-side threat infrastructure for Security pillar validation.

    Implementations: KaliMaliciousHost.
    """

    # --- Active inbound attacks (WAN → DUT) ---

    @abstractmethod
    def run_port_scan(self, target: str, port_range: str = "1-1024") -> ScanResult:
        """Run a TCP SYN scan against target (typically the DUT WAN IP).

        :param target: IP address or hostname to scan.
        :param port_range: Port range string, e.g. "1-1024".
        :return: ScanResult with open ports visible from the WAN side.
        """

    @abstractmethod
    def inject_syn_flood(self, target: str, rate_pps: int, duration_s: int) -> None:
        """Inject a SYN flood at the given packet rate for the given duration.

        :param target: IP address of the DUT WAN interface.
        :param rate_pps: Packets per second (e.g. 1000).
        :param duration_s: Duration of the flood in seconds.
        """

    # --- Passive threat services (targets for LAN → WAN blocking tests) ---

    @abstractmethod
    def start_c2_listener(self, port: int) -> None:
        """Start a TCP listener to accept inbound C2 beacon connections.

        :param port: TCP port to listen on (e.g. 4444).
        """

    @abstractmethod
    def stop_c2_listener(self, port: int) -> None:
        """Stop the C2 listener on the given port."""

    @abstractmethod
    def check_connection_received(self, port: int, source_ip: str | None = None) -> bool:
        """Return True if a connection attempt reached the listener (firewall bypass).

        A True result means the DUT did NOT block the connection — the test should
        assert False on this return value.

        :param port: Port the listener was running on.
        :param source_ip: Optional — filter by the expected source IP (LAN client).
        """

    @abstractmethod
    def get_eicar_url(self) -> str:
        """Return the HTTP URL hosting the EICAR test file.

        :return: Full URL, e.g. 'http://203.0.113.66/eicar.com'.
        """
```

**Functional implementation** (`KaliMaliciousHost`): SSH into a Kali Linux container. Active attacks use `nmap` and `hping3`; passive services use `netcat` or Python HTTP server.

---

#### `ProductivityServer` Template

**Location:** `boardfarm3/templates/productivity_server.py`

Abstracts the North-side Mock SaaS server. QoE productivity tests depend on this interface only — never on Nginx configuration directly.

```python
class ProductivityServer(ABC):
    @abstractmethod
    def get_service_url(self) -> str:
        """Return the base URL for the SaaS application."""

    @abstractmethod
    def set_response_delay(self, delay_ms: int) -> None:
        """Inject server-side processing delay (latency simulation)."""

    @abstractmethod
    def set_content_size(self, size_bytes: int) -> None:
        """Configure the size of the 'large asset' to simulate heavy/light apps."""
```

**Functional implementation** (`NginxProductivityServer`): Nginx container serving a configurable static payload. See `Application_Services_Implementation_Plan.md` Section 3.1.

---

#### `StreamingServer` Template

**Location:** `boardfarm3/templates/streaming_server.py`

Abstracts the North-side Nginx Video-on-Demand server. QoE streaming tests depend on this interface only.

```python
class StreamingServer(ABC):
    @abstractmethod
    def get_manifest_url(self, video_id: str = "default") -> str:
        """Return the HLS (.m3u8) or DASH (.mpd) URL for a video asset."""

    @abstractmethod
    def list_available_bitrates(self, video_id: str) -> list[str]:
        """Return list of available quality profiles (e.g. ['360p', '1080p'])."""
```

**Functional implementation** (`NginxStreamingServer`): Nginx container with multi-bitrate HLS/DASH content. See `Application_Services_Implementation_Plan.md` Section 3.2.

---

#### `ConferencingServer` Template

**Location:** `boardfarm3/templates/conferencing_server.py`

Abstracts the North-side WebRTC Echo server. QoE conferencing tests depend on this interface only.

```python
class ConferencingServer(ABC):
    @abstractmethod
    def start_session(self, session_id: str) -> str:
        """Start a new conference room/session.

        :return: The WebRTC signalling URL for clients to connect
                 (e.g. 'wss://webrtc-echo:8443/session1').
        """

    @abstractmethod
    def get_session_stats(self, session_id: str) -> dict:
        """Return server-side statistics for the session (Packet Loss, Jitter).

        Useful for correlating client-side MOS with server-side RTCP metrics.
        """
```

**Functional implementation** (`WebRTCConferencingServer`): `pion`-based WebRTC Echo container. No Coturn STUN/TURN required — direct peer connectivity is guaranteed in the controlled testbed network. See `Application_Services_Implementation_Plan.md` Section 3.3.

---

### 3.5 QoE Measurement Architecture

QoE measurement follows the standard Boardfarm four-layer architecture:

```
Feature File (Gherkin)
  └─► Step Definition (thin wrapper)
        └─► use_cases/qoe.py  (business logic: SLO assertions, R-Factor)
              └─► QoEClient template
                    └─► PlaywrightQoEClient (device class)
```

**Key principle:** MOS R-Factor calculation and SLO threshold comparisons live in `lib/qoe.py` and `use_cases/qoe.py`. Step definitions never contain QoE math.

```python
# use_cases/qoe.py (excerpt)

def assert_productivity_slo(client: QoEClient, url: str) -> QoEResult:
    """Run productivity measurement and assert SLOs.

    .. hint:: Implements steps such as:
        - Then the page load time should meet the SLO
        - Then the TTFB should be below 200ms

    :raises AssertionError: if load_time_ms > 4000 or ttfb_ms > 200
    """
    result = client.measure_productivity(url)
    assert result.load_time_ms is not None and result.load_time_ms <= 4000, (
        f"Page load {result.load_time_ms:.0f}ms exceeds 4s SLO"
    )
    assert result.ttfb_ms is not None and result.ttfb_ms <= 200, (
        f"TTFB {result.ttfb_ms:.0f}ms exceeds 200ms SLO"
    )
    return result


def assert_conferencing_slo(client: QoEClient, session_url: str) -> QoEResult:
    """Run conferencing measurement and assert MOS SLO (> 3.5 acceptable).

    .. hint:: Implements steps such as:
        - Then the conferencing quality should meet the SLO

    :raises AssertionError: if mos_score < 3.5
    """
    result = client.measure_conferencing(session_url)
    assert result.mos_score is not None and result.mos_score >= 3.5, (
        f"MOS {result.mos_score:.2f} below 3.5 SLO"
    )
    return result
```

**BDD step (thin wrapper):**

```python
@then('the conferencing quality should meet the SLO')
def assert_conferencing_slo_step(qoe_client, bf_context):
    result = qoe_use_cases.assert_conferencing_slo(qoe_client, bf_context.session_url)
    print(f"✓ MOS {result.mos_score:.2f} — SLO passed")
```

---

### 3.6 Failover Convergence Time Measurement

Sub-second failover validation (Pillar 2.3) requires correlating:

* **T0:** Impairment injected on the primary WAN link
* **T1:** DUT detects failure (BFD timeout, probe failure, SLA breach)
* **T2:** DUT switches active path to backup link
* **T3 - T0:** Total convergence time (the asserted metric)

This is implemented in `use_cases/wan_edge.py`:

```python
def measure_failover_convergence(
    dut: WANEdgeDevice,
    impairment_ctrl: TrafficController,
    primary_link: str,
    backup_link: str,
    poll_interval_ms: int = 50,
    timeout_ms: int = 5000,
) -> float:
    """Inject a blackout on primary_link and measure time until DUT switches to backup_link.

    .. hint:: Implements steps such as:
        - Then the DUT should switch to the backup path within 1000ms

    :param dut: WANEdgeDevice instance
    :param impairment_ctrl: TrafficController for the primary WAN link
    :param primary_link: Expected primary interface name (e.g. "wan1")
    :param backup_link: Expected backup interface name (e.g. "wan2")
    :param poll_interval_ms: How often to poll the DUT's active interface
    :param timeout_ms: Maximum wait for convergence before failing
    :return: Convergence time in milliseconds
    :raises AssertionError: if convergence does not occur within timeout_ms
    """
    import time
    from boardfarm3.use_cases import traffic_control as traffic_control_use_cases
    
    traffic_control_use_cases.inject_blackout(impairment_ctrl, duration_ms=timeout_ms + 1000)
    t0 = time.monotonic()
    deadline = t0 + timeout_ms / 1000
    while time.monotonic() < deadline:
        if dut.get_active_wan_interface() == backup_link:
            return (time.monotonic() - t0) * 1000
        time.sleep(poll_interval_ms / 1000)
    raise AssertionError(
        f"DUT did not switch from {primary_link!r} to {backup_link!r} within {timeout_ms}ms"
    )
```

**BDD step:**

```gherkin
When the primary WAN link fails
Then the DUT should switch to the backup path within 1000ms
```

```python
@then('the DUT should switch to the backup path within {max_ms:d}ms')
def assert_failover_time(dut, wan1_impairment, max_ms, bf_context):
    conv_ms = wan_edge_use_cases.measure_failover_convergence(
        dut, wan1_impairment, primary_link="wan1", backup_link="wan2"
    )
    assert conv_ms <= max_ms, f"Convergence {conv_ms:.0f}ms exceeded {max_ms}ms threshold"
    print(f"✓ Failover in {conv_ms:.0f}ms")
```

---

## 4. Implementation Plan

### 4.1 Container-First Approach

The testbed is built by **developing Docker containers first**, then aligning the Raikou docker-compose file to instantiate them. This approach allows each component to be developed and tested independently before integration.

**Development order:**

1. Build and validate each container image.
2. Create Docker Compose for Raikou with OVS topology.
3. Align Boardfarm inventory and env config to the running topology.

### 4.2 Minimum Viable Component Set (PoC)

The initial proof-of-concept uses the following minimal set of containers:

| Component | Purpose | Boardfarm Template | Notes |
| :--- | :--- | :--- | :--- |
| **Linux Router (DUT)** | FRR-based router with two WAN interfaces | `WANEdgeDevice` | Path steering, failover |
| **WAN 1 (TrafficController)** | Impairment container for first WAN link | `TrafficController` | `tc`/netem |
| **WAN 2 (TrafficController)** | Impairment container for second WAN link | `TrafficController` | `tc`/netem |
| **WAN-side Services** | Productivity + Streaming servers | — | Mock SaaS, Nginx HLS/DASH |
| **LAN-side Clients** | Productivity + Streaming clients | `QoEClient` | Playwright |

**Topology:** `[LAN Client] → [DUT] → [WAN1 / WAN2] → [Services]`

### 4.3 DUT: Linux Router with FRR (Dual WAN)

Before validating commercial SD-WAN appliances, the testbed itself must be validated. We use a **Linux Router with FRR** as the software DUT placeholder.

**Why Linux Router + FRR?**

* **Raikou Alignment:** Extends the existing Raikou router component (already uses FRR).
* **No KVM Required:** Runs as a standard Linux container; works in CI and cloud environments.
* **Path Steering:** FRR supports policy routing (PBR), nexthop groups, and next-hop tracking for failover.
* **Automation:** CLI (vtysh) and config files; easy to drive from Boardfarm.

**Initial scope (FRR only):**

* Multi-WAN with two interfaces (WAN1, WAN2).
* Policy routing and nexthop groups for path selection and failover.
* Gateway monitoring via resilient nexthop groups or a lightweight script.

**Planned expansion (later phases):**

* **StrongSwan:** Add IPsec VPN overlay for the "VPN/Overlay Encryption" pillar.
* **tc (Traffic Control):** Add traffic shaping (htb, fq_codel) for QoS validation.
* **iptables/nftables:** Add zone-based firewall rules for Security pillar validation.

#### WANEdge Template Implementation: Linux Router

`LinuxSDWANRouter` implements `WANEdgeDevice` using FRR CLI. This is the critical link that makes the PoC's test scenarios portable to commercial DUTs in Phase 5 — the test code does not change, only the device class and Boardfarm config.

| `WANEdgeDevice` Method | `LinuxSDWANRouter` Implementation |
| :--- | :--- |
| `get_active_wan_interface()` | `ip route get <dst>` → parse `dev` field (physical name) → reverse-lookup in `self._wan_interfaces` → **return logical label** (e.g. `"wan1"`) |
| `get_wan_path_metrics()` | `ping -c 5 <gateway>` per WAN interface → parse rtt/mdev/loss → return `dict[logical_label, PathMetrics]` |
| `get_wan_interface_status()` | `ip -j link show` → parse `operstate` → return `dict[logical_label, LinkStatus]` |
| `get_routing_table()` | `ip -j route show` |
| `apply_policy()` | Linux kernel PBR: `ip rule add` + `ip route add ... table N` |
| `get_telemetry()` | `ip -s link show`, `/proc/net/dev`, `/proc/stat`, `/proc/meminfo` |

#### Proxy Mapping: Linux Router to Commercial DUTs

| Feature Category | Commercial DUT (e.g., Meraki) | Linux Router Proxy Equivalent | `WANEdgeDevice` Method |
| :--- | :--- | :--- | :--- |
| **SD-WAN Policies** | Traffic Steering / Policy Routing | FRR PBR + Nexthop Groups | `apply_policy()` |
| **Active Path** | Flow table / dashboard | `ip route get` + vtysh | `get_active_wan_interface()` |
| **Link Metrics** | Built-in SLA probes | BFD / custom probe script | `get_wan_path_metrics()` |
| **QoS / Shaper** | App-aware Shaping | `tc` (planned) | — (QoS template TBD) |
| **Security / FW** | Zone-based FW / IPS | `iptables` (planned) | `get_telemetry()` for counters |
| **VPN/Overlay** | IPsec / WireGuard | StrongSwan (planned) | `get_telemetry()` |
| **Management** | Cloud Dashboard / API | SSH + vtysh / Config Files | `get_telemetry()` |

#### Pre-Hardware Validation Scenarios

1. **Orchestration Handshake**
    * **Goal:** Ensure Boardfarm can talk to the DUT via the `WANEdgeDevice` template.
    * **Method:** Call `dut.get_wan_interface_status()` and `dut.get_routing_table()`.
    * **Success:** Returns populated `LinkStatus` and `RouteEntry` objects without exception.

2. **Impairment Trigger Loop**
    * **Goal:** Verify that applying a "Satellite" profile via the TrafficController triggers failover.
    * **Method:** Configure FRR gateway monitoring. Inject 600ms latency via `tc` on WAN1.
    * **Success:** `dut.get_active_wan_interface()` returns `"wan2"`; LAN Client records transient QoE dip during switch.

3. **Path Steering Verification**
    * **Goal:** Verify that path selection responds to impairment changes.
    * **Method:** Apply `cable_typical` to WAN1, `satellite` to WAN2; verify traffic prefers WAN1.
    * **Success:** `dut.get_active_wan_interface()` returns `"wan1"`; assert confirmed via template call.

4. **Failover Convergence Time**
    * **Goal:** Measure how quickly the DUT switches paths after a blackout.
    * **Method:** Call `measure_failover_convergence(dut, wan1_ctrl, "wan1", "wan2")`.
    * **Success:** Convergence time returned; logged for baseline. (Threshold TBD in Phase 3.)

### 4.4 Additional Component Development

Beyond the PoC set, the following components are developed or integrated:

1. **Traffic Controller (Impairment Layer):**
    * Develop `LinuxTrafficControl` library for functional tests (wrapping `tc`/`netem`).
    * Implement IFB device setup for ingress rate-limiting (required for asymmetric profiles).
    * Implement the `TrafficController` Boardfarm template.
    * Implement `get_impairment_profile()` by parsing `tc qdisc show` output (not from in-memory state) to ensure round-trip fidelity.
    * Develop `SpirentTrafficController` driver for pre-production labs.

2. **Application Services (North-Side):**
    * **Productivity:** Mock SaaS server (HTTP/2, HTTP/3).
    * **Streaming:** Nginx VOD module with multi-bitrate HLS/DASH content.
    * **Conferencing:** WebRTC Echo server (`pion`-based lightweight container).
    * **Security:** "Bad Actor" container serving EICAR test files and listening for C2 callbacks — exposed via `MaliciousHost` device type.

3. **Client Measurement Tools (South-Side):**
    * Implement `PlaywrightQoEClient` device class (implements `QoEClient` template).
    * Capture navigation timing, media stats, and WebRTC `getStats()`.
    * Implement **MOS R-Factor calculation** in `lib/qoe.py` (not in Playwright scripts or step definitions).
    * Implement `qoe_use_cases.py` with SLO assertion functions for all three service categories.

4. **Background Load & Threat Generation:**
    * Implement `IperfTrafficGenerator` device class (implements `TrafficGenerator` template).
    * Implement `KaliMaliciousHost` device class (implements `MaliciousHost` template).
    * Implement `threat_use_cases.py` and `security_use_cases.py`.

5. **WANEdge DUT Driver:**
    * Implement `LinuxSDWANRouter` device class (implements `WANEdgeDevice` template).
    * Implement `wan_edge_use_cases.py` including `measure_failover_convergence()`.

### 4.5 ImpairmentProfile: Advanced Parameters

The standard four-parameter `ImpairmentProfile` covers symmetric link emulation. SD-WAN testing additionally requires advanced parameters. **Note:** These advanced parameters must be merged directly into the canonical schema definition in `boardfarm3/lib/traffic_control.py` to ensure a single source of truth for validation across the overriding framework.

#### Asymmetric Impairment

SD-WAN devices measure link quality bidirectionally. Realistic tests need independent control of uplink (egress from DUT) and downlink (ingress to DUT) conditions:

```python
@dataclass
class ImpairmentProfile:
    # Symmetric baseline (applied to both directions if overrides not set)
    latency_ms: int
    jitter_ms: int
    loss_percent: float
    bandwidth_limit_mbps: int | None      # None = no limit (no TBF qdisc applied)

    # Per-direction overrides (None = use symmetric value above)
    egress_bandwidth_limit_mbps: int | None = None   # DUT → WAN (upload)
    ingress_bandwidth_limit_mbps: int | None = None  # WAN → DUT (download)
    egress_loss_percent: float | None = None
    ingress_loss_percent: float | None = None
```

> **Linux `tc` constraint:** `tc netem` applies only to egress. Ingress shaping requires creating an IFB virtual interface and redirecting ingress traffic through it. `LinuxTrafficController.set_impairment_profile()` handles IFB setup automatically when `ingress_*` overrides are set. This constraint does not apply to `SpirentTrafficController`.

#### Packet Reordering and Corruption

For testing HPE Aruba EdgeConnect FEC and Packet Order Correction:

```python
@dataclass
class ImpairmentProfile:
    ...
    reorder_percent: float = 0.0    # % of packets delivered out of order
    corrupt_percent: float = 0.0    # % of packets with bit errors
    duplicate_percent: float = 0.0  # % of packets duplicated
```

These map directly to `tc netem reorder`, `corrupt`, and `duplicate` parameters.

#### Canonical Preset Completeness

All five canonical presets (`pristine`, `cable_typical`, `4g_mobile`, `satellite`, `congested`) must be present in every `boardfarm_env.json` under `environment_def.impairment_presets`. Tests that reference a preset by name will fail at init if the preset is absent. The `boardfarm_env_example.json` serves as the canonical reference.

---

## 5. Development Phases

### Component Readiness Map

Each component has its own internal phase numbering (see linked documents). The table below shows which component phases must be **complete** before each project phase gate is satisfied. Component plans are the authoritative source; this table is a navigation aid.

| Component | Project Ph 1 — Foundation | Project Ph 2 — Raikou Integration | Project Ph 3 — Validation | Project Ph 4 — Expansion |
| :--- | :--- | :--- | :--- | :--- |
| [LinuxSDWANRouter](LinuxSDWANRouter_Implementation_Plan.md) | §4.2 Ph 1 (Base Container) + Ph 2 (Driver) | §4.2 Ph 3 (Integration) | — | FRR/iptables/StrongSwan expansion |
| [QoEClient](QoE_Client_Implementation_Plan.md) | §5 Ph 1 (Container) + Ph 2 (Productivity) + Ph 3 (Streaming/Conf.) | §5 Ph 4 (Integration) | — | — |
| [Application Services](Application_Services_Implementation_Plan.md) | §6 Ph 1 (Productivity) + Ph 2 (Streaming) | §6 Ph 4 (Integration) | — | §6 Ph 3 (Malicious Host) |
| [Traffic Management](Traffic_Management_Components_Architecture.md) | `LinuxTrafficController` implementation (§7.1) | — | — | — |

> **Note:** Application Services Phase 3 (Malicious Host) is deferred to Project Phase 4 because it is only required for the Security pillar, which is exercised in that phase.

---

1. **Phase 1: Container Development (Foundation)**
    * Develop Docker images for each component: Linux Router (DUT), WAN1/WAN2 (TrafficController), Productivity, Streaming, LAN Client.
    * Extend Linux Router DUT with FRR for two WAN interfaces, policy routing, and failover.
    * Implement the `WANEdgeDevice` template and `LinuxSDWANRouter` device class.
    * Implement the `TrafficController` Boardfarm template and `LinuxTrafficControl` library (including IFB ingress support).
    * Implement the `QoEClient` template and `PlaywrightQoEClient` device class.
    * Develop `lib/qoe.py` (MOS R-Factor) and `use_cases/qoe.py` (SLO assertions).
    * Develop `use_cases/wan_edge.py` (path assertions, failover convergence).
    * Validate each container independently.

    **Exit criteria:**
    * All container images build successfully and pass standalone smoke tests.
    * `LinuxSDWANRouter` implements all `WANEdgeDevice` abstract methods with unit test coverage.
    * `PlaywrightQoEClient` returns a valid `QoEResult` for each service category against a local test server.
    * `LinuxTrafficController` round-trips `get_impairment_profile()` correctly (parsed from `tc qdisc show`, not memory).

2. **Phase 2: Raikou Integration & Dual WAN Topology**
    * Create Docker Compose for Raikou with Dual WAN topology.
    * Configure OVS bridges and network links.
    * Deploy full testbed (all containers instantiated via Raikou).
    * Align Boardfarm inventory and env config to the running topology.
    * Verify all five canonical impairment presets are present in env config.

    **Exit criteria:**
    * `raikou up` brings all containers online without manual intervention.
    * Boardfarm `parse_boardfarm_config()` resolves all devices (DUT, both TrafficControllers, QoEClient, services) without error.
    * End-to-end ping from LAN Client to WAN-side service passes through DUT via both WAN paths.

3. **Phase 3: Validation**
    * Run all four Pre-Hardware Validation Scenarios (Section 4.3).
    * Execute QoE baseline measurements under `pristine` profile for all three service categories.
    * Measure failover convergence time baseline (no threshold enforced yet — record for calibration).

    **Exit criteria:**
    * All four Pre-Hardware Validation Scenarios pass in ≥ 3 consecutive runs.
    * QoE SLOs pass under `pristine` and `cable_typical` profiles.
    * Failover convergence baseline is recorded (P50, P95 over 10 runs).
    * `dut.get_active_wan_interface()` returns the correct interface after each path-steering event.
    * No step definition contains business logic (QoE math, path polling loops, device CLI commands).

4. **Phase 4: Linux Router Expansion (Optional)**
    * Add **StrongSwan** to DUT for VPN/overlay encryption validation.
    * Add **tc** for QoS shaping validation.
    * Add **iptables** for firewall/security validation.
    * Implement `IperfTrafficGenerator` and `KaliThreatSimulator` device classes.
    * Implement `threat_use_cases.py` and `security_use_cases.py`.
    * Expand to **Triple WAN** topology.
    * *(If pursued, done before moving to commercial hardware.)*

    **Exit criteria:**
    * QoS: LLQ test confirms voice traffic (DSCP EF) maintains MOS > 4.0 under link saturation.
    * Security: Port scan is detected; C2 callback is blocked; EICAR download is blocked.
    * Triple WAN: `dut.get_active_wan_interface()` correctly identifies WAN3 as failover when WAN1 and WAN2 are both degraded.

5. **Phase 5: Commercial DUT Integration**
    * Swap Linux Router for Cisco/Fortinet/VMware virtual or physical appliances.
    * Develop vendor-specific `WANEdgeDevice` implementations (e.g. `CiscoC8000DUT`, `FortiGateDUT`).
    * Update Boardfarm inventory config to point to the physical/virtual DUT.
    * **No test scenario changes are expected** — all use cases depend only on the `WANEdgeDevice` template.
    * Execute "Scenario A: Brownout Resilience" and all Phase 3 / Phase 4 use cases against commercial DUT.

    **Transition checklist (what changes vs. Phase 3/4):**
    * Boardfarm inventory: new device type, IP, credentials, connection method.
    * New device class implementing `WANEdgeDevice` (vendor-specific CLI/API).
    * Env config: any vendor-specific `apply_policy()` dict format.
    * Test scenarios: unchanged.
