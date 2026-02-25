# QoE Client Implementation Plan

**Date:** February 24, 2026
**Status:** Design Document
**Related:** `WAN_Edge_Appliance_testing.md`, `LinuxSDWANRouter_Implementation_Plan.md`

---

## 1. Overview

This document defines the implementation plan for the **QoE (Quality of Experience) Client**. This component is responsible for simulating end-user behavior (browsing, streaming, conferencing) and measuring the perceived quality of the network connection.

### Purpose
1.  **User Simulation:** Replaces manual testing with automated, repeatable user actions (loading pages, watching video).
2.  **Metric Collection:** Captures high-fidelity metrics (TTFB, Rebuffer Ratio, MOS) that network-level stats (ping/loss) miss.
3.  **SLO Verification:** Provides the data source for asserting Service Level Objectives defined in the Technical Brief.

---

## 2. Architecture & Components

The QoE Client is built on **Playwright**, a modern browser automation framework, running inside a containerized environment.

### 2.1 Software Stack

| Component | Software Package | Purpose |
| :--- | :--- | :--- |
| **OS** | Ubuntu 22.04 LTS (or similar) | Standard base for browser support. |
| **Automation** | Python Playwright | Driving the browser, capturing navigation timing. |
| **Browsers** | Chromium, Firefox, WebKit | Rendering engines. |
| **Traffic Gen** | `iperf3` client | Generating background load if needed (optional). |
| **Runtime** | Python 3.10+ | Boardfarm device driver execution. |
| **Display** | Xvfb / Headless Mode | Running browsers without a physical monitor. |
| **SOCKS Proxy** | `dante-server` | Developer debugging — routes host browser traffic through the testbed LAN (see §3.4). |

### 2.2 Integration with Boardfarm

The `QoEClient` connects to the testbed orchestration via **SSH** (standard Boardfarm pattern) or by running the driver locally if the container shares the network namespace (less common). The primary interaction model is:

1.  Boardfarm (Host) calls `client.measure_productivity()`.
2.  `PlaywrightQoEClient` driver (Python) executes a Playwright script *inside* the container/VM.
3.  Metrics (`QoEResult`) are returned to Boardfarm for assertion.

---

## 3. Implementation Details

### 3.1 Docker Container Specification

**Dockerfile Strategy:**
*   Start from Microsoft's official `mcr.microsoft.com/playwright:v1.xx.0-jammy` image. This pre-installs all browser dependencies and browsers.
*   Install `openssh-server` to allow Boardfarm to connect and drive it.
*   Install `iperf3` for auxiliary bandwidth testing.
*   Install `dante-server` for the developer SOCKS v5 proxy (see §3.4).
*   Set up a non-root user (e.g., `boardfarm`) for running the browser (browsers often dislike running as root).

**Dockerfile (key additions):**

```dockerfile
FROM mcr.microsoft.com/playwright:v1.xx.0-jammy

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server \
    iperf3 \
    iproute2 \
    dante-server \
    && rm -rf /var/lib/apt/lists/*

COPY ./init /root/init
RUN chmod +x /root/init

CMD ["/bin/bash", "/root/init"]
```

**Container init script (`init`):**

The init script waits for the Raikou-injected `eth1` interface (LAN segment, `192.168.10.10`), configures Dante to route proxied traffic out via `eth1`, then starts SSH and Dante. This mirrors the existing `lan` container pattern.

```bash
#!/bin/bash

# Wait for eth1 (injected by Raikou onto the lan-segment OVS bridge)
count=0
while [ $count -lt 30 ]; do
    if ip addr show eth1 2>/dev/null | grep -q "inet "; then
        break
    fi
    echo "Waiting for eth1 (lan-segment)..."
    sleep 1
    count=$((count + 1))
done

# Dante routes proxied traffic out via eth1 → DUT → WAN → north-side services.
# The developer's browser traverses the exact same network path as Playwright.
ETH1_IP=$(ip addr show eth1 | grep "inet " | awk '{print $2}' | cut -d/ -f1)
EXTERNAL="${ETH1_IP:-eth1}"

cat > /etc/danted.conf << EOF
logoutput: stderr
internal: 0.0.0.0 port = 8080
external: $EXTERNAL
clientmethod: none
socksmethod: username none
user.privileged: root
user.unprivileged: nobody
client pass {
    from: 0.0.0.0/0 to: 0.0.0.0/0
    log: connect disconnect error
}
socks pass {
    from: 0.0.0.0/0 to: 0.0.0.0/0
    log: connect disconnect error
}
EOF

service danted start
/usr/sbin/sshd -D
```

### 3.2 Driver Implementation (`PlaywrightQoEClient`)

This class implements the `QoEClient` template defined in the Technical Brief.

**Location:** `boardfarm3/devices/playwright_qoe_client.py`

#### `QoEResult` data class

All measurement methods return a `QoEResult` instance. Fields are `None` when not applicable to the measurement type.

