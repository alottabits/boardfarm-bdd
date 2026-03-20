# Design: QoE Client (Playwright-based Measurement)

| Field | Value |
| :--- | :--- |
| **Status** | Implemented |
| **Date** | 2026-03-20 |
| **Related** | [`architecture.md`](architecture.md), [`testbed-configuration.md`](testbed-configuration.md), [`ADR-0001`](../../adr/0001-scope-to-digital-twin-phase-3.5.md) |

---

## 1. Context and Scope

The QoE (Quality of Experience) Client is the **LAN-side measurement client** in the WAN Edge testing framework. It sits on the LAN segment of the testbed, behind the Device Under Test, and exercises the same network path that a real end-user device would traverse.

Its role is to simulate end-user behaviour — page loads, video streaming, WebRTC conferencing — and collect high-fidelity application-layer metrics (TTFB, rebuffer ratio, MOS) that network-level counters like ping and packet loss cannot capture. These metrics feed directly into Service Level Objective assertions defined in the Technical Brief.

---

## 2. Non-Goals

The following capabilities are explicitly outside the QoE Client's scope. Each is handled by a dedicated testbed component (see [ADR-0001](../../adr/0001-scope-to-digital-twin-phase-3.5.md)).

- **iPerf3 background load generation.** Sustained bandwidth flooding is the TrafficGenerator's responsibility. The QoE Client carries an `iperf3` binary for auxiliary checks, but orchestrated load profiles belong to the TrafficGenerator component.
- **Security attack simulation.** Malware downloads, exploit payloads, and protocol abuse are the MaliciousHost's responsibility.

---

## 3. Architecture & Components

The QoE Client is built on **Playwright**, running inside a containerized environment on the testbed LAN segment.

### 3.1 Software Stack

| Component | Software Package | Purpose |
| :--- | :--- | :--- |
| **OS** | Ubuntu 22.04 LTS | Standard base for browser support. |
| **Automation** | Python Playwright | Drives the browser and captures navigation timing. |
| **Browsers** | Chromium, Firefox, WebKit | Rendering engines. |
| **Traffic Gen** | `iperf3` client | Auxiliary bandwidth checks. |
| **Runtime** | Python 3.10+ | Boardfarm device driver execution. |
| **Display** | Xvfb / Headless Mode | Runs browsers without a physical monitor. |
| **SOCKS Proxy** | `dante-server` | Developer debugging — routes host browser traffic through the testbed LAN (see §5.1). |

### 3.2 Integration with Boardfarm

The `QoEClient` connects to testbed orchestration via **SSH** (standard Boardfarm pattern). The primary interaction model is:

1. Boardfarm (Host) calls `client.measure_productivity()`.
2. `PlaywrightQoEClient` driver (Python) executes a Playwright script inside the container.
3. Metrics (`QoEResult`) are returned to Boardfarm for assertion.

---

## 4. Implementation Details

### 4.1 Docker Container Specification

The image starts from Microsoft's official `mcr.microsoft.com/playwright:v1.xx.0-jammy` base, which pre-installs all browser dependencies and browsers. On top of this, it adds SSH access for Boardfarm, `iperf3`, and the Dante SOCKS proxy.

A non-root user (`boardfarm`) runs the browser, since Chromium restricts root execution.

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

The init script waits for the Raikou-injected `eth1` interface (LAN segment, `192.168.10.10`), configures Dante to route proxied traffic out via `eth1`, registers the testbed CA in both the system trust store and the NSS database (required for Chromium/QUIC), then starts SSH and Dante.

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

### 4.2 Driver Implementation (`PlaywrightQoEClient`)

This class implements the `QoEClient` template defined in the Technical Brief.

**Location:** `boardfarm3/devices/playwright_qoe_client.py`

#### `QoEResult` Dataclass

**Canonical location:** `boardfarm3/lib/qoe.py` — imported by the `QoEClient` template (`boardfarm3/templates/qoe_client.py`) and the use-case layer (`boardfarm3/use_cases/qoe.py`). Defined once, used at all layers:

