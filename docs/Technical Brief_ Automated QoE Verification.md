# Technical Brief: Automated End-User Quality of Experience (QoE) Verification Framework

**Date:** February 06, 2026  
**Version:** 2.6  
**Status:** Draft

### Related Documents
- [Testbed Network Topology](./Testbed%20Network%20Topology.md) - Base Raikou + Boardfarm topology reference

---

## 1. Executive Summary

This document defines a standardized framework for verifying end-user Quality of Experience (QoE) across network infrastructure devices. By combining **Boardfarm testbed orchestration** with **Raikou container networking**, we create a deterministic environment where network conditions can be precisely controlled and user experience can be measured objectively.

### Key Value Propositions

1. **Deterministic Reproduction**: Every network issue can be reproduced exactly by replaying recorded impairment profiles
2. **DUT-Agnostic**: Framework supports any device providing network access (cable modems, SD-WAN appliances, routers, firewalls)
3. **User-Centric Metrics**: Focus on actual user experience (page load time, video quality, call clarity) rather than just network counters
4. **Automated Verification**: Programmatic assertion of QoE thresholds against Service Level Objectives (SLOs)

### Scope

The framework validates QoE for three primary service categories:
- **Productivity Applications**: Office 365, Google Workspace, SaaS platforms
- **Video Streaming**: Netflix, YouTube, Disney+, live streaming
- **Real-Time Communication**: Video conferencing (Teams, Zoom), VoIP

### Scalable Architecture: Simple to Complex

The framework is designed to support both simple single-path scenarios and complex multi-path SD-WAN configurations:

| Scenario | DUT Type | WAN Topology | Impairment Points |
|----------|----------|--------------|-------------------|
| **Simple** | Basic Router, Cable Modem | Single WAN path | One impairment point on `rtr-wan` bridge |
| **Complex** | SD-WAN / ApplicationGateway | Multiple WAN paths (WAN1, WAN2, LTE) | Independent impairment per path via dedicated bridges |

This approach ensures the same testing methodology scales from verifying a simple home router to validating complex SD-WAN failover policies on enterprise-grade ApplicationGateway devices.

---

## 2. Testbed Architecture

This framework extends the existing Raikou + Boardfarm testbed topology (see [Testbed Network Topology](./Testbed%20Network%20Topology.md)) with QoE measurement capabilities.

### 2.1 Topology Overview

The testbed creates a controlled environment with the Device Under Test (DUT) positioned between simulated ISP infrastructure (North-side) and simulated end-users (South-side). The **Network Factory** component operates **north of the Router** (on the `rtr-wan` bridge) to simulate WAN/backbone conditions such as internet latency, backbone congestion, and CDN distance.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         QoE Verification Testbed                                 │
│                    (Extension of Raikou + Boardfarm Topology)                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │              NORTH-SIDE: Infrastructure Services (Simulated Internet)      │  │
│  │                                                                            │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐   │  │
│  │  │ WAN         │  │ DHCP        │  │ ACS         │  │ SIP Center      │   │  │
│  │  │ Container   │  │ Container   │  │ Container   │  │                 │   │  │
│  │  │ 172.25.1.2  │  │ 172.25.1.20 │  │ 172.25.1.40 │  │ 172.25.1.5      │   │  │
│  │  │ DNS/HTTP/   │  │ DHCP/Prov.  │  │ TR-069      │  │ Voice Services  │   │  │
│  │  │ CDN/SaaS    │  │             │  │             │  │                 │   │  │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └────────┬────────┘   │  │
│  │         └────────────────┴────────────────┴──────────────────┘            │  │
│  │                                   │                                        │  │
│  │                    ┌──────────────▼──────────────┐                         │  │
│  │                    │      NETWORK FACTORY        │                         │  │
│  │                    │   (on rtr-wan OVS bridge)   │                         │  │
│  │                    │   - Latency / Jitter (tc)   │  ← Simulates internet   │  │
│  │                    │   - Packet Loss (netem)     │    backbone conditions  │  │
│  │                    │   - Bandwidth Limits        │                         │  │
│  │                    │   - Blackout / Brownout     │                         │  │
│  │                    └──────────────┬──────────────┘                         │  │
│  │                                   │                                        │  │
│  │                      rtr-wan bridge (172.25.1.0/24)                        │  │
│  │                                   │                                        │  │
│  │                    ┌──────────────▼──────────────┐                         │  │
│  │                    │     Router Container        │                         │  │
│  │                    │     (ISP Edge Gateway)      │                         │  │
│  │                    │     eth1: 172.25.1.1        │                         │  │
│  │                    │     NAT + FRR Routing       │                         │  │
│  │                    │     cpe: 10.1.1.1           │                         │  │
│  │                    └──────────────┬──────────────┘                         │  │
│  └───────────────────────────────────┼───────────────────────────────────────┘  │
│                                      │                                          │
│                           cpe-rtr bridge (10.1.1.0/24)                          │
│                                      │                                          │
│                           ┌──────────▼──────────┐                               │
│                           │  DEVICE UNDER TEST  │                               │
│                           │  (DUT / CPE)        │                               │
│                           │  eth1: 10.1.1.x     │                               │
│                           │  - Cable Modem      │                               │
│                           │  - SD-WAN Appliance │                               │
│                           │  - PrplOS Gateway   │                               │
│                           │  - SD-WAN Device    │                               │
│                           │  eth0: br-lan       │                               │
│                           └──────────┬──────────┘                               │
│                                      │                                          │
│  ┌───────────────────────────────────┼───────────────────────────────────────┐  │
│  │              SOUTH-SIDE: Client Devices (LAN Simulation)                   │  │
│  │                         lan-cpe bridge (br-lan)                            │  │
│  │                                   │                                        │  │
│  │    ┌──────────────────────────────┼──────────────────────────────┐         │  │
│  │    │                              │                              │         │  │
│  │  ┌─▼───────────┐  ┌───────────────▼───────────┐  ┌───────────────▼──────┐  │  │
│  │  │ LAN         │  │ Browser User              │  │ LAN Phone            │  │  │
│  │  │ Container   │  │ (Playwright)              │  │ (SIP Client)         │  │  │
│  │  │ DHCP Client │  │ - Productivity            │  │ Number: 1000         │  │  │
│  │  │ HTTP Proxy  │  │ - Video Streaming         │  │                      │  │  │
│  │  │             │  │ - Conferencing            │  │                      │  │  │
│  │  └─────────────┘  └───────────────────────────┘  └──────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 North-Side: Infrastructure Services (ISP + Simulated Internet)

The north-side consists of two logical layers on the `rtr-wan` bridge (172.25.1.0/24):

#### ISP Edge (Router Container)

| Component | IP Address | Role |
|-----------|------------|------|
| **Router** | 172.25.1.1 (wan), 10.1.1.1 (cpe) | ISP edge gateway - NAT, FRR routing |

The Router is the boundary between "customer network" and "internet". It performs NAT and routing, representing the ISP's customer-facing equipment.

#### Simulated Internet Services (North of Router)

| Component | IP Address | Services | QoE Role |
|-----------|------------|----------|----------|
| **WAN Container** | 172.25.1.2 | DNS, HTTP, TFTP, FTP | CDN, SaaS endpoints, general internet |
| **DHCP Container** | 172.25.1.20 | DHCP, provisioning | ISP provisioning (DOCSIS, TR-069 bootstrap) |
| **ACS Container** | 172.25.1.40 | TR-069 | Device management verification |
| **SIP Center** | 172.25.1.5 | SIP registrar | VoIP/conferencing backend |

These containers represent internet services that the end-user accesses through the ISP. The **Network Factory** applies impairments to traffic between the Router and these services.

#### Self-Hosted QoE Service Infrastructure

To ensure **deterministic and reproducible** QoE measurements, all backend services must be self-hosted within the testbed. Using public internet services (actual Netflix, YouTube, Teams) would introduce uncontrolled variables that undermine reproducibility.

**Design Principle:** Each QoE domain (productivity, streaming, conferencing) requires dedicated service simulators that provide realistic behavior while remaining fully controlled.

##### Productivity Services (Mock SaaS)

**Purpose:** Measure page load times, TTFB, file upload/download performance

| Service | Implementation | Metrics Enabled |
|---------|----------------|-----------------|
| **Web Server** | nginx with static HTML/CSS/JS bundles | Page Load Time, DOM Content Loaded |
| **Mock SaaS API** | Flask/FastAPI with realistic response sizes | TTFB, Transaction Time |
| **File Transfer** | nginx with upload endpoint (configurable delays) | Upload/Download throughput |
| **TLS Termination** | Self-signed certificates | TLS handshake timing |

**WAN Container Enhancement:**
```
WAN Container (172.25.1.2):
├── nginx serving "Office 365-like" static pages
│   ├── /login - Mock login page with JS bundle
│   ├── /dashboard - Complex page with multiple resources
│   └── /upload - File upload endpoint
├── Mock API endpoints returning realistic JSON payloads
└── Configurable response delays for SLA testing
```

##### Streaming Services (HLS/DASH Video)

**Purpose:** Measure adaptive bitrate behavior, rebuffering, startup time, resolution changes

| Service | Implementation | Metrics Enabled |
|---------|----------------|-----------------|
| **HLS/DASH Server** | nginx-vod-module or pre-packaged segments | Startup Time, Rebuffer Ratio |
| **Multi-Bitrate Content** | Pre-encoded test videos (Big Buck Bunny) | Resolution Changes, ABR behavior |
| **CDN Simulator** | nginx with configurable chunk delays | CDN latency simulation |

**Streaming Container (NEW - 172.25.1.10):**
```
Streaming Container:
├── nginx-vod-module (on-the-fly HLS/DASH packaging)
│   OR nginx serving pre-packaged segments
├── Test video content at multiple bitrates:
│   ├── 360p  @ 0.5 Mbps  (low quality fallback)
│   ├── 720p  @ 2.5 Mbps  (standard definition)
│   ├── 1080p @ 5.0 Mbps  (high definition)
│   └── 4K    @ 15 Mbps   (ultra high definition)
├── HLS manifests (.m3u8) with proper segment durations
└── DASH manifests (.mpd) for cross-platform testing
```