```python
from dataclasses import dataclass, field

@dataclass
class QoEResult:
    """Result of a single QoE measurement. All fields are optional (None if not measured)."""

    # --- Productivity / page-load metrics ---
    ttfb_ms: float | None = None
    """Time to First Byte (ms): responseStart - requestStart (Navigation Timing)."""
    load_time_ms: float | None = None
    """Full page load time (ms): loadEventEnd - navigationStart."""

    # --- Streaming metrics ---
    startup_time_ms: float | None = None
    """Video startup latency (ms): time from play() to 'playing' event."""
    rebuffer_ratio: float | None = None
    """Fraction of session spent buffering (0.0 = no rebuffering, 1.0 = all buffering)."""

    # --- Conferencing metrics ---
    latency_ms: float | None = None
    """Round-trip time (ms) from RTCPeerConnection.getStats()."""
    jitter_ms: float | None = None
    """Jitter (ms) from RTCPeerConnection.getStats()."""
    packet_loss_pct: float | None = None
    """Packet loss percentage from RTCPeerConnection.getStats()."""
    mos: float | None = None
    """Mean Opinion Score (1.0–5.0) calculated by lib/qoe.py using the ITU-T G.107 E-model."""

    # --- Transport metadata (Phase 3.5+) ---
    protocol: str | None = None
    """HTTP version actually negotiated, e.g. 'http/1.1', 'h2', 'h3'.
    Populated from Navigation Timing entry nextHopProtocol (zero additional cost).
    None in Phase 1–3 (plain HTTP — nextHopProtocol not available for non-TLS).
    Available once HTTPS is enabled in Phase 3.5."""
```

#### Key Methods & Logic

1.  **`measure_productivity(url, scenario="page_load")`**
    *   **Action:** Launch browser, navigate to `url`, wait for `networkidle`.
    *   **Metrics:**
        *   Extract `window.performance.timing` API data.
        *   **TTFB:** `responseStart - requestStart`
        *   **Load Time:** `loadEventEnd - navigationStart`
        *   **Protocol:** `performance.getEntriesByType('navigation')[0].nextHopProtocol` (populated when HTTPS is in use)
    *   **Success:** HTTP 200 OK and specific element visibility.

2.  **`measure_streaming(stream_url, duration_s)`**
    *   **Action:** Navigate to a page hosting a `<video>` player (HLS/DASH).
    *   **Metrics:**
        *   Poll `<video>` element properties: `buffered`, `currentTime`, `waiting` events.
        *   **Startup Time:** Time from `play()` to `playing` event.
        *   **Rebuffer Ratio:** `(Total time spent in 'waiting' state) / (Total session duration)`.
    *   **Reference:** HTML5 Video Events.

3.  **`measure_conferencing(session_url, duration_s)`**
    *   **Action:** Join a WebRTC session on the testbed's `pion`-based WebRTC Echo server.
    *   **Metrics:**
        *   Access `RTCPeerConnection.getStats()`.
        *   **Latency:** `roundTripTime`
        *   **Jitter:** `jitter`
        *   **Packet Loss:** `packetsLost`
    *   **MOS Calculation:** Pass these raw network stats to `lib/qoe.py` to calculate the R-Factor score (1-5).

### 3.3 MOS Calculation Logic (`lib/qoe.py`)

The Mean Opinion Score (MOS) will be estimated using the **E-model (ITU-T G.107)** simplified for IP networks.

**Formula Concept:**
`R = Ro - Is - Id - Ie + A`
*   `Ro`: Basic signal-to-noise ratio (default 93.2).
*   `Id`: Delay impairment (function of latency).
*   `Ie`: Equipment impairment (function of packet loss and codec).

**Code Location:** `boardfarm3/lib/qoe.py`
This library function will be pure Python, taking `latency`, `jitter`, and `loss` as inputs and returning a float `1.0 - 5.0`.

### 3.4 Developer Debugging Access

Two complementary tools are provided for debugging QoE test failures, covering different failure modes without compromising testbed isolation.

#### SOCKS v5 Proxy (Dante) — Network & Service Debugging

The `lan-client` container runs a **Dante SOCKS v5 proxy** on port 8080 (exposed to the host as port 18090 — see `SDWAN_Testbed_Configuration.md §5.1`). This proxy routes outbound traffic via `eth1`, the same interface Playwright uses, meaning the developer's browser traverses the identical network path — including any active `tc netem` impairment profiles on WAN1/WAN2.

**What this enables:**
- Browse directly to `http://172.16.0.10:8080/` (productivity server) and verify the page renders correctly under current impairment conditions.
- Access the HLS streaming endpoint at `http://172.16.0.10:8081/hls/default/index.m3u8` to verify content availability.
- Reach the WebRTC conferencing server at `wss://172.16.0.11:8443/` for manual session testing.
- Experience impairment profiles firsthand — browsing under `satellite` conditions (600 ms latency) is useful when calibrating QoE SLOs.

**Browser configuration (Firefox recommended):**

```
Settings → Network Settings → Manual Proxy Configuration:
  SOCKS Host: 127.0.0.1
  Port: 18090
  SOCKS v5
  ✓ Proxy DNS when using SOCKS v5
```

