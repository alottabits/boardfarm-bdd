# ADR-0001: Scope WAN Edge Testing Framework to Digital Twin (Phase 3.5)

| Field | Value |
| --- | --- |
| Status | Accepted |
| Date | 2026-03-20 |
| Deciders | req-tst team |
| Related | [architecture.md](../examples/sdwan-digital-twin/architecture.md), [testbed-configuration.md](../examples/sdwan-digital-twin/testbed-configuration.md) |

## Context

The WAN Edge Appliance Testing Framework was designed as a five-phase project to build a unified testing framework for validating commercial SD-WAN appliances (Cisco Catalyst 8000, Fortinet FortiGate, VMware SD-WAN, Palo Alto Prisma, HPE Aruba EdgeConnect). The phased plan was:

| Phase | Scope |
| :--- | :--- |
| **1 — Foundation** | Container development: Linux Router DUT, TrafficControllers, QoE Client, Application Services |
| **2 — Raikou Integration** | Dockerised testbed with OVS dual-WAN topology, Boardfarm inventory alignment |
| **3 — Validation** | End-to-end test execution: 4 pre-hardware validation scenarios, QoE baselines, failover convergence |
| **3.5 — Digital Twin Hardening** | StrongSwan IPsec, testbed CA/PKI, HTTPS/HTTP3 on application servers, WSS conferencing |
| **4 — Linux Router Expansion** | tc QoS shaping, iptables firewall, TrafficGenerator (iPerf3), MaliciousHost (Kali), Triple WAN |
| **5 — Commercial DUT Integration** | Swap Linux Router for vendor appliances; vendor-specific WANEdgeDevice drivers |

Phases 1 through 3.5 have been completed and validated. Phase 3.5 extended the Linux Router testbed with commercial-DUT-class capabilities (IPsec overlay, HTTPS, HTTP/3 QUIC), making the "digital twin" functionally representative of a real SD-WAN deployment.

At this point, the project delivered a fully operational test framework with 276 passing tests (60 unit, 22 WAN edge integration, 8 QoE impairment integration, 186 traffic control integration) across three test pillars: QoE, Path Steering, and partial Security (VPN/overlay encryption via StrongSwan).

The remaining phases (4 and 5) require either capabilities beyond the current project scope (commercial DUT hardware, vendor API access) or components with no immediate consumer (QoS contention testing, active threat emulation).

## Decision

We will scope the WAN Edge Testing Framework to the digital twin realized through Phase 3.5. Phases 4 and 5 will not be pursued at this time.

Specifically:

- **Delivered (Phases 1–3.5):** The complete framework is the final deliverable — Linux Router DUT with FRR + StrongSwan, Playwright QoE Client with HTTPS/H3 support, Application Services (Productivity, Streaming, Conferencing) with TLS, Traffic Management with dual-WAN impairment, testbed CA/PKI, and the Raikou-orchestrated Docker topology.
- **Not pursued — Phase 4 items:**
  - `TrafficGenerator` template and `IperfTrafficGenerator` device class (QoS contention background load)
  - `MaliciousHost` template and `KaliMaliciousHost` device class (active threat emulation)
  - `security_use_cases.py` composite scenarios (port scan detection, SYN flood mitigation, C2 blocking, EICAR download blocking)
  - DUT-side `tc` QoS shaping (htb, fq_codel)
  - DUT-side `iptables` zone-based firewall rules
  - Triple WAN topology expansion
  - `SpirentTrafficController` hardware appliance driver
- **Not pursued — Phase 5 items:**
  - Commercial DUT integration (vendor-specific `WANEdgeDevice` implementations)
  - Vendor REST/NETCONF API drivers

## Consequences

### Positive

- The documentation is simplified to describe the system as built, eliminating confusion between aspirational plans and realized functionality.
- The existing 276-test suite provides a validated, operational baseline for QoE, Path Steering, and VPN verification against the digital twin.
- The template-based architecture (`WANEdgeDevice`, `QoEClient`, `TrafficController`) remains intact, preserving the option to extend with commercial DUT drivers or additional components in the future without rework.
- Five implementation plan documents are replaced by concise as-built design references, reducing documentation maintenance burden.

### Negative

- The QoS (Quality of Service) and Security pillars are only partially validated. QoS contention testing (requiring `TrafficGenerator`) and active threat emulation (requiring `MaliciousHost`) remain unimplemented.
- No commercial DUT has been validated. The portability promise of the `WANEdgeDevice` template is designed but unproven against vendor hardware.

### Neutral

- The `TrafficGenerator` and `MaliciousHost` template definitions remain in the architecture documentation as designed interfaces. They can be implemented if the need arises, without redesigning the framework.
- The testbed configuration and CA setup documents are unchanged — they already describe the deployed system accurately.

## Options Considered

| Option | Pros | Cons |
| --- | --- | --- |
| Continue to Phase 5 (Commercial DUT) | Validates portability claim; tests real hardware | Requires vendor hardware procurement and API access; significant additional effort |
| Complete Phase 4 first, then decide on Phase 5 | Validates QoS and Security pillars fully | TrafficGenerator and MaliciousHost have no immediate consumer; effort spent without a DUT to test against |
| **Scope to Phase 3.5 (chosen)** | Delivers a complete, validated digital twin; documentation reflects reality; effort is focused | QoS contention and active security testing remain unvalidated; commercial portability is unproven |

## Deliverables at Phase 3.5

### Completion Evidence

**Phase 3 — Validation** *(completed 2026-03-05)*