**Content Preparation (using FFmpeg):**
```bash
# Encode test video at multiple bitrates for HLS
ffmpeg -i source.mp4 \
  -c:v libx264 -b:v 500k  -s 640x360  -hls_time 4 -hls_list_size 0 360p.m3u8 \
  -c:v libx264 -b:v 2500k -s 1280x720 -hls_time 4 -hls_list_size 0 720p.m3u8 \
  -c:v libx264 -b:v 5000k -s 1920x1080 -hls_time 4 -hls_list_size 0 1080p.m3u8

# Generate master playlist for adaptive streaming
cat > master.m3u8 << EOF
#EXTM3U
#EXT-X-STREAM-INF:BANDWIDTH=500000,RESOLUTION=640x360
360p.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=2500000,RESOLUTION=1280x720
720p.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=5000000,RESOLUTION=1920x1080
1080p.m3u8
EOF
```

##### Conferencing Services (WebRTC/VoIP)

**Purpose:** Measure RTT, jitter, packet loss, MOS score, video resolution

| Service | Implementation | Metrics Enabled |
|---------|----------------|-----------------|
| **WebRTC Server** | Jitsi Meet or Mediasoup | RTT, Jitter, Packet Loss via getStats() |
| **STUN/TURN** | coturn | NAT traversal, relay metrics |
| **Media Bot** | Automated call participant | Consistent call partner for testing |
| **SIP Server** | Kamailio (existing SIP Center) | Traditional VoIP metrics |

**Conferencing Container (NEW - 172.25.1.15):**
```
Conferencing Container:
├── Jitsi Meet (self-hosted)
│   ├── Jicofo (conference focus)
│   ├── Jitsi Videobridge (media routing)
│   └── Prosody (XMPP signaling)
├── coturn (STUN/TURN server)
│   ├── STUN on port 3478
│   └── TURN on port 3478 (TCP/UDP)
├── Media Bot (automated call participant)
│   ├── Joins calls automatically
│   ├── Sends test audio/video patterns
│   └── Provides consistent call partner
└── Integration with existing SIP Center for VoIP
```

**Why Jitsi Meet?**
- Fully open source and self-hostable
- WebRTC-based (matches Teams/Zoom architecture)
- Exposes all WebRTC `getStats()` metrics
- Can run headless for automated testing

##### DNS Configuration for Service Discovery

The WAN container's DNS must resolve test domains to local service IPs. This allows the Playwright browser to navigate to familiar URLs while hitting local services:

```bind
; /etc/bind/zones/test.local.zone
; QoE Test Domains - resolve to self-hosted services

; Productivity (Mock SaaS)
office365.test.local.     IN A  172.25.1.2
sharepoint.test.local.    IN A  172.25.1.2
docs.test.local.          IN A  172.25.1.2
salesforce.test.local.    IN A  172.25.1.2

; Video Streaming
youtube.test.local.       IN A  172.25.1.10
netflix.test.local.       IN A  172.25.1.10
twitch.test.local.        IN A  172.25.1.10
vimeo.test.local.         IN A  172.25.1.10

; Conferencing
teams.test.local.         IN A  172.25.1.15
zoom.test.local.          IN A  172.25.1.15
meet.test.local.          IN A  172.25.1.15

; STUN/TURN
stun.test.local.          IN A  172.25.1.15
turn.test.local.          IN A  172.25.1.15
```

##### Extended WAN Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    NORTH-SIDE: Self-Hosted QoE Services                      │
│                         (rtr-wan bridge: 172.25.1.0/24)                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌───────────────────┐  ┌───────────────────┐  ┌─────────────────────────┐  │
│  │ WAN Container     │  │ Streaming         │  │ Conferencing            │  │
│  │ 172.25.1.2        │  │ Container         │  │ Container               │  │
│  │                   │  │ 172.25.1.10       │  │ 172.25.1.15             │  │
│  │ • DNS (bind9)     │  │                   │  │                         │  │
│  │ • nginx (web)     │  │ • nginx-vod       │  │ • Jitsi Meet            │  │
│  │ • Mock SaaS API   │  │ • HLS/DASH        │  │ • coturn (STUN/TURN)    │  │
│  │ • File transfer   │  │ • Multi-bitrate   │  │ • WebRTC signaling      │  │
│  │                   │  │   test videos     │  │ • Media bot             │  │
│  └───────────────────┘  └───────────────────┘  └─────────────────────────┘  │
│                                                                              │
│  ┌───────────────────┐  ┌───────────────────┐  ┌─────────────────────────┐  │
│  │ DHCP Container    │  │ ACS Container     │  │ SIP Center              │  │
│  │ 172.25.1.20       │  │ 172.25.1.40       │  │ 172.25.1.5              │  │
│  │ (existing)        │  │ (existing)        │  │ (existing - VoIP)       │  │
│  └───────────────────┘  └───────────────────┘  └─────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

##### Implementation Priority

| Priority | Container | Complexity | Value | Dependencies |
|----------|-----------|------------|-------|--------------|
| **1** | Enhanced WAN (Mock SaaS) | Low | Medium | Extends existing container |
| **2** | Streaming (HLS/DASH) | Medium | High | New container, video encoding |
| **3** | Conferencing (Jitsi) | High | High | New container, complex setup |

**Traffic Flow:**
1. LAN client sends request through DUT
2. DUT forwards to Router (`10.1.1.1`) on `cpe-rtr` bridge
3. Router applies NAT (source → `172.25.1.1`) and forwards to `rtr-wan` bridge
4. **Network Factory applies impairments** (latency, loss, bandwidth)
5. WAN services receive impaired request and respond
6. Response traverses Network Factory (impairments applied)
7. Router de-NATs and forwards to DUT → LAN client

### 2.3 Network Factory: Architecture Overview

The **Network Factory** capability is implemented through the collaboration of two components:

1. **Raikou (Infrastructure Layer)**: Creates the OVS bridges, veth pairs, and provides the low-level tc/netem execution environment
2. **Boardfarm ISPGateway.impairment (Device Layer)**: Exposes impairment control as a property of the Router device, following existing Boardfarm patterns

This separation of concerns ensures:
- Raikou handles network topology creation and container orchestration
- Boardfarm standardizes the interface for test cases to control impairments
- Test cases use `router.impairment.set_profile("degraded")` without knowing tc/netem details

#### Technical Implementation: tc/netem on Veth Interfaces

**Important:** Linux `tc`/`netem` rules cannot be applied directly to OVS bridges. OVS bridges are software switches that don't support the standard Linux queuing discipline interface.

Instead, impairments are applied to the **veth interfaces** that connect containers to OVS bridges:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                     How Raikou Connects Containers to Bridges                 │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│   ┌─────────────────┐              ┌─────────────────┐                       │
│   │  Router         │              │  WAN Services   │                       │
│   │  Container      │              │  Container      │                       │
│   │                 │              │                 │                       │
│   │   eth1          │              │   eth1          │                       │
│   └────────┬────────┘              └────────┬────────┘                       │
│            │                                │                                │
│   ┌────────▼────────┐              ┌────────▼────────┐                       │
│   │  veth_c         │              │  veth_c         │  ← Container side     │
│   │  (inside netns) │              │  (inside netns) │                       │
│   └────────┬────────┘              └────────┬────────┘                       │
│            │ veth pair                      │ veth pair                      │
│   ┌────────▼────────┐              ┌────────▼────────┐                       │
│   │  veth_l         │              │  veth_l         │  ← Host side          │
│   │  (host netns)   │              │  (host netns)   │    tc/netem HERE      │
│   └────────┬────────┘              └────────┬────────┘                       │
│            │                                │                                │
│            └────────────────┬───────────────┘                                │
│                             │                                                │
│                    ┌────────▼────────┐                                       │
│                    │  rtr-wan        │                                       │
│                    │  OVS Bridge     │                                       │
│                    └─────────────────┘                                       │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Raikou's veth creation** (from `util/ovs-docker`):
```bash
# Create a veth pair
ip link add "${PORTNAME}_l" type veth peer name "${PORTNAME}_c"

# Add host-side veth to OVS bridge  
ovs-vsctl add-port "$BRIDGE" "${PORTNAME}_l"

# Move container-side veth into container namespace
ip link set "${PORTNAME}_c" netns "$PID"
ip netns exec "$PID" ip link set dev "${PORTNAME}_c" name "eth1"
```

**Impairment application**: tc/netem rules are applied to the **host-side veth** (`${PORTNAME}_l`):
```bash
# Find Router's eth1 veth port on rtr-wan bridge
PORT=$(ovs-vsctl --data=bare --no-heading --columns=name find interface \
    external_ids:container_id="router" \
    external_ids:container_iface="eth1")

# Apply impairment to Router's uplink
tc qdisc add dev ${PORT} root netem delay 100ms 20ms loss 2%
```

#### Why Raikou as Network Factory?

| Benefit | Description |
|---------|-------------|
| **Unified Management** | Single API for topology and impairment control |
| **Existing Infrastructure** | Raikou already tracks all veth interfaces and their metadata |
| **Multi-Path Ready** | Create multiple bridges with independent impairments |
| **Consistent Cleanup** | Impairments automatically removed when containers are destroyed |

#### Placement: North of Router

Traffic flow with impairments:
```
Internet Services (WAN/CDN/SaaS) ←──[veth with tc/netem]──→ OVS Bridge ←──→ Router (eth1)
```

**Why this placement (north of Router)?**
- **Simulates real-world conditions**: Latency to distant servers, backbone congestion, and CDN issues occur in the internet backbone, not the last mile
- **Router is the ISP edge**: The Router container represents the customer-facing ISP equipment; impairments should affect what the ISP "sees" from the internet
- **Comprehensive testing**: All traffic to/from WAN services (DNS, HTTP, streaming, VoIP) passes through the impairment zone
- **Realistic scenarios**: When testing "satellite latency" or "congested backbone", the impairment should be between ISP and internet, not between customer and ISP

**Alternative: Last-Mile Impairment**

For scenarios requiring last-mile simulation (e.g., DSL line quality, cable plant issues), impairments can alternatively be applied to veth interfaces on the `cpe-rtr` bridge between the DUT and Router. This is a secondary use case.

### 2.4 Multi-Path Topology (SD-WAN / ApplicationGateway)

