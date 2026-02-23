# Technical Brief: WAN Edge Appliance Testing Framework

**Date:** February 07, 2026
**Version:** 1.3 (Container-First Plan, Linux Router DUT)
**Status:** Draft

---

## 1. Executive Summary

This document defines the scope and implementation plan for a unified testing framework designed to validate **WAN Edge appliances**. As the enterprise edge evolves from simple routing to intelligent SD-WAN and SASE (Secure Access Service Edge), verification must move beyond basic connectivity to encompass application performance, traffic intelligence, security efficacy, and user experience.

The framework is designed to validate market-leading WAN Edge platforms, including:
*   **Cisco Catalyst 8000 Series (Viptela):** IOS-XE based SD-WAN stack (Heavyweight routing).
*   **Fortinet FortiGate:** ASIC-accelerated path steering and NGFW convergence.
*   **VMware SD-WAN (Velocloud):** Dynamic Multi-Path Optimization (DMPO) and packet-level steering.
*   **Palo Alto ION (Prisma SD-WAN):** App-defined networking (Layer 7 focus).
*   **HPE Aruba EdgeConnect (Silver Peak):** Path conditioning (FEC, Packet Order Correction).

The testing strategy focuses on four core pillars:
1.  **Quality of Experience (Outcome):** Does the user perceive the network as good?
2.  **Quality of Service (Mechanism):** Is traffic prioritized correctly?
3.  **Path Steering (Intelligence):** Is the best link chosen dynamically?
4.  **Security (Protection):** Is the edge secure against threats without compromising performance?

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

#### Impairment Profiles
To verify resilience, the testbed applies deterministic network profiles:

| Profile Name | Latency | Jitter | Packet Loss | Bandwidth | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `pristine` | 5ms | 1ms | 0% | 1 Gbps | Ideal conditions |
| `cable_typical` | 15ms | 5ms | 0.1% | 100 Mbps | Typical subscriber |
| `4g_mobile` | 80ms | 30ms | 1% | 20 Mbps | Mobile/LTE failover |
| `satellite` | 600ms | 50ms | 2% | 10 Mbps | High latency link |
| `congested` | 25ms | 40ms | 3% | Variable | Peak hour congestion |

### 2.2 Quality of Service (QoS) - The Mechanism
QoS verifies the underlying mechanisms the DUT uses to manage contention. It answers: *"Is the device correctly classifying and prioritizing traffic?"*
*   **Traffic Management:** Verification of Shapers, Policers, and Burst handling.
*   **DSCP Tagging:** Ensuring markings are preserved or re-written correctly across the WAN overlay.
*   **Rate Limiting:** Verifying SLA enforcement for specific traffic classes.
*   **Queuing:** Validating Low Latency Queuing (LLQ) effectiveness under link saturation.

### 2.3 Path Steering - The Intelligence
Path Steering verifies the "Brain" of the SD-WAN solution. It answers: *"Is the device making the optimal path decision based on real-time conditions?"*
*   **Link Selection:** Choosing the best path based on Latency, Loss, and Jitter measurements.
*   **Performance-based Routing (PbR):** Dynamic re-routing of flows when SLA thresholds are breached.
*   **Sub-second Failover:** Ensuring session persistence (e.g., Voice calls) during blackout events.
*   **Brownout Resilience:** Utilizing features like FEC (Forward Error Correction) or Packet Duplication to mitigate degraded links.

### 2.4 Security & Firewalling - The Protection
Security verifies the robustness of the WAN Edge as the first line of defense (SASE/NGFW). It answers: *"Is the network secure, and what is the performance cost of that security?"*

*   **Zone-Based Firewalling:** Verification of stateful inspection rules (Allow/Deny) between LAN, WAN, and DMZ zones.
*   **Application Control (L7 Filtering):** Blocking specific applications (e.g., BitTorrent, Social Media) regardless of port.
*   **Performance Impact:** Measuring "Throughput with Services" vs. "Raw Throughput" to quantify the cost of enabling IPS/IDS and SSL Inspection.
*   **Threat Emulation:**
    *   **Inbound:** Port scanning detection, DDoS mitigation (rate limiting SYN floods).
    *   **Outbound:** Blocking Command & Control (C2) callback attempts (DNS sinkholing).
*   **VPN/Overlay Encryption:** Verifying IPsec/WireGuard tunnel establishment and re-keying under load.

---

## 3. Architecture & Tooling