All five exit criteria met. Test suites: `test_wan_edge_integration.py` (22 tests, 4 scenarios) and `test_qoe_impairment_integration.py` (7 tests, 2 QoE profiles + 1 degradation-detection test). Both suites passed 27 tests, 2 xfailed across three consecutive runs (~213 s per run).

| Criterion | Result | Evidence |
| :--- | :---: | :--- |
| All 4 Pre-Hardware Scenarios pass >= 3 consecutive runs | Pass | `test_wan_edge_integration.py` — 22/22 passed x 3 runs |
| QoE SLOs pass under `pristine` and `cable_typical` | Pass | `test_qoe_impairment_integration.py` — productivity + streaming pass; conferencing xfail (resolved in Phase 3.5) |
| Failover convergence baseline recorded (P50, P95 / 10 runs) | Pass | `test_failover_convergence_p50_p95_baseline_10_runs` — both P50 and P95 <= 3 000 ms |
| `get_active_wan_interface()` correct after every steering event | Pass | Verified in Scenarios 2, 3, and 4 across all failover/recovery cycles |
| No business logic in step/test definitions | Pass | All tests delegate to `use_cases/wan_edge.py`, `use_cases/qoe.py`, `use_cases/traffic_control.py` |

**Phase 3.5 — Digital Twin Hardening** *(completed 2026-03-06)*

All four exit criteria met. Full test suite: 276 tests passing.

| Criterion | Result | Evidence |
| :--- | :---: | :--- |
| StrongSwan tunnel `ESTABLISHED` | Pass | `ipsec statusall`: IKEv2 SA `ESTABLISHED` to `ipsec-hub` (172.16.0.20), ESP AES_CBC_256/HMAC_SHA2_256_128 |
| HTTPS 200 with valid TLS | Pass | `curl --cacert testbed-ca.crt https://172.16.0.10/` returns HTTP/2 200; TLSv1.3 verified |
| `QoEResult.protocol == "h3"` | Pass | Nginx 1.29.5 `--with-http_v3_module` serves QUIC on UDP:443; Chromium uses `--origin-to-force-quic-on` |
| Phase 3 scenarios pass over HTTPS | Pass | All 8 QoE tests pass (productivity HTTP + HTTPS/H3, streaming, 2x conferencing WSS) |

### Component Disposition

| Component | Realized | Status |
| :--- | :---: | :--- |
| `LinuxSDWANRouter` (FRR + StrongSwan) | Yes | Deployed — see [`linux-sdwan-router.md`](../examples/sdwan-digital-twin/linux-sdwan-router.md) |
| `PlaywrightQoEClient` (HTTPS/H3/WSS) | Yes | Deployed — see [`qoe-client.md`](../examples/sdwan-digital-twin/qoe-client.md) |
| Application Services (Productivity, Streaming, Conferencing) | Yes | Deployed — see [`application-services.md`](../examples/sdwan-digital-twin/application-services.md) |
| `LinuxTrafficController` (tc/netem) | Yes | Deployed — see [`traffic-management.md`](../examples/sdwan-digital-twin/traffic-management.md) |
| Testbed CA/PKI | Yes | Deployed — see [`testbed-ca-setup.md`](../examples/sdwan-digital-twin/testbed-ca-setup.md) |
| Raikou OVS Dual-WAN topology | Yes | Deployed — see [`testbed-configuration.md`](../examples/sdwan-digital-twin/testbed-configuration.md) |
| `IperfTrafficGenerator` | No | Descoped (Phase 4) |
| `KaliMaliciousHost` | No | Descoped (Phase 4) |
| `SpirentTrafficController` | No | Descoped (Phase 4) |
| `security_use_cases.py` | No | Descoped (Phase 4) — design in [`security-testing.md`](../examples/sdwan-digital-twin/future/security-testing.md) |
| Triple WAN topology | No | Descoped (Phase 4) |
| Commercial DUT drivers | No | Descoped (Phase 5) |

### Documentation Changes

As part of this decision, the project documentation was restructured:

| Action | Document |
| :--- | :--- |
| **Created** | `docs/adr/0001-scope-to-digital-twin-phase-3.5.md` (this document) |
| **Rewritten** (plan to as-built) | `WAN_Edge_Appliance_testing.md` → [`architecture.md`](../examples/sdwan-digital-twin/architecture.md) |
| **Rewritten** (plan to as-built) | `LinuxSDWANRouter_Implementation_Plan.md` → [`linux-sdwan-router.md`](../examples/sdwan-digital-twin/linux-sdwan-router.md) |
| **Rewritten** (plan to as-built) | `QoE_Client_Implementation_Plan.md` → [`qoe-client.md`](../examples/sdwan-digital-twin/qoe-client.md) |
| **Rewritten** (plan to as-built) | `Application_Services_Implementation_Plan.md` → [`application-services.md`](../examples/sdwan-digital-twin/application-services.md) |
| **Edited** (removed aspirational sections) | [`traffic-management.md`](../examples/sdwan-digital-twin/traffic-management.md) |
| **Implemented** (post-ADR; moved from `future/`) | [`traffic-generator.md`](../examples/sdwan-digital-twin/traffic-generator.md) |
| **Updated** (descoped; kept as design reference) | [`security-testing.md`](../examples/sdwan-digital-twin/future/security-testing.md) (MaliciousHost + security use cases) |
| **Unchanged** | [`testbed-configuration.md`](../examples/sdwan-digital-twin/testbed-configuration.md), [`testbed-ca-setup.md`](../examples/sdwan-digital-twin/testbed-ca-setup.md) |