For advanced DUTs with multiple WAN interfaces (ApplicationGateway devices such as SD-WAN appliances), the topology extends to support **independent impairment per path**:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                Multi-Path QoE Testbed (SD-WAN / ApplicationGateway)              │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                    NORTH-SIDE: Simulated Internet Services                 │  │
│  │                                                                            │  │
│  │    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                   │  │
│  │    │ WAN/CDN     │    │ DNS/DHCP    │    │ SaaS/Cloud  │                   │  │
│  │    │ Services    │    │ Services    │    │ Services    │                   │  │
│  │    └──────┬──────┘    └──────┬──────┘    └──────┬──────┘                   │  │
│  │           └─────────────────┬┴───────────────────┘                         │  │
│  │                             │                                              │  │
│  │  ┌──────────────────────────┼──────────────────────────┐                   │  │
│  │  │                          │                          │                   │  │
│  │  │                          │                          │                   │  │
│  │  ▼                          ▼                          ▼                   │  │
│  │ ┌────────────────┐  ┌────────────────┐  ┌────────────────┐                 │  │
│  │ │ wan1-bridge    │  │ wan2-bridge    │  │ lte-bridge     │                 │  │
│  │ │ ┌────────────┐ │  │ ┌────────────┐ │  │ ┌────────────┐ │                 │  │
│  │ │ │ tc/netem   │ │  │ │ tc/netem   │ │  │ │ tc/netem   │ │                 │  │
│  │ │ │ "fiber"    │ │  │ │ "cable"    │ │  │ │ "4g_mobile"│ │                 │  │
│  │ │ │ 10ms/0%    │ │  │ │ 25ms/0.5%  │ │  │ │ 80ms/1%   │ │                 │  │
│  │ │ └────────────┘ │  │ └────────────┘ │  │ └────────────┘ │                 │  │
│  │ └───────┬────────┘  └───────┬────────┘  └───────┬────────┘                 │  │
│  │         │                   │                   │                          │  │
│  └─────────┼───────────────────┼───────────────────┼──────────────────────────┘  │
│            │                   │                   │                             │
│            │                   │                   │                             │
│            ▼                   ▼                   ▼                             │
│       ┌─────────────────────────────────────────────────────┐                    │
│       │              MERAKI MX / SD-WAN DEVICE              │                    │
│       │                    (DUT)                            │                    │
│       │                                                     │                    │
│       │    WAN1 (eth1)    WAN2 (eth2)    LTE (usb0)        │                    │
│       │    Primary        Secondary      Failover          │                    │
│       │                                                     │                    │
│       │    ┌─────────────────────────────────────────┐      │                    │
│       │    │         SD-WAN Policy Engine            │      │                    │
│       │    │   • Path selection based on SLA         │      │                    │
│       │    │   • Application-aware routing           │      │                    │
│       │    │   • Automatic failover                  │      │                    │
│       │    └─────────────────────────────────────────┘      │                    │
│       │                                                     │                    │
│       │                      LAN                            │                    │
│       └───────────────────────┬─────────────────────────────┘                    │
│                               │                                                  │
│  ┌────────────────────────────┼────────────────────────────────────────────────┐ │
│  │              SOUTH-SIDE: Client Devices (LAN Simulation)                    │ │
│  │                        lan-cpe bridge                                       │ │
│  │    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                    │ │
│  │    │ Browser     │    │ Browser     │    │ SIP Phone   │                    │ │
│  │    │ User 1      │    │ User 2      │    │ (VoIP)      │                    │ │
│  │    └─────────────┘    └─────────────┘    └─────────────┘                    │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Multi-Path Test Scenarios:**

| Scenario | Path Configuration | Expected Behavior |
|----------|--------------------|-------------------|
| **WAN1 Degradation** | WAN1: `congested_peak`, WAN2: `pristine` | Traffic shifts to WAN2 |
| **WAN1 Blackout** | WAN1: link down, WAN2: `pristine` | Immediate failover to WAN2 |
| **All Paths Degraded** | WAN1: `degraded`, WAN2: `degraded`, LTE: `4g_mobile` | Best-effort routing, voice prioritized to LTE |
| **Voice Priority** | All paths: `congested_peak` | VoIP stays on lowest-latency path |

This multi-path architecture enables verification of SD-WAN policy decisions under controlled, reproducible conditions.

### 2.5 South-Side: Client Devices (LAN Simulation)

Simulated users connect to the DUT LAN via the `lan-cpe` OVS bridge, appearing as distinct devices:

| Component | Connection | Purpose |
|-----------|------------|---------|
| **LAN Container** | eth1 → lan-cpe bridge | Existing test client (DHCP, HTTP proxy) |
| **Browser User** | eth1 → lan-cpe bridge | Playwright-based QoE measurement |
| **LAN Phone** | eth1 → lan-cpe bridge | SIP client (number 1000) |

**Networking Strategy:**

For the DUT to apply per-client policies (e.g., QoS, firewall rules), each simulated user must appear as a distinct physical device on the LAN:

| Requirement | Solution |
|-------------|----------|
| Unique MAC address per user | Raikou assigns dedicated MAC via OVS |
| Unique IP from LAN subnet | DHCP from DUT or static assignment |
| Distinct client identity | DUT sees separate devices, not NAT'd host |

### 2.6 Device Under Test (DUT) Abstraction

The framework treats the DUT as a replaceable component. The default is the PrplOS CPE, but it can be substituted with any device providing network access:

| Capability | Description | Examples |
|------------|-------------|----------|
| **Routing** | Forward traffic between LAN and WAN | All devices |
| **NAT** | Translate private IPs to public | Most devices |
| **QoS** | Prioritize traffic classes | ApplicationGateway, enterprise routers |
| **Firewall** | Filter traffic by rules/policies | All security appliances |
| **DPI** | Classify traffic by application | ApplicationGateway, next-gen firewalls |
| **SD-WAN** | Multi-path routing, failover | ApplicationGateway (Meraki, Viptela, Fortinet, etc.) |

**DUT Interface Requirements:**
- **eth0 (LAN)**: Connected to `lan-cpe` bridge
- **eth1 (WAN)**: Connected to `cpe-rtr` bridge, obtains IP via DHCP from Router

Device-specific verification is handled through Boardfarm's device templates (see Section 2.7).

### 2.7 Boardfarm Device Architecture

The QoE framework introduces new device types in Boardfarm to properly model the different classes of network equipment in the testbed. This follows Boardfarm's established pattern of **templates** (abstract interfaces) and **device implementations** (concrete classes).

#### 2.7.1 Device Type Separation: CPE vs ApplicationGateway

A critical architectural decision is the recognition that **CPE** (Customer Premises Equipment) and **ApplicationGateway** (SD-WAN/L7 appliances) are fundamentally different device types:

| Aspect | CPE (Cable Modem/Router) | ApplicationGateway (SD-WAN, NGFW) |
|--------|--------------------------|-----------------------------------|
| **OSI Layer** | L2/L3 (Data Link/Network) | L3-L7 (Network through Application) |
| **Primary Function** | Basic connectivity, NAT, DHCP | Application-aware routing, DPI, SD-WAN |
| **Management Protocol** | TR-069/CWMP, SNMP, CLI | Cloud Dashboard API, REST, vendor-specific |
| **Traffic Handling** | IP packets, port-based rules | Deep packet inspection, app classification |
| **QoS Capabilities** | Basic queue management | Application-aware traffic shaping |
| **Network Position** | Edge of ISP network (bridge mode or NAT) | Customer's intelligent gateway |
| **Examples** | Cable modems, residential gateways | Meraki MX, Cisco Viptela, Fortinet, Palo Alto |

**Rationale:** Extending the CPE template to accommodate ApplicationGateway functionality would be architecturally incorrect. An ApplicationGateway device sits *behind* or *instead of* a basic CPE, providing intelligent application services. The device capabilities are fundamentally different.

#### 2.7.2 New Template: ApplicationGateway

Following Boardfarm's sub-component pattern (like `cpe.hw`, `cpe.sw`, `acs.nbi`, `acs.gui`), the ApplicationGateway template exposes functional sub-components:

```python
# boardfarm3/templates/app_gateway.py

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from boardfarm3.templates.app_gateway.app_gateway_mgmt import AppGatewayMgmt
    from boardfarm3.templates.app_gateway.app_gateway_wan import AppGatewayWan
    from boardfarm3.templates.app_gateway.app_gateway_traffic import AppGatewayTraffic
    from boardfarm3.templates.app_gateway.app_gateway_policy import AppGatewayPolicy


class ApplicationGateway(ABC):
    """Template for L7-capable network appliances (SD-WAN, NGFW, etc.)
    
    Represents devices that provide:
    - Application identification and classification
    - Traffic shaping based on application awareness
    - Multi-path WAN with intelligent path selection
    - Security services (IPS, content filtering, etc.)
    
    Examples: Meraki MX, Cisco Viptela, Fortinet SD-WAN, Palo Alto Prisma
    """
    
    @property
    @abstractmethod
    def config(self) -> dict:
        """Device configuration from inventory."""
        raise NotImplementedError
    
    @property
    @abstractmethod
    def mgmt(self) -> AppGatewayMgmt:
        """Management interface (API, console if available)."""
        raise NotImplementedError
    
    @property
    @abstractmethod
    def wan(self) -> AppGatewayWan:
        """WAN interfaces and SD-WAN path management."""
        raise NotImplementedError
    
    @property
    @abstractmethod
    def traffic(self) -> AppGatewayTraffic:
        """Traffic analytics and application classification."""
        raise NotImplementedError
    
    @property
    @abstractmethod
    def policy(self) -> AppGatewayPolicy:
        """QoS, security, and traffic shaping policies."""
        raise NotImplementedError
```

**Sub-Component Templates:**

| Sub-Component | Purpose | Key Methods |
|---------------|---------|-------------|
| `mgmt` | Management interface (API connectivity, device status) | `is_online()`, `reboot()`, `get_system_status()` |
| `wan` | WAN interface and path management | `get_uplinks()`, `get_active_uplink()`, `get_failover_config()` |
| `traffic` | Traffic analytics and classification | `get_client_applications()`, `get_traffic_classification()` |
| `policy` | QoS and security policy management | `get_traffic_shaping_rules()`, `get_applied_policy()` |