To ensure consistency and portability across different environments (Functional vs. Pre-Production), the framework leverages a decoupled architecture.

### 3.1 Core Components
*   **Raikou:** Used to instantiate networked containers for the functional testbed components (Clients, Servers, ISP Routers). It provides the "Network-in-a-Box" infrastructure with OVS bridges.
*   **Boardfarm:** The orchestration layer. It configures the testbed, manages device connections (DUT, Clients, Traffic Generators), and provides a consistent test interface (API) regardless of the underlying hardware.

### 3.2 Testbed Topology: Dual WAN (Initial) → Triple WAN (Expansion)
The initial testbed uses a **Dual WAN** topology to prove the concept. Expansion to **Triple WAN** follows once validation is complete.

![triple_wan_topology](../Excalidraw/triple_wan_topology.excalidraw.svg)

**Connections:**
1.  **LAN Side:**
    *   **South-Side Clients:** Playwright containers (Browser/App simulation).
    *   **Traffic Generators:** iPerf3/Trex for background load.
    *   **Threat Simulator:** Kali Linux container for generating test attacks (Nmap, Hydra).
2.  **DUT (WAN Edge Appliance):**
    *   **WAN 1 (MPLS/Fiber):** High bandwidth, low latency, high cost.
    *   **WAN 2 (Internet/Cable):** High bandwidth, variable latency, low cost.
    *   **WAN 3 (LTE/5G):** Metered bandwidth, higher latency, backup path. *(Added in expansion phase.)*
3.  **WAN Emulator (Traffic Control):**
    *   Injects impairments (Delay, Loss, Jitter, Bandwidth limits) independently on each WAN link.
4.  **Cloud Side:**
    *   **North-Side Services:** Productivity, Streaming, and Conferencing servers hosted in the testbed (simulating Cloud/Internet).
    *   **Malicious Hosts:** Simulated Command & Control (C2) servers and malware distribution points for security validation.

### 3.3 Implementation Types
*   **Functional Testbed:** All components are containerized implementations, except for the DUT. Traffic control is done via Linux `tc` within Raikou containers.
*   **Pre-Production Testbed:** Physical hardware DUTs. Traffic control is handled by dedicated hardware (Spirent, Keysight) or high-performance WAN emulators. Boardfarm abstracts these differences using the `TrafficController` template.

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

| Component | Purpose | Notes |
| :--- | :--- | :--- |
| **Linux Router (DUT)** | FRR-based router with two WAN interfaces | Path steering, failover |
| **WAN 1 (TrafficController)** | Impairment container for first WAN link | `tc`/netem |
| **WAN 2 (TrafficController)** | Impairment container for second WAN link | `tc`/netem |
| **WAN-side Services** | Productivity + Streaming servers | Mock SaaS, Nginx HLS/DASH |
| **LAN-side Clients** | Productivity + Streaming clients | Playwright or similar |

**Topology:** `[LAN Client] → [DUT] → [WAN1 / WAN2] → [Services]`

### 4.3 DUT: Linux Router with FRR (Dual WAN)

Before validating commercial SD-WAN appliances, the testbed itself must be validated. We use a **Linux Router with FRR** as the software DUT placeholder.

**Why Linux Router + FRR?**
*   **Raikou Alignment:** Extends the existing Raikou router component (already uses FRR).
*   **No KVM Required:** Runs as a standard Linux container; works in CI and cloud environments.
*   **Path Steering:** FRR supports policy routing (PBR), nexthop groups, and next-hop tracking for failover.
*   **Automation:** CLI (vtysh) and config files; easy to drive from Boardfarm.

**Initial scope (FRR only):**
*   Multi-WAN with two interfaces (WAN1, WAN2).
*   Policy routing and nexthop groups for path selection and failover.
*   Gateway monitoring via resilient nexthop groups or a lightweight script.

**Planned expansion (later phases):**
*   **StrongSwan:** Add IPsec VPN overlay for the "VPN/Overlay Encryption" pillar.
*   **tc (Traffic Control):** Add traffic shaping (htb, fq_codel) for QoS validation.
*   **iptables/nftables:** Add zone-based firewall rules for Security pillar validation.

#### Proxy Mapping: Linux Router to Commercial DUTs