**Testbed isolation:** The proxy only exposes the LAN-side network perspective of the `lan-client` container. Traffic still passes through the DUT and the WAN impairment containers — there is no backdoor into the simulated network. The north-side services (`172.16.0.x`) are reachable only by traversing the DUT, exactly as Playwright does.

#### Playwright Trace Viewer — Automated Session Debugging

For debugging failures in Playwright's automated browser session itself (element selection failures, unexpected page states, timing issues), use Playwright's built-in trace recording. This requires no container changes and produces a complete visual record of every action.

**Enable tracing** by passing `--trace on` to the Playwright launch config, or by wrapping the measurement call:

```python
async with browser.new_context() as ctx:
    await ctx.tracing.start(screenshots=True, snapshots=True, sources=True)
    result = await measure_productivity(ctx, url)
    await ctx.tracing.stop(path="trace.zip")
```

**View the trace** locally after test completion:

```bash
playwright show-trace trace.zip
```

The trace viewer shows a full screenshot timeline, the DOM state at each step, all network requests and responses, and browser console output — covering every failure mode that the SOCKS proxy cannot diagnose.

**CI integration:** Store `trace.zip` as a CI artifact on test failure. The trace can be viewed in the Playwright Trace Viewer web UI without any local Playwright installation.

---

## 4. North-Side Service Requirements

The QoE Client needs targets (servers) to measure against. These "North-Side" containers must be defined in the `Application_Services_Implementation_Plan.md`.

*   **Productivity Target:** A lightweight HTTP server returning a page with a specific weight (e.g., 2MB of JS/CSS) to simulate a SaaS app load.
*   **Streaming Target:** An Nginx server hosting `.m3u8` (HLS) playlists and video segments.
*   **Conferencing Target:** `pion`-based WebRTC Echo server (see `Application_Services_Implementation_Plan.md` Section 3.3).

---

## 5. Development Phases

> See the [Component Readiness Map](WAN_Edge_Appliance_testing.md#component-readiness-map) in `WAN_Edge_Appliance_testing.md §5` for how these phases map to project-level gates.

1.  **Phase 1: Container Build** *(Project Phase 1 — Foundation)*
    *   Build Docker image with Playwright + SSH + `dante-server`.
    *   Verify Dante SOCKS v5 proxy is reachable at host port 18090.
    *   Verify developer browser can reach `http://172.16.0.10:8080/` through the proxy.
    *   Verify manual Playwright script execution via SSH.
2.  **Phase 2: Driver Logic (Productivity)** *(Project Phase 1 — Foundation)*
    *   Implement `measure_productivity`.
    *   Test against a public site (e.g., `example.com`) or local Nginx.
3.  **Phase 3: Advanced Metrics (Streaming/Conferencing)** *(Project Phase 1 — Foundation)*
    *   Implement video event listeners for Rebuffer Ratio.
    *   Implement `getStats()` parsing for WebRTC.
    *   Implement MOS calculator in `lib/qoe.py`.
4.  **Phase 4: Integration** *(Project Phase 2 — Raikou Integration)*
    *   Deploy in Raikou.
    *   Run Boardfarm scenarios asserting SLOs.
5.  **Phase 3.5: Testbed CA Trust & Protocol Verification** *(Project Phase 3.5 — Digital Twin, Optional)*

    > **Prerequisite:** Testbed CA generated and `ca.crt` mounted into the `lan-client` container per **[`Testbed_CA_Setup.md §4–7`](Testbed_CA_Setup.md)**. The `update-ca-certificates` call described there registers the CA with both the system OpenSSL store and the NSS database used by Chromium.

    *   The `lan-client` init script calls `update-ca-certificates` at startup (see `Testbed_CA_Setup.md §7`), which makes the CA trusted by Playwright/Chromium automatically. No Playwright launch-flag override is needed.

    *   **Exit criterion — trust store:** Verify from inside the container:
        ```bash
        openssl verify \
            -CAfile /usr/local/share/ca-certificates/testbed-ca.crt \
            /usr/local/share/ca-certificates/testbed-ca.crt
        # Expected: OK
        ```

    *   **Exit criterion — HTTPS access:**
        ```bash
        curl -sv --cacert /usr/local/share/ca-certificates/testbed-ca.crt \
            https://172.16.0.10/
        # Expected: TLSv1.3, issuer "SD-WAN Testbed CA", HTTP 200
        ```
    *   Verify `QoEResult.protocol` returns `"h2"` for the HTTPS productivity server.
    *   Verify `QoEResult.protocol` returns `"h3"` after Chromium upgrades via `Alt-Svc` header (requires a second request to the same origin).
    *   Update `measure_productivity()` to read `nextHopProtocol` and populate `QoEResult.protocol`.
    *   **No changes to test use cases or BDD scenarios** — the `protocol` field is informational metadata; SLO assertions remain on TTFB and load time.

---

## 6. VM Migration Note

To migrate this component to a VM:
1.  Provision a Ubuntu VM.
2.  `pip install playwright`
3.  `playwright install --with-deps`
4.  Ensure X11 forwarding or Xvfb is configured if running headless is not sufficient (Playwright headless usually works fine).
5.  Update Boardfarm inventory.