**Device Implementation Example:**

Each vendor requires a concrete implementation of the `ApplicationGateway` template. The implementation wraps the vendor-specific API (REST, Dashboard, CLI, etc.):

```python
# boardfarm3/devices/example_sdwan.py

class ExampleSDWAN(ApplicationGateway):
    """Example SD-WAN / ApplicationGateway device implementation.
    
    Real implementations would include:
    - MerakiMX (Meraki Dashboard API)
    - ViptelaSDWAN (vManage API)
    - FortiGateSDWAN (FortiOS REST API)
    - PaloAltoPrisma (Prisma SD-WAN API)
    """
    
    def __init__(self, config: dict, cmdline_args):
        self._config = config
        self._mgmt = VendorMgmt(self)      # Vendor-specific management
        self._wan = VendorWan(self)        # WAN interface control
        self._traffic = VendorTraffic(self) # Traffic analytics
        self._policy = VendorPolicy(self)  # Policy management
    
    @property
    def mgmt(self) -> VendorMgmt:
        return self._mgmt
    
    @property
    def wan(self) -> VendorWan:
        return self._wan
    
    @property
    def traffic(self) -> VendorTraffic:
        return self._traffic
    
    @property
    def policy(self) -> VendorPolicy:
        return self._policy
```

#### 2.7.3 Router Template with Impairment Property

Following the existing Boardfarm pattern where `wan.firewall` provides firewall control as a sub-component, the **Router** (ISP Gateway) device template includes an `impairment` property for tc/netem control:

```python
# boardfarm3/templates/isp_gateway.py

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from boardfarm3.lib.boardfarm_pexpect import BoardfarmPexpect
    from boardfarm3.lib.networking import IptablesFirewall, NetworkImpairment


class ISPGateway(ABC):
    """ISP Gateway / Router template.
    
    Represents the ISP edge router that connects WAN infrastructure
    to the DUT. Includes impairment control for simulating network conditions.
    """
    
    @property
    @abstractmethod
    def console(self) -> BoardfarmPexpect:
        """Device console."""
        raise NotImplementedError
    
    @property
    @abstractmethod
    def iface_dut(self) -> str:
        """Interface facing DUT."""
        raise NotImplementedError
    
    @property
    @abstractmethod
    def firewall(self) -> IptablesFirewall:
        """Firewall component for traffic filtering."""
        raise NotImplementedError
    
    @property
    @abstractmethod
    def impairment(self) -> NetworkImpairment:
        """Network impairment component for tc/netem control.
        
        Apply impairments on the DUT-facing interface to simulate
        various network conditions (latency, jitter, loss, bandwidth).
        
        Usage:
            router.impairment.set_profile("cable_degraded")
            router.impairment.set_delay("50ms", jitter="10ms")
            router.impairment.clear()
        """
        raise NotImplementedError
```

**NetworkImpairment Component:**

```python
# boardfarm3/lib/networking.py (addition)

class NetworkImpairment:
    """Network impairment control using tc/netem.
    
    Similar pattern to IptablesFirewall - wraps console commands
    for managing traffic control rules on a specific interface.
    """
    
    PROFILES = {
        "pristine": {"delay": "5ms", "jitter": "1ms", "loss": "0%"},
        "fiber_pristine": {"delay": "10ms", "jitter": "2ms", "loss": "0%"},
        "cable_typical": {"delay": "20ms", "jitter": "5ms", "loss": "0.1%"},
        "cable_degraded": {"delay": "50ms", "jitter": "15ms", "loss": "1%"},
        "lte_variable": {"delay": "80ms", "jitter": "30ms", "loss": "2%"},
        "congested": {"delay": "150ms", "jitter": "50ms", "loss": "5%"},
        "total_failure": {"loss": "100%"},
    }
    
    def __init__(self, console: BoardfarmPexpect, interface: str):
        self._console = console
        self._interface = interface
        self._current_profile: str | None = None
    
    def set_profile(self, profile: str) -> None:
        """Apply a named impairment profile."""
        if profile not in self.PROFILES:
            raise ValueError(f"Unknown profile: {profile}")
        settings = self.PROFILES[profile]
        self.clear()
        
        netem_opts = []
        if "delay" in settings:
            delay_str = f"delay {settings['delay']}"
            if "jitter" in settings:
                delay_str += f" {settings['jitter']}"
            netem_opts.append(delay_str)
        if "loss" in settings:
            netem_opts.append(f"loss {settings['loss']}")
        
        if netem_opts:
            self._console.execute_command(
                f"tc qdisc replace dev {self._interface} root netem {' '.join(netem_opts)}"
            )
        self._current_profile = profile
    
    def set_delay(self, delay: str, jitter: str | None = None) -> None:
        """Set latency on the interface."""
        jitter_str = f" {jitter}" if jitter else ""
        self._console.execute_command(
            f"tc qdisc replace dev {self._interface} root netem delay {delay}{jitter_str}"
        )
    
    def clear(self) -> None:
        """Remove all impairments from the interface."""
        self._console.execute_command(
            f"tc qdisc del dev {self._interface} root 2>/dev/null || true"
        )
        self._current_profile = None
    
    def get_status(self) -> dict:
        """Get current impairment status."""
        output = self._console.execute_command(f"tc qdisc show dev {self._interface}")
        return {
            "interface": self._interface,
            "profile": self._current_profile,
            "raw_config": output.strip(),
        }
```

**Key Architectural Benefit:** The impairment is a property of the Router (where the tc/netem commands execute), not a separate device. This:
- Follows existing Boardfarm patterns (`wan.firewall`, `cpe.sw`)
- Places responsibility where it belongs (the router owns its egress characteristics)
- Simplifies multi-WAN testing (each router manages its own path)

#### 2.7.4 Device Type Summary

| Device Type | Template | Sub-Components | Use Case |
|-------------|----------|----------------|----------|
| **CPE** | `CPE` | `hw`, `sw` | Basic routers, cable modems, residential gateways |
| **ApplicationGateway** | `ApplicationGateway` | `mgmt`, `wan`, `traffic`, `policy` | SD-WAN appliances, next-gen firewalls (Meraki, Viptela, Fortinet, etc.) |
| **ISPGateway (Router)** | `ISPGateway` | `firewall`, `impairment` | ISP edge simulation with impairment control |
| **WAN** | `WAN` | `firewall`, `multicast`, `nslookup` | WAN services container |
| **LAN** | `LAN` | (existing) | LAN client simulation |

---

## 3. Impairment Model: The Network Factory

The Network Factory is the **core differentiator** enabling deterministic QoE testing. It provides programmatic control over network conditions using Linux Traffic Control (`tc`) and Network Emulation (`netem`).

**Implementation:** The Network Factory is implemented as an **extension of Raikou**, adding impairment control to its existing network orchestration capabilities. This provides:
- **Single API** for topology creation and impairment management
- **Per-bridge impairment control** for multi-path scenarios
- **Veth-based tc/netem application** (see Section 2.3 for technical details)

### 3.1 Impairment Profiles

Named, versioned profiles represent real-world network conditions:

| Profile Name | Latency | Jitter | Packet Loss | Bandwidth | Description |
|--------------|---------|--------|-------------|-----------|-------------|
| `pristine` | 5ms | 1ms | 0% | 1 Gbps | Ideal conditions (baseline) |
| `fiber_pristine` | 10ms | 2ms | 0% | 1 Gbps | Enterprise fiber connection |
| `cable_typical` | 15ms | 5ms | 0.1% | 100 Mbps | Typical cable subscriber |
| `dsl_rural` | 45ms | 15ms | 0.5% | 25 Mbps | Rural DSL connection |
| `4g_mobile` | 80ms | 30ms | 1% | 20 Mbps | Mobile LTE user |
| `satellite` | 600ms | 50ms | 2% | 10 Mbps | Satellite/maritime |
| `congested_peak` | 25ms | 40ms | 3% | Variable | Peak hour congestion |
| `degraded_uplink` | 20ms | 10ms | 5% | 2 Mbps | ISP degradation |

**Implementation Example:**
```bash
# Apply 'dsl_rural' profile to DUT uplink interface
tc qdisc add dev eth-wan root netem \
    delay 45ms 15ms distribution normal \
    loss 0.5% \
    rate 25mbit
```

### 3.2 Transient Events

Scriptable events simulate real-world network incidents at precise moments:

| Event | Parameters | Implementation | Use Case |
|-------|------------|----------------|----------|
| `blackout` | `duration_sec` | `ip link set dev down/up` | Link failure, failover testing |
| `brownout` | `bandwidth_kbps`, `duration_sec` | `tc qdisc change ... rate` | Gradual degradation |
| `latency_spike` | `added_ms`, `duration_sec` | `tc qdisc change ... delay` | Routing flap simulation |
| `packet_storm` | `loss_pct`, `duration_sec` | `tc qdisc change ... loss` | Congestion event |
| `jitter_burst` | `jitter_ms`, `duration_sec` | `tc qdisc change ... delay X Yms` | Wireless interference |

**Event Scripting Example:**
```bash
# Simulate 30-second blackout during file upload
sleep 10  # Wait for upload to start
ip link set eth-wan down
sleep 30
ip link set eth-wan up
```

### 3.3 Deterministic Reproduction

Every impairment is timestamped and logged for exact reproduction:

```json
{
  "test_run_id": "qoe-2026-02-06-001",
  "impairment_log": [
    {"timestamp": "00:00:00.000", "action": "set_profile", "profile": "pristine"},
    {"timestamp": "00:01:30.500", "action": "set_profile", "profile": "congested_peak"},
    {"timestamp": "00:02:45.000", "action": "inject_event", "event": "latency_spike", "params": {"added_ms": 200, "duration_sec": 10}},
    {"timestamp": "00:03:30.000", "action": "set_profile", "profile": "pristine"}
  ]
}
```

To reproduce a failure:
1. Load the impairment log from the original test
2. Replay events at the same relative timestamps
3. Observe identical network behavior

---

## 4. QoE Measurement Framework

### 4.1 Measurement Architecture

QoE is measured at three layers, with application-layer metrics being the primary success criteria:

```
                    ┌─────────────────────────────────┐
                    │      QoE ASSERTION ENGINE       │
                    │  (Pass/Fail against SLO)        │
                    └───────────────┬─────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
┌───────▼───────────┐    ┌──────────▼──────────┐    ┌──────────▼──────────┐
│ APPLICATION LAYER │    │  TRANSPORT LAYER    │    │   NETWORK LAYER     │
│ (User Experience) │    │  (Connection Health)│    │   (Link Health)     │
├───────────────────┤    ├─────────────────────┤    ├─────────────────────┤
│ • Page Load Time  │    │ • TCP Retransmits   │    │ • ICMP RTT          │
│ • Time to First   │    │ • WebRTC getStats() │    │ • Traceroute hops   │
│   Byte (TTFB)     │    │ • RTP packet loss   │    │ • tc qdisc stats    │
│ • Video Buffer %  │    │ • TLS handshake     │    │ • Interface counters│
│ • Rebuffer Events │    │ • Connection resets │    │                     │
│ • MOS Score       │    │                     │    │                     │
│ • Resolution      │    │                     │    │                     │
└───────────────────┘    └─────────────────────┘    └─────────────────────┘
        ▲                          ▲                          ▲
        │                          │                          │
   PRIMARY                    DIAGNOSTIC                 DIAGNOSTIC
   (Pass/Fail)                (Root Cause)              (Root Cause)
```

### 4.2 Service Category Metrics

#### 4.2.1 Productivity Applications

**Target:** Office 365, Google Workspace, Salesforce, custom SaaS

**Measurement Tool:** Playwright (Headless Chromium) + Navigation Timing API

| Metric | API Source | Description |
|--------|------------|-------------|
| **Time to First Byte (TTFB)** | `performance.timing.responseStart - navigationStart` | Server + network responsiveness |
| **DOM Content Loaded** | `performance.timing.domContentLoadedEventEnd` | Page becomes interactive |
| **Page Load Time (PLT)** | `performance.timing.loadEventEnd - navigationStart` | Full page render complete |
| **Transaction Time** | Custom measurement | End-to-end workflow (e.g., login → upload → confirm) |

**Why Playwright?**
- Generates authentic TLS Client Hello (SNI), HTTP headers, User-Agent
- Triggers DPI classification (DUT sees "Office 365", not generic "HTTPS")
- Executes JavaScript, loads dynamic content

#### 4.2.2 Video Streaming

**Target:** Netflix, YouTube, Disney+, Twitch, live streams

**Measurement Tool:** Playwright + Media Source Extensions (MSE) API

| Metric | API Source | Description |
|--------|------------|-------------|
| **Startup Time** | Custom: time from play() to first frame | Initial buffering delay |
| **Rebuffer Ratio** | `video.buffered` vs playhead | % of time spent rebuffering |
| **Rebuffer Count** | `waiting` event count | Number of stall events |
| **Resolution Changes** | `videoWidth`, `videoHeight` monitoring | Adaptive bitrate adjustments |
| **Current Resolution** | `videoWidth x videoHeight` | Achieved quality level |

**Adaptive Bitrate Considerations:**
- Under impairment, ABR algorithms may reduce quality to avoid stalls
- Test should verify graceful degradation, not just absence of stalls

#### 4.2.3 Real-Time Communication

**Target:** Microsoft Teams, Zoom, Google Meet, WebRTC, VoIP

**Measurement Tool:** Playwright + WebRTC `getStats()` API, or pjsua for SIP

| Metric | API Source | Description |
|--------|------------|-------------|
| **Round Trip Time (RTT)** | `RTCIceCandidatePairStats.currentRoundTripTime` | Network latency |
| **Jitter** | `RTCInboundRtpStreamStats.jitter` | Packet timing variance |
| **Packet Loss** | `RTCInboundRtpStreamStats.packetsLost` | Dropped packets |
| **MOS Score** | Calculated from above metrics | Mean Opinion Score (1-5) |
| **Resolution** | `RTCInboundRtpStreamStats.frameWidth/Height` | Video quality achieved |
| **Frames Dropped** | `RTCInboundRtpStreamStats.framesDropped` | Decode/render failures |

**MOS Calculation (ITU-T G.107 E-Model simplified):**
```
R = 93.2 - (latency_ms / 40) - (jitter_ms * 2) - (packet_loss_pct * 2.5)
MOS = 1 + 0.035*R + R*(R-60)*(100-R)*7e-6
```

### 4.3 QoE Thresholds (Service Level Objectives)

| Metric | Good | Acceptable | Poor | Critical |
|--------|------|------------|------|----------|
| **Page Load Time** | < 2s | 2-5s | 5-10s | > 10s |
| **TTFB** | < 200ms | 200-500ms | 500ms-1s | > 1s |
| **Video Startup** | < 1s | 1-3s | 3-5s | > 5s |
| **Rebuffer Ratio** | 0% | < 1% | 1-5% | > 5% |
| **Voice MOS** | > 4.0 | 3.5-4.0 | 3.0-3.5 | < 3.0 |
| **Video Call RTT** | < 150ms | 150-300ms | 300-500ms | > 500ms |
| **Video Call Jitter** | < 30ms | 30-50ms | 50-100ms | > 100ms |
| **Packet Loss** | < 0.5% | 0.5-2% | 2-5% | > 5% |

---

## 5. DUT Verification Through Boardfarm Templates

While QoE metrics provide the user-centric pass/fail criteria, device-specific verification confirms that DUT features (QoS, DPI, policies) are functioning as configured. This verification leverages Boardfarm's template system (see Section 2.7).

### 5.1 Verification Through Device Templates

Rather than a separate "adapter" pattern, device verification uses the Boardfarm device templates. Each device type provides standardized methods for querying device state:

| DUT Type | Boardfarm Template | Verification Sub-Component |
|----------|-------------------|----------------------------|
| **SD-WAN / NGFW** | `ApplicationGateway` | `dut.traffic`, `dut.policy` |
| **Cable Modem** | `CPE` | `dut.sw` (via TR-069/ACS) |
| **Linux Router** | `LinuxDevice` or `CPE` | Console access |

### 5.2 ApplicationGateway Verification (SD-WAN, NGFW)

For L7-capable devices, the `ApplicationGateway` template provides traffic and policy verification:

```python
# boardfarm3/templates/app_gateway/app_gateway_traffic.py

class AppGatewayTraffic(ABC):
    """Traffic analytics sub-component for ApplicationGateway."""
    
    @abstractmethod
    def get_client_applications(self, mac_address: str, timespan_sec: int = 300) -> list[dict]:
        """Get applications used by a client.
        
        Returns:
            List of {"application": str, "category": str, "bytes": int, ...}
        """
        raise NotImplementedError
    
    @abstractmethod
    def get_traffic_classification(self, mac_address: str) -> dict | None:
        """Get current traffic classification for a client.
        
        Returns:
            {"application": str, "category": str, "latency_class": str, ...}
        """
        raise NotImplementedError
```

**Vendor-Specific Implementation Example:**

Each ApplicationGateway vendor requires a concrete implementation. Below is a generic example showing the pattern:

```python
# boardfarm3/devices/vendor/vendor_traffic.py

class VendorTraffic(AppGatewayTraffic):
    """Vendor-specific traffic analytics implementation.
    
    Real implementations wrap vendor APIs:
    - Meraki: Dashboard API (getNetworkClientsApplicationUsage)
    - Viptela: vManage REST API
    - Fortinet: FortiOS REST API
    - Palo Alto: Prisma SD-WAN API
    """
    
    def __init__(self, device: ApplicationGateway):
        self._device = device
        self._api = device.mgmt.api_client  # Vendor-specific API client
    
    def get_client_applications(self, mac_address: str, timespan_sec: int = 300) -> list[dict]:
        # Implementation varies by vendor
        # Cloud-managed devices may have eventual consistency (3-5 min delay)
        return self._api.get_application_usage(mac_address, timespan_sec)
    
    def get_traffic_classification(self, mac_address: str) -> dict | None:
        return self._api.get_client_classification(mac_address)
```

**Important:** Cloud-managed ApplicationGateway devices (Meraki, Viptela, etc.) often have **eventual consistency**. Tests may need to include a delay (typically 3-5 minutes) between traffic generation and API verification.

### 5.3 CPE Verification (Cable Modems, TR-069 Devices)

For basic CPE devices, verification uses the existing `cpe.sw` sub-component which interfaces with TR-069/ACS:

```python
# Using existing Boardfarm use cases
from boardfarm3.use_cases import cpe

# Get interface statistics via TR-181
stats = cpe.get_interface_stats(env.cpe, interface="wan")

# Verify QoS queue statistics
qos_stats = cpe.get_qos_queue_stats(env.cpe)
```

### 5.4 ISP Gateway Verification (Router)

The Router's verification includes both firewall and impairment status:

```python
# boardfarm3/use_cases/isp_gateway.py

def get_network_status(router: ISPGateway) -> dict:
    """Get ISP gateway network status including impairment config."""
    return {
        "impairment": router.impairment.get_status(),
        "interface_stats": router.console.execute_command(
            f"ip -s link show {router.iface_dut}"
        ),
    }
```

### 5.5 Use Case: Verifying DPI Classification

```python
# boardfarm3/use_cases/qoe.py

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from boardfarm3.templates.app_gateway import ApplicationGateway


def verify_traffic_classification(
    dut: ApplicationGateway,
    client_mac: str,
    expected_app: str,
    timeout_sec: int = 300,
) -> bool:
    """Verify DUT correctly classified client traffic.
    
    Args:
        dut: The ApplicationGateway device (e.g., SD-WAN appliance)
        client_mac: Client's MAC address
        expected_app: Expected application classification
        timeout_sec: Time to wait for eventual consistency
    
    Returns:
        True if classification matches expected
        
    Note:
        Cloud-managed devices may have eventual consistency.
        This function polls until timeout or match.
    """
    import time
    start = time.time()
    
    while time.time() - start < timeout_sec:
        apps = dut.traffic.get_client_applications(client_mac)
        for app in apps:
            if app.get("application") == expected_app:
                return True
        time.sleep(30)  # Poll every 30 seconds
    
    return False
```

---

## 6. Test Scenarios