| Feature Category | Commercial DUT (e.g., Meraki) | Linux Router Proxy Equivalent | Validation Goal |
| :--- | :--- | :--- | :--- |
| **SD-WAN Policies** | Traffic Steering / Policy Routing | FRR PBR + Nexthop Groups | Test Boardfarm's ability to trigger path shifts. |
| **QoS / Shaper** | App-aware Shaping | `tc` (planned) | Verify that QoE scripts detect throttled traffic. |
| **Security / FW** | Zone-based FW / IPS | `iptables` (planned) | Verify Allow/Deny logic and threat blocking. |
| **VPN/Overlay** | IPsec / WireGuard | StrongSwan (planned) | Verify tunnel establishment and re-keying. |
| **Management** | Cloud Dashboard / API | SSH + vtysh / Config Files | Test "Telemetry" collection scripts. |

#### Pre-Hardware Validation Scenarios

1.  **Orchestration Handshake**
    *   **Goal:** Ensure Boardfarm can talk to the DUT.
    *   **Method:** Create a Boardfarm `linux_router_dut` driver (or extend existing router device).
    *   **Success:** Boardfarm successfully fetches interface status and routing table.

2.  **Impairment Trigger Loop**
    *   **Goal:** Verify that applying a "Satellite" profile via the TrafficController triggers failover.
    *   **Method:** Configure FRR gateway monitoring. Inject 600ms latency via `tc` on WAN1.
    *   **Success:** DUT fails over to WAN2; LAN Client records transient QoE dip during switch.

3.  **Path Steering Verification**
    *   **Goal:** Verify that path selection responds to impairment changes.
    *   **Method:** Apply `cable_typical` to WAN1, `satellite` to WAN2; verify traffic prefers WAN1.
    *   **Success:** Traffic flows via preferred path; Boardfarm can assert path choice.

### 4.4 Additional Component Development

Beyond the PoC set, the following components are developed or integrated:

1.  **Traffic Controller (Impairment Layer):**
    *   Develop `LinuxTrafficControl` library for functional tests (wrapping `tc`/`netem`).
    *   Implement the `TrafficController` Boardfarm template.
    *   Develop `SpirentImpairment` driver for pre-production labs.

2.  **Application Services (North-Side):**
    *   **Productivity:** Mock SaaS server (HTTP/2, HTTP/3).
    *   **Streaming:** Nginx VOD module with multi-bitrate HLS/DASH content.
    *   **Conferencing:** Self-hosted Jitsi Meet + Coturn (STUN/TURN) setup.
    *   **Security:** "Bad Actor" container serving EICAR test files and listening for C2 callbacks.

3.  **Client Measurement Tools (South-Side):**
    *   Enhance **Playwright** scripts to capture navigation timing, media stats, and WebRTC `getStats()`.
    *   Implement **MOS calculation** logic based on captured metrics (R-Factor calculation).
    *   Integrate **Nmap/Kali** scripts for basic penetration testing assertions.

---

## 5. Development Phases

1.  **Phase 1: Container Development (Foundation)**
    *   Develop Docker images for each component: Linux Router (DUT), WAN1/WAN2 (TrafficController), Productivity, Streaming, LAN Client.
    *   Extend Linux Router DUT with FRR for two WAN interfaces, policy routing, and failover.
    *   Implement the `TrafficController` Boardfarm template and `LinuxTrafficControl` library.
    *   Develop Playwright measurement scripts for QoE as part of the LAN Client (Productivity, Streaming).
    *   Validate each container independently.

2.  **Phase 2: Raikou Integration & Dual WAN Topology**
    *   Create Docker Compose for Raikou with Dual WAN topology.
    *   Configure OVS bridges and network links.
    *   Deploy full testbed (all containers instantiated via Raikou).
    *   Align Boardfarm inventory and env config to the running topology.

3.  **Phase 3: Validation**
    *   Run initial validation scenarios (Orchestration Handshake, Impairment Trigger Loop, Path Steering).

4.  **Phase 4: Linux Router Expansion (Optional)**
    *   Add **StrongSwan** to DUT for VPN/overlay encryption validation.
    *   Add **tc** for QoS shaping validation.
    *   Add **iptables** for firewall/security validation.
    *   Expand to **Triple WAN** topology.
    *   *(If pursued, done before moving to commercial hardware.)*

5.  **Phase 5: Commercial DUT Integration**
    *   Swap Linux Router for Cisco/Fortinet/VMware virtual or physical appliances.
    *   Develop specific Boardfarm drivers for the commercial DUTs.
    *   Execute "Scenario A: Brownout Resilience" and other use cases.