```
boardfarm3/lib/qoe.py                        ← QoEResult + MOS R-Factor calculation
boardfarm3/templates/qoe_client.py            ← QoEClient template (imports QoEResult)
boardfarm3/devices/playwright_qoe_client.py   ← concrete Playwright implementation
boardfarm3/use_cases/qoe.py                   ← SLO assertion helpers (imports QoEResult)
```

All measurement methods return a `QoEResult` instance. Fields are `None` when not applicable to the measurement type. `success` defaults to `True`; the device class sets it to `False` when the underlying request fails or is blocked (e.g., EICAR download intercepted by Application Control).

```python
from dataclasses import dataclass

@dataclass
class QoEResult:
    """Result of a single QoE measurement."""

    # --- Productivity / page-load metrics ---
    ttfb_ms: float | None = None
    """Time to First Byte (ms): responseStart - requestStart (Navigation Timing)."""
    load_time_ms: float | None = None
    """Full page load time (ms): loadEventEnd - navigationStart."""

    # --- Streaming metrics ---
    startup_time_ms: float | None = None
    """Video startup latency (ms): time from play() to 'playing' event."""
    rebuffer_ratio: float | None = None
    """Fraction of session spent buffering (0.0–1.0)."""

    # --- Conferencing metrics (WebRTC getStats()) ---
    latency_ms: float | None = None
    """Round-trip time (ms) from RTCPeerConnection.getStats()."""
    jitter_ms: float | None = None
    """Jitter (ms) from RTCPeerConnection.getStats()."""
    packet_loss_pct: float | None = None
    """Packet loss percentage from RTCPeerConnection.getStats()."""
    mos_score: float | None = None
    """Mean Opinion Score (1.0–5.0), ITU-T G.107 E-model via lib/qoe.py."""

    # --- Transport metadata ---
    protocol: str | None = None
    """HTTP version actually negotiated, e.g. 'http/1.1', 'h2', 'h3'.
    Populated from Navigation Timing nextHopProtocol (zero additional cost).
    Available for HTTPS connections; None for plain HTTP."""

    # --- Request outcome ---
    success: bool = True
    """False when the underlying request was blocked or failed (e.g. HTTP 4xx/5xx,
    network error, or EICAR download intercepted)."""
```

#### Key Methods

1. **`measure_productivity(url, scenario="page_load")`**
    - Launches a browser, navigates to `url`, and waits for `networkidle`.
    - Extracts `window.performance.timing` data: **TTFB** (`responseStart - requestStart`), **Load Time** (`loadEventEnd - navigationStart`).
    - Reads `performance.getEntriesByType('navigation')[0].nextHopProtocol` to populate `QoEResult.protocol`. For HTTPS origins Chromium reports `"h2"`; after receiving an `Alt-Svc` header a subsequent request to the same origin upgrades to `"h3"`.
    - Success requires HTTP 200 and visibility of a target element.

2. **`measure_streaming(stream_url, duration_s)`**
    - Navigates to a page hosting a `<video>` player (HLS/DASH).
    - Polls `<video>` element properties: `buffered`, `currentTime`, `waiting` events.
    - **Startup Time:** time from `play()` to `playing` event.
    - **Rebuffer Ratio:** total time in `waiting` state divided by session duration.

3. **`measure_conferencing(session_url, duration_s)`**
    - Joins a WebRTC session on the testbed's `pion`-based Echo server.
    - Reads `RTCPeerConnection.getStats()` for **latency** (`roundTripTime`), **jitter**, and **packet loss** (`packetsLost`).
    - Passes raw stats to `lib/qoe.py` to compute the MOS score.

### 4.3 MOS Calculation Logic (`lib/qoe.py`)

The Mean Opinion Score is estimated using the **E-model (ITU-T G.107)**, simplified for IP networks.

**Formula:**
`R = Ro - Is - Id - Ie + A`

- `Ro`: Basic signal-to-noise ratio (default 93.2).
- `Id`: Delay impairment (function of latency).
- `Ie`: Equipment impairment (function of packet loss and codec).