### 6.1 Baseline Performance Verification

**Objective:** Establish baseline QoE metrics under ideal conditions

```gherkin
Scenario: Baseline QoE - Productivity Application
  Given the network factory is set to "pristine" profile
  And a simulated browser user is connected to the DUT LAN
  When the user navigates to Office 365 and uploads a 10MB file
  Then the page load time should be less than 2 seconds
  And the upload transaction should complete within 30 seconds
  And the DUT should classify traffic as "Office 365" (if DPI capable)
```

### 6.2 Degraded Network - Streaming Resilience

**Objective:** Verify adaptive bitrate handles degradation gracefully

```gherkin
Scenario: Video Streaming under Network Degradation
  Given the network factory is set to "cable_typical" profile
  And a simulated browser user is streaming YouTube at 1080p
  When the network factory transitions to "degraded_uplink" profile
  Then the video rebuffer ratio should remain below 1%
  And the video resolution should adapt downward within 10 seconds
  And when the network factory returns to "cable_typical" profile
  Then the video resolution should recover to 720p or higher within 30 seconds
```

### 6.3 Link Failure - SD-WAN Failover

**Objective:** Verify seamless failover during active session

```gherkin
Scenario: Voice Call Continuity during WAN Failover
  Given the DUT has dual WAN connections (primary and backup)
  And a simulated user is in an active WebRTC voice call
  And the call MOS score is above 4.0
  When the network factory injects a "blackout" event on primary WAN
  Then the call should continue without disconnection
  And the MOS score should remain above 3.5 within 5 seconds
  And the DUT should report failover to backup WAN
```

### 6.4 QoS Policy Validation

**Objective:** Verify traffic prioritization under congestion

```gherkin
Scenario: Voice Priority over Bulk Data
  Given the network factory is set to "congested_peak" profile
  And simulated user A is in an active VoIP call
  And simulated user B is performing a large file download
  When both users compete for limited bandwidth
  Then user A's voice MOS should remain above 3.5
  And user B's download throughput should be throttled
  And the DUT QoS statistics should show prioritization of voice traffic
```

### 6.5 DPI Classification Verification

**Objective:** Verify deep packet inspection correctly identifies applications

```gherkin
Scenario: Application Classification Accuracy
  Given a simulated browser user connected to the DUT LAN
  When the user accesses the following applications:
    | Application     | Expected Classification |
    | Netflix         | Video Streaming         |
    | Microsoft Teams | Video Conferencing      |
    | Salesforce      | Business Application    |
    | YouTube         | Video Streaming         |
  Then the DUT should classify each application correctly
  And the appropriate traffic shaping policy should be applied
```

---

## 7. Implementation with Boardfarm

### 7.1 Testbed Configuration

The QoE testbed extends the standard Raikou topology with Network Factory (impairment) capabilities and browser-based users. Two configuration variants are supported:

#### 7.1.1 Simple Topology (Single WAN Path)

For basic routers, cable modems, and single-WAN devices:

```json
{
  "testbed_name": "qoe_verification_simple",
  "topology": "raikou_qoe_single_wan",
  
  "devices": {
    "dut": {
      "type": "CPE",
      "comment": "Device Under Test - basic router, cable modem (L2/L3 device)",
      "template": "boardfarm3.templates.cpe.CPE",
      "interfaces": {
        "eth0": {"bridge": "lan-cpe", "role": "lan"},
        "eth1": {"bridge": "cpe-rtr", "role": "wan"}
      }
    },
    
    "router": {
      "type": "ISPGateway",
      "comment": "ISP Edge Gateway with impairment control",
      "template": "boardfarm3.templates.isp_gateway.ISPGateway",
      "image": "router:v1.2.0",
      "interfaces": {
        "cpe": {"bridge": "cpe-rtr", "ip": "10.1.1.1/24"},
        "eth1": {"bridge": "rtr-wan", "ip": "172.25.1.1/24"}
      },
      "impairment_interface": "eth1"
    },
    
    "wan": {
      "type": "WAN",
      "comment": "DNS, HTTP, Mock SaaS API, file transfer",
      "interfaces": {"eth1": {"bridge": "rtr-wan", "ip": "172.25.1.2/24"}}
    },
    "streaming": {
      "type": "Streaming",
      "comment": "HLS/DASH video server with multi-bitrate content",
      "image": "streaming:v1.0.0",
      "interfaces": {"eth1": {"bridge": "rtr-wan", "ip": "172.25.1.10/24"}}
    },
    "conferencing": {
      "type": "Conferencing",
      "comment": "Jitsi Meet, coturn (STUN/TURN), WebRTC signaling",
      "image": "conferencing:v1.0.0",
      "interfaces": {"eth1": {"bridge": "rtr-wan", "ip": "172.25.1.15/24"}}
    },
    "dhcp": {"type": "DHCP", "interfaces": {"eth1": {"bridge": "rtr-wan", "ip": "172.25.1.20/24"}}},
    "acs": {"type": "ACS", "interfaces": {"eth1": {"bridge": "rtr-wan", "ip": "172.25.1.40/24"}}},
    "sipcenter": {"type": "SIPCenter", "interfaces": {"eth1": {"bridge": "rtr-wan", "ip": "172.25.1.5/24"}}},
    
    "lan": {"type": "LAN", "interfaces": {"eth1": {"bridge": "lan-cpe"}}},
    "browser_user_1": {"type": "PlaywrightBrowser", "interfaces": {"eth1": {"bridge": "lan-cpe"}}},
    "lan_phone": {"type": "SIPPhone", "interfaces": {"eth1": {"bridge": "lan-cpe"}}}
  },
  
  "bridges": {
    "cpe-rtr": {"subnet": "10.1.1.0/24"},
    "lan-cpe": {},
    "rtr-wan": {"subnet": "172.25.1.0/24"}
  },
  
  "impairments": {
    "rtr-wan": {
      "comment": "Single impairment point for all WAN traffic",
      "target_container": "router",
      "target_interface": "eth1",
      "default_profile": "cable_typical"
    }
  }
}
```

#### 7.1.2 Multi-Path Topology (SD-WAN / ApplicationGateway)

For enterprise ApplicationGateway devices with multiple WAN interfaces:

```json
{
  "testbed_name": "qoe_verification_sdwan",
  "topology": "raikou_qoe_multi_wan",
  
  "devices": {
    "dut": {
      "type": "ApplicationGateway",
      "comment": "SD-WAN or NGFW appliance (L3-L7 device)",
      "template": "boardfarm3.templates.app_gateway.ApplicationGateway",
      "device_class": "boardfarm3.devices.vendor_sdwan.VendorSDWAN",
      "interfaces": {
        "eth0": {"bridge": "lan-cpe", "role": "lan"},
        "eth1": {"bridge": "wan1-bridge", "role": "wan1"},
        "eth2": {"bridge": "wan2-bridge", "role": "wan2"},
        "usb0": {"bridge": "lte-bridge", "role": "lte_backup"}
      },
      "config": {
        "api_url": "${VENDOR_API_URL}",
        "api_key": "${VENDOR_API_KEY}",
        "device_id": "device-12345"
      }
    },
    
    "wan_services": {
      "type": "WAN",
      "comment": "Shared internet services (DNS, HTTP, CDN, SaaS)",
      "image": "wan:v1.2.0",
      "interfaces": {
        "eth1": {"bridge": "wan1-bridge", "ip": "172.25.1.2/24"},
        "eth2": {"bridge": "wan2-bridge", "ip": "172.26.1.2/24"},
        "eth3": {"bridge": "lte-bridge", "ip": "172.27.1.2/24"}
      }
    },
    
    "dhcp": {"type": "DHCP", "interfaces": {"eth1": {"bridge": "wan1-bridge", "ip": "172.25.1.20/24"}}},
    "sipcenter": {"type": "SIPCenter", "interfaces": {"eth1": {"bridge": "wan1-bridge", "ip": "172.25.1.5/24"}}},
    
    "lan": {"type": "LAN", "interfaces": {"eth1": {"bridge": "lan-cpe"}}},
    "browser_user_1": {"type": "PlaywrightBrowser", "interfaces": {"eth1": {"bridge": "lan-cpe"}}},
    "browser_user_2": {"type": "PlaywrightBrowser", "interfaces": {"eth1": {"bridge": "lan-cpe"}}},
    "lan_phone": {"type": "SIPPhone", "interfaces": {"eth1": {"bridge": "lan-cpe"}}}
  },
  
  "bridges": {
    "lan-cpe": {"comment": "DUT LAN"},
    "wan1-bridge": {"subnet": "172.25.1.0/24", "comment": "Primary WAN (fiber/cable)"},
    "wan2-bridge": {"subnet": "172.26.1.0/24", "comment": "Secondary WAN (DSL/backup)"},
    "lte-bridge": {"subnet": "172.27.1.0/24", "comment": "LTE/Cellular failover"}
  },
  
  "impairments": {
    "wan1-bridge": {
      "comment": "Primary WAN - fiber-like characteristics",
      "target_container": "dut",
      "target_interface": "eth1",
      "default_profile": "fiber_pristine"
    },
    "wan2-bridge": {
      "comment": "Secondary WAN - cable/DSL characteristics",
      "target_container": "dut",
      "target_interface": "eth2",
      "default_profile": "cable_typical"
    },
    "lte-bridge": {
      "comment": "LTE backup - mobile characteristics",
      "target_container": "dut",
      "target_interface": "usb0",
      "default_profile": "4g_mobile"
    }
  }
}
```

**Key Differences:**

| Aspect | Simple Topology | Multi-Path Topology |
|--------|-----------------|---------------------|
| WAN Bridges | 1 (`rtr-wan`) | 3+ (`wan1-bridge`, `wan2-bridge`, `lte-bridge`) |
| Impairment Points | 1 (Router's eth1) | 3+ (DUT's each WAN interface) |
| Router Container | Yes (ISP simulation) | Optional (DUT has direct WAN) |
| SD-WAN Testing | No | Yes (failover, path selection) |

### 7.2 OVS Bridge Configuration

