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
*   Set up a non-root user (e.g., `boardfarm`) for running the browser (browsers often dislike running as root).

### 3.2 Driver Implementation (`PlaywrightQoEClient`)

This class implements the `QoEClient` template defined in the Technical Brief.

**Location:** `boardfarm3/devices/playwright_qoe_client.py`

#### Key Methods & Logic

1.  **`measure_productivity(url, scenario="page_load")`**
    *   **Action:** Launch browser, navigate to `url`, wait for `networkidle`.
    *   **Metrics:**
        *   Extract `window.performance.timing` API data.
        *   **TTFB:** `responseStart - requestStart`
        *   **Load Time:** `loadEventEnd - navigationStart`
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
    *   Build Docker image with Playwright + SSH.
    *   Verify manual script execution via SSH.
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

---

## 6. VM Migration Note

To migrate this component to a VM:
1.  Provision a Ubuntu VM.
2.  `pip install playwright`
3.  `playwright install --with-deps`
4.  Ensure X11 forwarding or Xvfb is configured if running headless is not sufficient (Playwright headless usually works fine).
5.  Update Boardfarm inventory.