**Location:** `boardfarm3/lib/qoe.py` — a pure-Python function that takes `latency`, `jitter`, and `loss` as inputs and returns a float in the range 1.0–5.0.

### 4.4 Testbed CA Trust and Protocol Verification

The `lan-qoe-client` init script calls `update-ca-certificates` at startup (per `testbed-ca-setup.md §7`), which registers the testbed CA with both the system OpenSSL store and the NSS database used by Chromium. This makes the CA trusted by Playwright/Chromium automatically — no launch-flag override is needed.

**Trust store verification** (from inside the container):

```bash
openssl verify \
    -CAfile /usr/local/share/ca-certificates/testbed-ca.crt \
    /usr/local/share/ca-certificates/testbed-ca.crt
# Expected: OK
```

**HTTPS access verification:**

```bash
curl -sv --cacert /usr/local/share/ca-certificates/testbed-ca.crt \
    https://172.16.0.10/
# Expected: TLSv1.3, issuer "SD-WAN Testbed CA", HTTP 200
```

`QoEResult.protocol` reports `"h2"` for HTTPS connections and `"h3"` after Chromium upgrades via the `Alt-Svc` header on a subsequent request to the same origin. The `protocol` field is informational metadata; SLO assertions remain on TTFB and load time.

---

## 5. Developer Debugging Access

Two complementary tools cover different failure modes without compromising testbed isolation.

### 5.1 SOCKS v5 Proxy (Dante) — Network & Service Debugging

The `lan-qoe-client` container runs a **Dante SOCKS v5 proxy** on port 8080, exposed to the host as port 18090 (see `testbed-configuration.md §5.1`). This proxy routes outbound traffic via `eth1` — the same interface Playwright uses — so the developer's browser traverses the identical network path, including any active `tc netem` impairment profiles on WAN1/WAN2.

**What this enables:**

- Browse to `http://172.16.0.10:8080/` (productivity server) and verify page rendering under current impairment conditions.
- Access the HLS streaming endpoint at `http://172.16.0.11:8081/hls/default/index.m3u8` to verify content availability.
- Reach the WebRTC conferencing server at `wss://172.16.0.12:8443/` for manual session testing.
- Experience impairment profiles firsthand — browsing under `satellite` conditions (600 ms latency) helps calibrate QoE SLOs.

**Browser configuration (Firefox recommended):**

```
Settings → Network Settings → Manual Proxy Configuration:
  SOCKS Host: 127.0.0.1
  Port: 18090
  SOCKS v5
  ✓ Proxy DNS when using SOCKS v5
```

**Testbed isolation:** The proxy only exposes the LAN-side network perspective of the `lan-qoe-client` container. Traffic still passes through the DUT and the WAN impairment containers — there is no backdoor into the simulated network.

### 5.2 Playwright Trace Viewer — Automated Session Debugging

For debugging failures in Playwright's automated browser session (element selection failures, unexpected page states, timing issues), Playwright's built-in trace recording produces a complete visual record of every action.

**Enable tracing** by wrapping the measurement call:

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

The trace viewer shows a screenshot timeline, DOM state at each step, all network requests/responses, and browser console output. Store `trace.zip` as a CI artifact on test failure — the trace can be viewed in the Playwright Trace Viewer web UI without a local Playwright installation.

---

## 6. North-Side Service Requirements

The QoE Client measures against north-side target servers that sit on the WAN side of the DUT. These are defined in `application-services.md`.

- **Productivity Target:** A lightweight HTTP/HTTPS server returning a page with a controlled weight (~2 MB of JS/CSS) to simulate a SaaS application load.
- **Streaming Target:** An Nginx server hosting `.m3u8` (HLS) playlists and video segments.
- **Conferencing Target:** A `pion`-based WebRTC Echo server (see `application-services.md §3.3`).

---

## 7. VM Migration Note

To migrate this component from a Docker container to a VM:

1. Provision an Ubuntu VM.
2. `pip install playwright`
3. `playwright install --with-deps`
4. Ensure Xvfb is configured if headless mode is not sufficient (Playwright headless usually works fine).
5. Update Boardfarm inventory to point at the VM's SSH endpoint.