```
┌───────────────────────────────────────────────────────────────────────┐
│                        Raikou OVS Bridges                              │
├───────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  rtr-wan bridge (172.25.1.0/24) ← Network Factory applies here        │
│  ├── [tc/netem rules]                 - Impairment injection          │
│  ├── Router eth1 (172.25.1.1)         - ISP Gateway (wan-facing)      │
│  ├── WAN eth1 (172.25.1.2)            - DNS/HTTP/Mock SaaS            │
│  ├── Streaming eth1 (172.25.1.10)     - HLS/DASH video server [NEW]   │
│  ├── Conferencing eth1 (172.25.1.15)  - Jitsi/WebRTC [NEW]            │
│  ├── DHCP eth1 (172.25.1.20)          - Provisioning                  │
│  ├── ACS eth1 (172.25.1.40)           - TR-069                        │
│  └── SIP Center eth1 (172.25.1.5)     - VoIP                          │
│                                                                        │
│  cpe-rtr bridge (10.1.1.0/24)                                         │
│  ├── Router cpe (10.1.1.1)            - ISP Gateway (cpe-facing)      │
│  └── DUT eth1 (10.1.1.x DHCP)         - Device Under Test             │
│                                                                        │
│  lan-cpe bridge (DUT LAN subnet)                                      │
│  ├── DUT eth0 (br-lan)                - LAN gateway                   │
│  ├── LAN eth1                         - Standard test client          │
│  ├── Browser User 1 eth1              - QoE measurement               │
│  ├── Browser User 2 eth1              - QoE measurement               │
│  └── LAN Phone eth1                   - VoIP client                   │
│                                                                        │
└───────────────────────────────────────────────────────────────────────┘
```

### 7.3 Network Factory: Implementation

The Network Factory is implemented at two levels:

**Level 1: Boardfarm Device Property (Primary Interface)**
- Test cases interact with `router.impairment` property
- Follows existing Boardfarm patterns (`wan.firewall`, `cpe.sw`)
- Commands execute via the Router container's console

**Level 2: Raikou API (Alternative/Advanced Interface)**  
- For scenarios requiring external orchestration
- Useful when impairment control happens outside Boardfarm
- Leverages Raikou's existing veth interface management

For most QoE testing, the Boardfarm `router.impairment` property is the recommended interface.

#### 7.3.1 Proposed Raikou API Extension

New API endpoint for impairment management:

```python
# raikou-net/app/routers/impairment.py (proposed extension)

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Literal
from app.utils import run_command, get_logger

router = APIRouter()
_LOGGER = get_logger("impairment")

class ImpairmentConfig(BaseModel):
    """Configuration for network impairment on a bridge."""
    container: str  # Target container name
    interface: str  # Container interface (e.g., "eth1")
    profile: Optional[str] = None  # Named profile
    # Or explicit parameters:
    delay: Optional[str] = None    # e.g., "50ms"
    jitter: Optional[str] = None   # e.g., "10ms"
    loss: Optional[str] = None     # e.g., "1%"
    rate: Optional[str] = None     # e.g., "100mbit"

PROFILES = {
    "pristine": {"delay": "5ms", "jitter": "1ms", "loss": "0%", "rate": "1gbit"},
    "fiber_pristine": {"delay": "10ms", "jitter": "2ms", "loss": "0%", "rate": "1gbit"},
    "cable_typical": {"delay": "15ms", "jitter": "5ms", "loss": "0.1%", "rate": "100mbit"},
    "dsl_rural": {"delay": "45ms", "jitter": "15ms", "loss": "0.5%", "rate": "25mbit"},
    "4g_mobile": {"delay": "80ms", "jitter": "30ms", "loss": "1%", "rate": "20mbit"},
    "satellite": {"delay": "600ms", "jitter": "50ms", "loss": "2%", "rate": "10mbit"},
    "congested_peak": {"delay": "25ms", "jitter": "40ms", "loss": "3%", "rate": "5mbit"},
    "degraded_uplink": {"delay": "20ms", "jitter": "10ms", "loss": "5%", "rate": "2mbit"},
}

def _get_veth_port(container: str, interface: str) -> str:
    """
    Find the host-side veth port for a container interface.
    
    Raikou stores container/interface metadata in OVS external_ids.
    """
    result = run_command(
        f"ovs-vsctl --data=bare --no-heading --columns=name find interface "
        f'external_ids:container_id="{container}" '
        f'external_ids:container_iface="{interface}"',
        check=True
    )
    port = result.stdout.strip()
    if not port:
        raise ValueError(f"No veth found for {container}:{interface}")
    return port

@router.post("/impairment/set")
async def set_impairment(bridge: str, config: ImpairmentConfig) -> dict:
    """
    Apply network impairment to a container's interface.
    
    The impairment is applied to the host-side veth interface,
    NOT directly to the OVS bridge (which doesn't support tc/netem).
    """
    # Find the veth port on host side
    veth_port = _get_veth_port(config.container, config.interface)
    _LOGGER.info(f"Found veth port {veth_port} for {config.container}:{config.interface}")
    
    # Get profile parameters or use explicit values
    if config.profile:
        if config.profile not in PROFILES:
            raise HTTPException(400, f"Unknown profile: {config.profile}")
        params = PROFILES[config.profile]
    else:
        params = {
            "delay": config.delay or "0ms",
            "jitter": config.jitter or "0ms",
            "loss": config.loss or "0%",
            "rate": config.rate or "1gbit",
        }
    
    # Clear existing rules
    run_command(f"tc qdisc del dev {veth_port} root", check=False)
    
    # Apply tc/netem rules
    cmd = (
        f"tc qdisc add dev {veth_port} root netem "
        f"delay {params['delay']} {params['jitter']} distribution normal "
        f"loss {params['loss']} "
        f"rate {params['rate']}"
    )
    run_command(cmd, check=True)
    
    _LOGGER.info(f"Applied impairment to {veth_port}: {params}")
    return {"status": "success", "veth_port": veth_port, "params": params}

@router.delete("/impairment/clear")
async def clear_impairment(container: str, interface: str) -> dict:
    """Remove all impairments from a container's interface."""
    veth_port = _get_veth_port(container, interface)
    run_command(f"tc qdisc del dev {veth_port} root", check=False)
    _LOGGER.info(f"Cleared impairment from {veth_port}")
    return {"status": "success", "veth_port": veth_port}
```

#### 7.3.2 Boardfarm Network Factory Client

Boardfarm component that interfaces with Raikou's impairment API:

```python
# boardfarm/lib/network_factory.py

import time
import requests
from typing import Dict, List, Optional
from dataclasses import dataclass, field

@dataclass
class PathConfig:
    """Configuration for a single network path."""
    bridge: str
    container: str
    interface: str
    default_profile: str = "pristine"

class NetworkFactory:
    """
    Boardfarm component for deterministic network impairment.
    
    Communicates with Raikou's impairment API to apply tc/netem rules
    to veth interfaces. Supports both single-path and multi-path topologies.
    """
    
    def __init__(self, raikou_url: str, paths: Dict[str, PathConfig]):
        """
        Initialize NetworkFactory with path configurations.
        
        Args:
            raikou_url: Raikou API base URL (e.g., "http://localhost:8000")
            paths: Dictionary of path_name -> PathConfig
                   Simple topology: {"wan": PathConfig(...)}
                   Multi-path: {"wan1": PathConfig(...), "wan2": PathConfig(...), "lte": PathConfig(...)}
        """
        self.raikou_url = raikou_url
        self.paths = paths
        self.impairment_log: List[Dict] = []
        self._start_time = time.time()
        self._current_profiles: Dict[str, str] = {}
    
    def set_profile(self, path: str, profile_name: str) -> None:
        """
        Apply a named impairment profile to a specific path.
        
        Args:
            path: Path name (e.g., "wan1", "wan2", "lte")
            profile_name: Profile to apply (e.g., "cable_typical", "4g_mobile")
        """
        if path not in self.paths:
            raise ValueError(f"Unknown path: {path}. Available: {list(self.paths.keys())}")
        
        config = self.paths[path]
        response = requests.post(
            f"{self.raikou_url}/impairment/set",
            params={"bridge": config.bridge},
            json={
                "container": config.container,
                "interface": config.interface,
                "profile": profile_name
            }
        )
        response.raise_for_status()
        
        self._current_profiles[path] = profile_name
        self._log_event("set_profile", {"path": path, "profile": profile_name})
    
    def set_all_paths(self, profile_name: str) -> None:
        """Apply the same profile to all paths."""
        for path in self.paths:
            self.set_profile(path, profile_name)
    
    def inject_event(self, path: str, event: str, **params) -> None:
        """
        Inject a transient network event on a specific path.
        
        Args:
            path: Path name
            event: Event type ("blackout", "latency_spike", "packet_storm", "brownout")
            **params: Event-specific parameters
        """
        if event == "blackout":
            self._blackout(path, params.get("duration_sec", 10))
        elif event == "latency_spike":
            self._latency_spike(path, params.get("added_ms", 100), params.get("duration_sec", 5))
        elif event == "packet_storm":
            self._packet_storm(path, params.get("loss_pct", 10), params.get("duration_sec", 5))
        elif event == "brownout":
            self._brownout(path, params.get("bandwidth_kbps", 500), params.get("duration_sec", 10))
        
        self._log_event("inject_event", {"path": path, "event": event, "params": params})
    
    def clear_all_impairments(self) -> None:
        """Remove all impairments from all paths."""
        for path, config in self.paths.items():
            requests.delete(
                f"{self.raikou_url}/impairment/clear",
                params={"container": config.container, "interface": config.interface}
            )
            self._current_profiles.pop(path, None)
    
    def get_impairment_log(self) -> List[Dict]:
        """Return timestamped log of all impairments for reproduction."""
        return self.impairment_log
    
    def _blackout(self, path: str, duration_sec: int) -> None:
        """Simulate complete link failure on a path."""
        config = self.paths[path]
        # Use Raikou to bring interface down
        requests.post(
            f"{self.raikou_url}/impairment/set",
            params={"bridge": config.bridge},
            json={"container": config.container, "interface": config.interface, "rate": "0kbit"}
        )
        time.sleep(duration_sec)
        # Restore previous profile
        if path in self._current_profiles:
            self.set_profile(path, self._current_profiles[path])
    
    def _latency_spike(self, path: str, added_ms: int, duration_sec: int) -> None:
        """Simulate temporary latency increase."""
        # Implementation similar to existing, but calls Raikou API
        pass
    
    def _packet_storm(self, path: str, loss_pct: int, duration_sec: int) -> None:
        """Simulate packet loss event."""
        pass
    
    def _brownout(self, path: str, bandwidth_kbps: int, duration_sec: int) -> None:
        """Simulate bandwidth degradation."""
        pass
    
    def _log_event(self, action: str, details: Dict) -> None:
        """Log impairment event with timestamp."""
        elapsed = time.time() - self._start_time
        timestamp = f"{int(elapsed // 60):02d}:{elapsed % 60:06.3f}"
        self.impairment_log.append({"timestamp": timestamp, "action": action, **details})
```

