# TrafficGenerator Implementation Plan

**Date:** February 24, 2026
**Status:** Design Document
**Related:** `WAN_Edge_Appliance_testing.md`, `Traffic_Management_Components_Architecture.md`

---

## 1. Overview

### Purpose

The **Traffic Generator** injects calibrated background load into the testbed to create the traffic contention required for QoS validation. Without a controlled background load, queue pressure cannot be created and QoS tests (DSCP prioritisation, LLQ effectiveness, shaper/policer verification) cannot produce meaningful results.

The Traffic Generator is used exclusively as a **background load source** — it does not measure application quality (that is the `QoEClient`'s role). It answers: *"Is the correct amount of traffic, at the correct DSCP marking, flowing across the path?"*

### Key Design Principles

1. **Test Portability:** Use cases depend on the `TrafficGenerator` template only. They never call iPerf3 or Trex CLIs directly.
2. **Async Model:** `start_traffic()` is non-blocking. The test injects load, performs QoE measurement, then calls `stop_traffic()` to retrieve results and tear down.
3. **DSCP Transparency:** The generator marks traffic with a caller-specified DSCP value. The DUT's QoS policy is what re-marks or preserves it — the generator simply ensures traffic enters the network with the intended marking.
4. **Server Placement:** Each `TrafficGenerator` device in inventory includes a co-located iPerf3 server target. The server runs on the North-side (Application Services container or dedicated host) and the client runs on the generator device itself (LAN side). This creates a realistic LAN→WAN traffic flow through the DUT.

---

## 2. Architecture & Components

### 2.1 Boardfarm Template

**Location:** `boardfarm3/templates/traffic_generator.py`

The abstract interface all test cases depend on. Already defined in `WAN_Edge_Appliance_testing.md §3.4` — reproduced here for completeness.

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class TrafficSpec:
    protocol: str           # "tcp" | "udp"
    bandwidth_mbps: int     # Target sending rate
    dscp: int               # DSCP value (0–63), e.g. 46 = EF (voice), 34 = AF41 (video)
    duration_s: int         # Flow duration in seconds
    destination: str        # iPerf3 server IP or hostname
    parallel_streams: int = 1  # Number of parallel iPerf3 streams

@dataclass
class TrafficResult:
    sent_mbps: float        # Average sending rate achieved
    received_mbps: float    # Average receiving rate at server
    loss_percent: float     # UDP packet loss (0.0 for TCP)
    jitter_ms: float | None # UDP jitter (None for TCP)
    dscp_marking: int | None  # DSCP observed at receiver, if measurable

class TrafficGenerator(ABC):
    """Abstract background load generator for QoS and contention tests.

    Implementations: IperfTrafficGenerator (Linux/Docker), TrexTrafficGenerator (appliance).
    """

    @abstractmethod
    def start_traffic(self, spec: TrafficSpec) -> None:
        """Start a background traffic flow. Non-blocking — returns immediately.

        The flow runs until stop_traffic() is called or duration_s expires.
        :param spec: Traffic parameters (rate, protocol, DSCP, destination).
        """

    @abstractmethod
    def stop_traffic(self) -> TrafficResult:
        """Stop the active flow and return measured results.

        Blocks until the iPerf3 process terminates and results are parsed.
        Safe to call even if the flow has already expired (returns last result).
        :return: TrafficResult with achieved rates and loss statistics.
        """

    @abstractmethod
    def run_traffic(self, spec: TrafficSpec) -> TrafficResult:
        """Run a traffic flow to completion and return results. Blocking.

        Equivalent to start_traffic() + sleep(spec.duration_s) + stop_traffic().
        Use for flows where the test does not need to do anything during the flow.
        :return: TrafficResult with achieved rates and loss statistics.
        """
```

### 2.2 Implementation Types

| Testbed Type | Implementation Class | Underlying Tool | Connection |
| :--- | :--- | :--- | :--- |
| **Functional (Docker/Raikou)** | `IperfTrafficGenerator` | iPerf3 | SSH into LAN-side container |
| **External Linux host (VM or physical)** | `IperfTrafficGenerator` | iPerf3 | SSH into host |
| **Dedicated appliance (pre-production)** | `TrexTrafficGenerator` | Cisco TRex | REST API |

The same `IperfTrafficGenerator` class covers both the Docker and external Linux host cases — only the inventory config differs (container vs. physical host IP/credentials).

### 2.3 iPerf3 Server Placement

The iPerf3 server runs on the **North-side Application Services container** (the same host as `NginxProductivityServer` and `NginxStreamingServer`). This mirrors production reality: the traffic generator simulates a LAN client sending bulk data to a cloud/internet service.

```
[IperfTrafficGenerator]  →  [DUT]  →  [TrafficController]  →  [AppServer (iPerf3 server)]
    LAN side                  DUT          WAN emulator             North side
```

The iPerf3 server is started at Boardfarm initialisation (as part of the Application Services container startup) and remains running for the duration of the test session. Each `start_traffic()` call starts a new iPerf3 client session against the persistent server.

The server's IP address is provided to `TrafficGenerator` via the `TrafficSpec.destination` field, which is set by the use case (not hardcoded in the driver).

---

## 3. Implementation Details

### 3.1 Docker Container Specification (`IperfTrafficGenerator` — functional testbed)

```dockerfile
FROM ubuntu:22.04
RUN apt-get update && apt-get install -y \
    iperf3 \
    openssh-server \
    iproute2 \
    && rm -rf /var/lib/apt/lists/*
# SSH daemon for Boardfarm console access
RUN mkdir /run/sshd
CMD ["/usr/sbin/sshd", "-D"]
```

**Packages:**
- `iperf3` — traffic generation client
- `openssh-server` — Boardfarm SSH console access
- `iproute2` — interface inspection (`ip addr`, `ip route`)

**Notes:**
- The container has no iPerf3 server. The server runs on the Application Services container.
- The same image can be used for an external Linux host by provisioning via `apt` instead of Docker.

### 3.2 Driver Implementation (`IperfTrafficGenerator`)

**Location:** `boardfarm3/devices/iperf_traffic_generator.py`

```python
import json
import threading
from boardfarm3.devices.base_devices import LinuxDevice
from boardfarm3.templates.traffic_generator import TrafficGenerator, TrafficSpec, TrafficResult

class IperfTrafficGenerator(LinuxDevice, TrafficGenerator):
    """TrafficGenerator implementation using iPerf3 over SSH.

    Works for both Docker containers and external Linux hosts (VM/physical).
    The only difference is the inventory config (IP, port, credentials).
    """

    def __init__(self, config: dict, cmdline_args) -> None:
        super().__init__(config, cmdline_args)
        self._active_result: TrafficResult | None = None
        self._lock = threading.Lock()

    def start_traffic(self, spec: TrafficSpec) -> None:
        """Start iPerf3 client in background (non-blocking)."""
        cmd = _build_iperf3_cmd(spec, background=True)
        self._console.sendline(cmd)
        # iPerf3 writes JSON result to /tmp/iperf3_result.json on completion

    def stop_traffic(self) -> TrafficResult:
        """Send SIGINT to iPerf3, wait for JSON output, parse result."""
        self._console.sendline("kill $(cat /tmp/iperf3.pid) 2>/dev/null; wait")
        raw = self._console.sendline_and_read("cat /tmp/iperf3_result.json")
        return _parse_iperf3_json(raw)

    def run_traffic(self, spec: TrafficSpec) -> TrafficResult:
        """Run iPerf3 to completion (blocking)."""
        cmd = _build_iperf3_cmd(spec, background=False)
        raw = self._console.sendline_and_read(cmd, timeout=spec.duration_s + 10)
        return _parse_iperf3_json(raw)


def _build_iperf3_cmd(spec: TrafficSpec, background: bool) -> str:
    """Build the iPerf3 client command from a TrafficSpec."""
    parts = [
        "iperf3",
        f"--client {spec.destination}",
        f"--bandwidth {spec.bandwidth_mbps}M",
        f"--time {spec.duration_s}",
        f"--parallel {spec.parallel_streams}",
        f"--tos {spec.dscp << 2}",   # iPerf3 uses ToS byte; DSCP occupies the top 6 bits
        "--json",
    ]
    if spec.protocol == "udp":
        parts.append("--udp")
    if background:
        parts += ["--pidfile /tmp/iperf3.pid", "> /tmp/iperf3_result.json 2>&1 &"]
    return " ".join(parts)


def _parse_iperf3_json(raw: str) -> TrafficResult:
    """Parse iPerf3 JSON output into a TrafficResult."""
    data = json.loads(raw)
    end = data["end"]
    # TCP: sum in intervals
    sent = end.get("sum_sent", end.get("sum", {}))
    recv = end.get("sum_received", end.get("sum", {}))
    loss = recv.get("lost_percent", 0.0)
    jitter = recv.get("jitter_ms")
    return TrafficResult(
        sent_mbps=sent.get("bits_per_second", 0) / 1e6,
        received_mbps=recv.get("bits_per_second", 0) / 1e6,
        loss_percent=loss,
        jitter_ms=jitter,
        dscp_marking=None,  # iPerf3 does not report received DSCP
    )
```

### 3.3 DSCP Marking

iPerf3 sets the **IP ToS byte** via `--tos`. The DSCP value occupies the top 6 bits of the ToS byte, so the conversion is:

```
ToS = DSCP << 2
```

| DSCP Name | DSCP Value | ToS Value | Traffic Class |
| :--- | :--- | :--- | :--- |
| Best Effort (BE) | 0 | 0 | Default |
| AF41 | 34 | 136 | Video (bulk background) |
| EF | 46 | 184 | Voice (priority) |
| CS5 | 40 | 160 | Signalling |

> **Note:** iPerf3 marks the **sending** socket with the specified ToS value. Whether this marking is **preserved or re-written** across the DUT and WAN overlay is exactly what the QoS test is asserting. The generator's role is only to ensure the traffic enters the network with the intended DSCP — it does not verify what arrives at the server.

### 3.4 Async Traffic Model

`start_traffic()` is non-blocking by design. The expected test pattern for QoS validation is:

```python
# 1. Start background load (non-blocking)
traffic_use_cases.start_traffic(generator, spec=TrafficSpec(
    protocol="udp",
    bandwidth_mbps=80,       # Saturate the 100 Mbps WAN link
    dscp=0,                  # BE — low priority background traffic
    duration_s=60,
    destination=app_server_ip,
))

# 2. Assert QoE SLO for priority traffic (while background load is running)
qoe_result = qoe_use_cases.measure_conferencing(client, conf_server)
assert qoe_result.mos_score >= 4.0, "MOS below threshold under load"

# 3. Stop background load and collect generator results
result = traffic_use_cases.stop_traffic(generator)
assert result.loss_percent < 1.0, "Background flow lost too much"
```

### 3.5 TrexTrafficGenerator (Hardware Appliance)

For pre-production testbeds with a dedicated Cisco TRex appliance:

```python
class TrexTrafficGenerator(BoardfarmDevice, TrafficGenerator):
    """TrafficGenerator implementation using Cisco TRex via REST API."""

    def start_traffic(self, spec: TrafficSpec) -> None:
        self._api.start_stream(
            rate_mbps=spec.bandwidth_mbps,
            dscp=spec.dscp,
            protocol=spec.protocol,
            destination=spec.destination,
        )

    def stop_traffic(self) -> TrafficResult:
        stats = self._api.stop_stream_and_get_stats()
        return TrafficResult(
            sent_mbps=stats["tx_bps"] / 1e6,
            received_mbps=stats["rx_bps"] / 1e6,
            loss_percent=stats["loss_pct"],
            jitter_ms=stats.get("jitter_ms"),
            dscp_marking=stats.get("rx_dscp"),  # TRex can report received DSCP
        )

    def run_traffic(self, spec: TrafficSpec) -> TrafficResult:
        self.start_traffic(spec)
        time.sleep(spec.duration_s)
        return self.stop_traffic()
```

---

## 4. Integration Plan

### 4.1 Boardfarm Inventory

```json
{
  "name": "lan_traffic_gen",
  "type": "iperf_traffic_generator",
  "connection_type": "ssh",
  "ipaddr": "192.168.100.20",
  "port": 22,
  "username": "root",
  "password": "boardfarm"
}
```

For an external Linux host or VM, the `type` is identical — only `ipaddr` and credentials differ.

For the Trex appliance:

```json
{
  "name": "trex_generator",
  "type": "trex_traffic_generator",
  "connection_type": "rest",
  "ipaddr": "10.0.0.50",
  "rest_port": 8090
}
```

### 4.2 iPerf3 Server on Application Services Container

The Application Services container must expose an iPerf3 server. Add to its startup:

```bash
# Start iPerf3 server on the Application Services container
iperf3 --server --daemon --pidfile /run/iperf3.pid
```

The server listens on the default port (5201). The server IP is exposed via the `TrafficSpec.destination` field populated by the test use case from the `AppServer` device config.

### 4.3 Use Cases

**Location:** `boardfarm3/use_cases/traffic_generator.py`

```python
from boardfarm3.templates.traffic_generator import TrafficGenerator, TrafficSpec, TrafficResult

def start_traffic(generator: TrafficGenerator, spec: TrafficSpec) -> None:
    """Start background load. Non-blocking."""
    generator.start_traffic(spec)

def stop_traffic(generator: TrafficGenerator) -> TrafficResult:
    """Stop background load and return results."""
    return generator.stop_traffic()

def run_traffic(generator: TrafficGenerator, spec: TrafficSpec) -> TrafficResult:
    """Run traffic to completion. Blocking."""
    return generator.run_traffic(spec)

def saturate_wan_link(
    generator: TrafficGenerator,
    app_server_ip: str,
    link_bandwidth_mbps: int,
    dscp: int = 0,
    utilisation_pct: float = 0.85,
) -> None:
    """Start a background flow that saturates the WAN link to a given utilisation.

    Designed to be paired with a QoE assertion and a subsequent stop_traffic() call.

    :param utilisation_pct: Fraction of link capacity to consume (default 85%).
    """
    target_mbps = int(link_bandwidth_mbps * utilisation_pct)
    spec = TrafficSpec(
        protocol="udp",
        bandwidth_mbps=target_mbps,
        dscp=dscp,
        duration_s=300,     # Long enough for any QoE measurement; caller stops early
        destination=app_server_ip,
    )
    generator.start_traffic(spec)
```

### 4.4 Development Phases

> See the [Component Readiness Map](WAN_Edge_Appliance_testing.md#component-readiness-map) in `WAN_Edge_Appliance_testing.md §5` for how these phases map to project-level gates.

1. **Phase 1: Container Build** *(Project Phase 4 — Expansion)*
    * Build Docker image with iPerf3 + SSH.
    * Add iPerf3 server startup to Application Services container.
    * Verify manual `iperf3 --client` run via SSH.

2. **Phase 2: Driver Implementation** *(Project Phase 4 — Expansion)*
    * Implement `IperfTrafficGenerator` class.
    * Unit test DSCP ToS conversion and JSON result parsing against mock output.
    * Verify `start_traffic()` / `stop_traffic()` async model.

3. **Phase 3: Integration** *(Project Phase 4 — Expansion)*
    * Deploy in Raikou alongside existing topology.
    * Run QoS contention test: saturate WAN link with BE traffic, assert MOS > 4.0 for EF-marked conferencing flow.
    * Verify DSCP preservation end-to-end using `ip-tc` counters on the DUT.

> **Note:** The `TrafficGenerator` is only required for **Project Phase 4 (Expansion)** — QoS validation is not in scope for Phases 1–3 (foundation and basic QoE/path-steering validation). This differs from `TrafficController` and `QoEClient`, which are required from Phase 1.

---

## 5. VM Migration Note

The `IperfTrafficGenerator` requires no changes to migrate from Docker to a VM or physical host:

1. Provision a Ubuntu/Debian Linux host.
2. Run `apt install iperf3 openssh-server`.
3. Update Boardfarm inventory `ipaddr` and credentials.

The Python driver requires no changes — it connects via SSH regardless of whether the target is a container or a bare-metal host.