#### 7.3.3 Boardfarm Use Cases for Impairment Control

The primary interface for test cases is through Boardfarm use cases that operate on the `router.impairment` property:

```python
# boardfarm3/use_cases/impairment.py

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from boardfarm3.templates.isp_gateway import ISPGateway


def apply_network_profile(router: ISPGateway, profile: str) -> None:
    """Apply a network condition profile to the ISP gateway.
    
    Args:
        router: The ISP Gateway device
        profile: Profile name (e.g., "pristine", "cable_degraded", "congested")
    
    Example:
        apply_network_profile(env.router, "cable_degraded")
    """
    router.impairment.set_profile(profile)


def simulate_network_degradation(router: ISPGateway, delay_ms: int, loss_pct: float) -> None:
    """Simulate specific network degradation.
    
    Args:
        router: The ISP Gateway device
        delay_ms: Latency to add in milliseconds
        loss_pct: Packet loss percentage
    
    Example:
        simulate_network_degradation(env.router, delay_ms=150, loss_pct=3.0)
    """
    router.impairment.clear()
    router.impairment.set_delay(f"{delay_ms}ms")
    # Loss would require additional tc command


def restore_pristine_network(router: ISPGateway) -> None:
    """Remove all impairments and restore ideal conditions.
    
    Example:
        restore_pristine_network(env.router)
    """
    router.impairment.set_profile("pristine")


def get_network_status(router: ISPGateway) -> dict:
    """Get current network impairment status.
    
    Returns:
        Dictionary with current impairment configuration
    """
    return router.impairment.get_status()
```

**Test Case Example (Gherkin + Python):**

```gherkin
@qoe @impairment
Scenario: Video streaming resilience under degraded network
  Given the testbed is operational
  And the network is in "pristine" condition
  When a user starts streaming video at 1080p
  And the network degrades to "cable_degraded" profile
  Then the video should adapt quality within 10 seconds
  And the rebuffer ratio should be below 2%
```

```python
# test_qoe_streaming.py

def test_video_streaming_under_degradation(env, browser_user):
    """Test video streaming QoE under network degradation."""
    # Setup: pristine network
    apply_network_profile(env.router, "pristine")
    
    # Start streaming
    metrics_baseline = browser_user.play_video("https://streaming.test.local/movie.m3u8")
    assert metrics_baseline["initial_resolution"] == "1080p"
    
    # Apply degradation
    apply_network_profile(env.router, "cable_degraded")
    
    # Measure behavior under stress
    time.sleep(10)
    metrics_degraded = browser_user.get_streaming_metrics()
    
    # Verify graceful degradation
    assert metrics_degraded["rebuffer_ratio"] < 0.02  # < 2%
    # Resolution should have adapted
    
    # Cleanup
    restore_pristine_network(env.router)
```

#### 7.3.4 Raikou API (Alternative Interface)

For advanced scenarios or external orchestration, Raikou provides an API extension:

**Simple Topology (Single WAN):**
```python
# Initialize for single-path topology (direct Raikou API)
factory = NetworkFactory(
    raikou_url="http://raikou:8000",
    paths={
        "wan": PathConfig(
            bridge="rtr-wan",
            container="router",
            interface="eth1",
            default_profile="cable_typical"
        )
    }
)

# Apply impairment
factory.set_profile("wan", "congested_peak")

# Inject transient event
factory.inject_event("wan", "latency_spike", added_ms=200, duration_sec=10)
```

**Multi-Path Topology (SD-WAN):**
```python
# Initialize for multi-path topology
factory = NetworkFactory(
    raikou_url="http://raikou:8000",
    paths={
        "wan1": PathConfig(bridge="wan1-bridge", container="dut", interface="eth1", default_profile="fiber_pristine"),
        "wan2": PathConfig(bridge="wan2-bridge", container="dut", interface="eth2", default_profile="cable_typical"),
        "lte": PathConfig(bridge="lte-bridge", container="dut", interface="usb0", default_profile="4g_mobile"),
    }
)

# Test failover: degrade primary, verify traffic shifts
factory.set_profile("wan1", "congested_peak")  # Primary degraded
factory.set_profile("wan2", "pristine")         # Secondary optimal
# Expect: SD-WAN shifts traffic to wan2

# Test blackout failover
factory.inject_event("wan1", "blackout", duration_sec=30)
# Expect: Immediate failover to wan2 or lte
```

### 7.4 QoE Measurement Use Cases

```python
# boardfarm3/use_cases/qoe.py

def measure_page_load_time(browser: PlaywrightBrowser, url: str) -> Dict:
    """
    Measure page load performance metrics.
    
    Returns:
        {
            "ttfb_ms": float,
            "dom_content_loaded_ms": float,
            "page_load_time_ms": float,
            "url": str
        }
    """
    page = browser.new_page()
    page.goto(url, wait_until="load")
    
    timing = page.evaluate("""() => {
        const t = performance.timing;
        return {
            ttfb: t.responseStart - t.navigationStart,
            dcl: t.domContentLoadedEventEnd - t.navigationStart,
            plt: t.loadEventEnd - t.navigationStart
        };
    }""")
    
    return {
        "ttfb_ms": timing["ttfb"],
        "dom_content_loaded_ms": timing["dcl"],
        "page_load_time_ms": timing["plt"],
        "url": url
    }


def measure_video_streaming_qoe(browser: PlaywrightBrowser, video_url: str, duration_sec: int) -> Dict:
    """
    Measure video streaming quality metrics.
    
    Returns:
        {
            "startup_time_ms": float,
            "rebuffer_count": int,
            "rebuffer_ratio": float,
            "resolution_changes": List[Dict],
            "final_resolution": str
        }
    """
    # Implementation uses MSE API monitoring
    pass


def measure_webrtc_call_qoe(browser: PlaywrightBrowser, call_duration_sec: int) -> Dict:
    """
    Measure WebRTC call quality metrics.
    
    Returns:
        {
            "avg_rtt_ms": float,
            "avg_jitter_ms": float,
            "packet_loss_pct": float,
            "mos_score": float,
            "resolution": str,
            "frames_dropped": int
        }
    """
    # Implementation uses getStats() API polling
    pass
```

---

## 8. Appendix

### A. Impairment Profile Library

Profiles are versioned and stored as YAML for easy management:

```yaml
# impairment_profiles/v1.0/cable_typical.yaml
name: cable_typical
version: "1.0"
description: "Typical cable internet subscriber conditions"
parameters:
  delay_ms: 15
  jitter_ms: 5
  loss_percent: 0.1
  bandwidth_mbps: 100
  
metadata:
  created: "2026-02-06"
  author: "QoE Team"
  reference: "FCC Measuring Broadband America 2025"
```

### B. MOS Score Reference

| MOS | Quality | User Perception |
|-----|---------|-----------------|
| 5 | Excellent | Imperceptible impairment |
| 4 | Good | Perceptible but not annoying |
| 3 | Fair | Slightly annoying |
| 2 | Poor | Annoying |
| 1 | Bad | Very annoying |

### C. Device Adapter Configuration Examples

#### ApplicationGateway Configuration (Generic)
```json
{
  "device_class": "vendor_sdwan",
  "api_url": "${VENDOR_API_URL}",
  "api_key": "${VENDOR_API_KEY}",
  "device_id": "device-12345",
  "consistency_delay_sec": 300
}
```

**Vendor-specific examples:**
- **Meraki**: `api_key`, `network_id`, `organization_id`
- **Viptela**: `vmanage_url`, `username`, `password`, `device_id`
- **Fortinet**: `fortigate_url`, `api_token`, `vdom`
- **Palo Alto**: `prisma_url`, `client_id`, `client_secret`

#### TR-069 Configuration
```json
{
  "adapter": "tr069",
  "acs_url": "http://genieacs:7557",
  "device_id": "CPE-001122334455"
}
```

#### Linux Router Configuration
```json
{
  "adapter": "linux_ssh",
  "host": "192.168.1.1",
  "username": "admin",
  "key_file": "/path/to/key"
}
```

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-05 | - | Initial Meraki-focused draft |
| 2.0 | 2026-02-06 | - | Restructured for generic QoE verification framework |
| 2.1 | 2026-02-06 | - | Aligned with Testbed Network Topology; Router correctly placed as ISP Gateway |
| 2.2 | 2026-02-06 | - | Network Factory moved north of Router (rtr-wan bridge) to simulate backbone conditions |
| 2.3 | 2026-02-06 | - | **Raikou as Network Factory**: tc/netem applied to veth interfaces (not OVS bridges); added multi-path topology support for SD-WAN/ApplicationGateway; proposed Raikou API extension for impairment control |
| 2.4 | 2026-02-06 | - | **Self-Hosted QoE Services**: Added detailed WAN infrastructure for deterministic testing - Streaming Container (HLS/DASH), Conferencing Container (Jitsi/WebRTC), enhanced WAN with Mock SaaS; DNS configuration for service discovery |
| 2.5 | 2026-02-06 | - | **Boardfarm Device Architecture**: Added dedicated `ApplicationGateway` template for SD-WAN/L7 devices; Router `impairment` property following existing Boardfarm patterns (`wan.firewall`); updated DUT verification to use templates instead of adapters; clarified separation between Raikou (infrastructure) and Boardfarm (device abstraction) |
| 2.6 | 2026-02-06 | - | **Vendor-Agnostic Language**: Refactored document to present `ApplicationGateway` as a generic device category with vendor implementations (Meraki, Viptela, Fortinet, Palo Alto) as examples rather than primary focus |
