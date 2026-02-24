# Document Improvement Checklist

**Date:** February 24, 2026  
**Status:** Planning Phase Checklist  
**Source:** Review of WAN Edge Appliance testing documentation set

This checklist captures all consistency gaps and completeness gaps identified across the six architecture/planning documents. Items are grouped by severity and type. Each item should be resolved during the planning phase before implementation begins.

---

## How to Use This Checklist

- **Consistency items** require aligning two or more existing documents to a single agreed decision.
- **Completeness items** require authoring new content (sections, diagrams, code, configs).
- Work through **High** severity items first — several will block integration (Phases 1–2).
- Check off each item (`- [x]`) when the corresponding document(s) have been updated.

---

## Reference documents

The following documents are affected:

[Boardfarm Test Automation Architecture](Boardfarm%20Test%20Automation%20Architecture.md)
[Application_Services_Implementation_Plan](Application_Services_Implementation_Plan.md)
[LinuxSDWANRouter_Implementation_Plan](LinuxSDWANRouter_Implementation_Plan.md)
[QoE_Client_Implementation_Plan](QoE_Client_Implementation_Plan.md)
[Traffic_Management_Components_Architecture](Traffic_Management_Components_Architecture.md)
[WAN_Edge_Appliance_testing](WAN_Edge_Appliance_testing.md)

---

## Section A — Consistency Gaps (Conflicts Between Documents)

### A1 — HIGH: `ThreatSimulator` vs `ThreatServer` Naming Conflict

**Affected docs:** `WAN_Edge_Appliance_testing.md`, `Application_Services_Implementation_Plan.md`

**Problem:**  
`WAN_Edge_Appliance_testing.md` defines a `ThreatSimulator` template (`boardfarm3/templates/threat_simulator.py`) with attack-generation methods (`run_port_scan`, `send_c2_callback`, `inject_syn_flood`) implemented by `KaliThreatSimulator`. The same document also references a separate `MaliciousHost` device type (WAN-side passive target) with no template definition.

`Application_Services_Implementation_Plan.md` defines a `ThreatServer` template (`boardfarm3/templates/threat_server.py`) with listener/server methods (`start_c2_listener`, `get_eicar_url`, `check_connection_received`) implemented by `KaliThreatServer`. This appears to be the WAN-side target, but the name differs from `MaliciousHost` and the file location differs from `ThreatSimulator`.

**Resolution (applied):** Single WAN-side `MaliciousHost` component. No separate LAN-side `ThreatSimulator`. The `QoEClient` fulfils the "compromised host" role for outbound C2 tests.

**Resolution required:**
- [x] Decide whether there are **two** separate components or **one** combined component → **one WAN-side `MaliciousHost`; `QoEClient` used for LAN-side outbound tests.**
- [x] Settle on canonical template names and file locations → **`MaliciousHost` at `boardfarm3/templates/malicious_host.py`.**
- [x] Define a formal `MaliciousHost` template (abstract methods, file location) → **Done in both `WAN_Edge_Appliance_testing.md` §3.4 and `Application_Services_Implementation_Plan.md` §4.**
- [x] Update both documents to use the agreed names consistently → **Done.**
- [x] Confirm canonical Kali container class name → **`KaliMaliciousHost`.**

---

### A2 — HIGH: Interface Name Translation (`eth2` vs `wan1`) — Contract Missing

**Affected docs:** `WAN_Edge_Appliance_testing.md`, `LinuxSDWANRouter_Implementation_Plan.md`

**Problem:**  
`WAN_Edge_Appliance_testing.md` expects `WANEdgeDevice.get_active_wan_interface()` to return logical names like `"wan1"`, `"wan2"` (used in `measure_failover_convergence()` as `backup_link="wan2"`).

`LinuxSDWANRouter_Implementation_Plan.md` shows the implementation parsing `ip -o route get` which returns the actual Linux interface name `"eth2"`. The Boardfarm inventory carries a mapping (`"wan_interfaces": {"wan1": "eth2", "wan2": "eth3"}`) but no document explains where and how the driver performs the `eth2` → `wan1` translation.

As written, `measure_failover_convergence()` would never match because it compares `dut.get_active_wan_interface()` (returning `"eth2"`) to `"wan2"`.

**Resolution (applied):** `get_active_wan_interface()` (and all other interface-keyed return values) always returns the **logical label** from the `wan_interfaces` inventory mapping. The `wan_interfaces` key is required for all `WANEdgeDevice` implementations.

**Resolution required:**
- [x] Document the translation contract → **logical labels always returned; documented in `WANEdgeDevice` template docstring.**
- [x] Add reverse-lookup pattern to `LinuxSDWANRouter_Implementation_Plan.md` → **`_wan_interfaces` / `_physical_to_logical` init pattern + `_to_logical()` helper added to §3.3.**
- [x] Update `WANEdgeDevice` template docstring → **Done in `WAN_Edge_Appliance_testing.md` §3.4.**
- [x] Confirm `wan_interfaces` is required → **Marked as required in both `LinuxSDWANRouter_Implementation_Plan.md` §4.1 and `WANEdgeDevice` docstring.**

---

### A3 — HIGH: `apply_policy()` Implementation — Two Different Approaches

**Affected docs:** `WAN_Edge_Appliance_testing.md`, `LinuxSDWANRouter_Implementation_Plan.md`

**Problem:**  
`WAN_Edge_Appliance_testing.md` Section 4.3 proxy mapping table states `apply_policy()` is implemented by writing FRR PBR rules via `vtysh`.

`LinuxSDWANRouter_Implementation_Plan.md` Section 3.2.5 implements `apply_policy()` using Linux kernel PBR: `ip rule add`, `ip route add ... table <N>`, and `/etc/iproute2/rt_tables`. No FRR `vtysh` is used.

These are different control-plane mechanisms and produce different system state.

**Resolution (applied):** FRR vtysh route-maps are canonical. Direct kernel ip-rule is incorrect because FRR owns the routing table and would overwrite manually injected kernel rules. Using vtysh also correctly mirrors how commercial DUTs accept policy via their management interface (REST/NETCONF → control plane → forwarding plane).

**Resolution required:**
- [x] Decide which mechanism is canonical → **FRR vtysh route-maps.**
- [x] Update `LinuxSDWANRouter_Implementation_Plan.md` §3.3 method 5 to use FRR vtysh route-map commands → **Done; includes rationale, vtysh command sequence, and cleanup procedure.**
- [x] Document cleanup/rollback procedure → **Done: `no route-map <name>` + `no ip access-list <name>` via vtysh before each apply.**
- [x] `WAN_Edge_Appliance_testing.md` proxy mapping table → **Already correct (stated vtysh); no change needed.**

---

### A4 — MEDIUM: `get_wan_path_metrics()` — FRR vtysh vs ping

**Affected docs:** `WAN_Edge_Appliance_testing.md`, `LinuxSDWANRouter_Implementation_Plan.md`

**Problem:**  
`WAN_Edge_Appliance_testing.md` Section 3.4 proxy mapping table states `get_wan_path_metrics()` is implemented via `FRR vtysh -c "show ip nexthop" + custom BFD probe`.

`LinuxSDWANRouter_Implementation_Plan.md` Section 3.2.2 implements it using `ping -c 5 -i 0.2 <gateway>` to measure latency, jitter (mdev), and loss. FRR vtysh is not mentioned for metrics.

**Resolution (applied):** Ping is correct. FRR has no built-in SLA prober that produces numeric latency/jitter/loss values — `show ip nexthop` gives reachability state only, not quality metrics. Ping is the functional proxy for the built-in SLA probers found in commercial SD-WAN DUTs. The WAN_Edge proxy table was corrected (as part of A2 update) and the stray §2.3 note has been fixed to distinguish `get_active_wan_interface()` (ip route) from `get_wan_path_metrics()` (ping probes). The `LinuxSDWANRouter_Implementation_Plan.md` ping approach required no change.

**Resolution required:**
- [x] Clarify whether `ping` is intended to be the "custom probe" → **Yes. Ping is the correct approach; FRR vtysh produces no numeric quality metrics.**
- [x] Update the WAN_Edge proxy mapping table → **Already corrected during A2 update to show ping-based approach.**
- [x] Fix stray §2.3 note in `WAN_Edge_Appliance_testing.md` → **Done: note now distinguishes `get_active_wan_interface()` (ip route) from `get_wan_path_metrics()` (ping probes).**
- [x] State whether BFD is used for Phase 1/2 → **Not needed for metrics; BFD is a separate concern for failover detection (see B9).**

---

### A5 — MEDIUM: `get_impairment_profile()` — In-Memory vs Parsed from `tc qdisc show`

**Affected docs:** `WAN_Edge_Appliance_testing.md`, `Traffic_Management_Components_Architecture.md`

**Problem:**  
`WAN_Edge_Appliance_testing.md` Section 4.4 and Phase 1 exit criteria explicitly require: *"parsed from `tc qdisc show` output (not from in-memory state) to ensure round-trip fidelity."*

`Traffic_Management_Components_Architecture.md` Section 6.3 (`LinuxTrafficControlAdapter`) implements `get_impairment_profile()` returning `self._current` — in-memory state. The standalone `LinuxTrafficController.get_impairment_profile()` body is shown as `...` (not specified).

**Resolution (applied):** The WAN Edge testbed uses **only standalone dedicated impairment containers** — one `LinuxTrafficController` per WAN link in the functional testbed, and `SpirentTrafficController` in pre-production. There is no co-hosted impairment pattern in this testbed, so `LinuxTrafficControlAdapter` and the `LinuxISPGateway` composition model have been removed from the architecture document entirely.

`LinuxTrafficController.get_impairment_profile()` parses `tc -j qdisc show dev <iface>` on every call (kernel state, not memory). `set_impairment_profile()` intentionally omits `self._current` assignment. Full parsing implementation and `tc -j qdisc show` JSON field mapping are documented in `Traffic_Management_Components_Architecture.md` Section 7.1.

**Resolution required:**
- [x] Specify `LinuxTrafficController.get_impairment_profile()` → **Done: full `tc -j qdisc show` parsing implementation documented in Section 7.1.**
- [x] Decide on `LinuxTrafficControlAdapter` → **Removed. Not relevant to this testbed; only standalone devices are used.**
- [x] Document `tc qdisc show` parsing logic → **Done: JSON field mapping table and example output added to Section 7.1.**

---

### A6 — MEDIUM: Conferencing Server Technology — Three Documents Disagree

**Affected docs:** `WAN_Edge_Appliance_testing.md`, `Application_Services_Implementation_Plan.md`, `QoE_Client_Implementation_Plan.md`

**Problem:**  
- `WAN_Edge_Appliance_testing.md` Section 4.4: *"Self-hosted Jitsi Meet + Coturn (STUN/TURN) setup."*
- `Application_Services_Implementation_Plan.md` Section 3.3: Recommends *"WebRTC Echo"* using `pion`, explicitly over a full Jitsi installation.
- `QoE_Client_Implementation_Plan.md` Section 4: *"A WebRTC echo server or Jitsi instance"* — leaves it open.

**Resolution (applied):** **WebRTC Echo server** (`pion`-based container) is the selected implementation. No Coturn STUN/TURN is required — the fully controlled testbed network guarantees direct peer connectivity. All three documents have been updated:
- `WAN_Edge_Appliance_testing.md` §4.4: replaced "Jitsi Meet + Coturn" with "WebRTC Echo server (`pion`-based)".
- `Application_Services_Implementation_Plan.md` §3.3: removed option framing, stated decision directly; updated Docker networking from port 3478 (STUN/TURN) to 8443 (WebRTC signalling); updated `ConferencingServer` docstring example URL.
- `QoE_Client_Implementation_Plan.md` §3 and §4: replaced "Jitsi Meet or synthetic WebRTC test page" with the definitive `pion`-based WebRTC Echo server reference.

**Resolution required:**
- [x] Decision: **WebRTC Echo server (`pion`-based)** — no Jitsi, no Coturn.
- [x] All three documents updated to state the same choice.
- [x] Jitsi references removed from `WAN_Edge_Appliance_testing.md`.
- [x] STUN/TURN port (3478) removed; replaced with WebRTC signalling port (8443).

---

### A7 — MEDIUM: Server-Side Templates Missing from WAN_Edge Template Section

**Affected docs:** `WAN_Edge_Appliance_testing.md`, `Application_Services_Implementation_Plan.md`

**Problem:**  
`WAN_Edge_Appliance_testing.md` Section 3.4 lists four Boardfarm templates. `Application_Services_Implementation_Plan.md` defines three additional templates — `ProductivityServer`, `StreamingServer`, `ConferencingServer` — that QoE tests depend on. These are absent from the WAN_Edge template catalogue.

**Resolution (applied):** `ProductivityServer`, `StreamingServer`, and `ConferencingServer` templates have been added to `WAN_Edge_Appliance_testing.md` Section 3.4, each with their file location, brief description, abstract interface, and a cross-reference to `Application_Services_Implementation_Plan.md`. `MaliciousHost` was already present in Section 3.4 (resolved as part of A1).

**Resolution required:**
- [x] Add `ProductivityServer`, `StreamingServer`, `ConferencingServer` to WAN_Edge §3.4 → **Done.**
- [x] Add `MaliciousHost` → **Already present (A1 resolution).**

---

### A8 — MEDIUM: Phase Numbering — Component Phases vs Project Phases Not Cross-Referenced

**Affected docs:** `WAN_Edge_Appliance_testing.md`, `QoE_Client_Implementation_Plan.md`, `LinuxSDWANRouter_Implementation_Plan.md`, `Application_Services_Implementation_Plan.md`

**Problem:**  
Each component implementation plan uses internal phase numbering (Phase 1–4) while `WAN_Edge_Appliance_testing.md` defines project-level phases (Phase 1–5). There is no cross-reference mapping, e.g., "QoE Client Phase 1–3 complete within WAN_Edge Project Phase 1."

A reader cannot determine how component milestones map to project milestones or what must be done in parallel vs sequentially.

**Resolution (applied):** Component plans keep their internal phase numbering (renaming would break internal readability). Cross-references added in two places:

1. **`WAN_Edge_Appliance_testing.md` §5**: A "Component Readiness Map" table added before the numbered phase list, showing which component plan phases must be complete at each project phase gate.
2. **Each component plan's Development Phases section**: Each phase entry annotated with `*(Project Phase X — Name)*`. A callout block also links back to the Readiness Map.
3. **`Traffic_Management_Components_Architecture.md` §7**: Added a project phase alignment note (no separate development phases section exists in this doc).

**Resolution required:**
- [x] Add mapping table → **Done in `WAN_Edge_Appliance_testing.md` §5 (Component Readiness Map).**
- [x] Annotate component phases → **Done in all three component plans.**

---

### A9 — LOW: `congested` Profile Bandwidth — `0` vs `None` Semantic Ambiguity

**Affected docs:** `WAN_Edge_Appliance_testing.md`, `Traffic_Management_Components_Architecture.md`

**Problem:**  
The `ImpairmentProfile` schema uses `None or 0 = no limit / variable` for `bandwidth_mbps`. The `congested` preset uses `bandwidth_mbps: 0`. The value `0` intuitively means "zero bandwidth" (blocked), not "variable/unlimited." This could cause developer confusion.

**Resolution (applied):** Two improvements made together:
1. **Field renamed** `bandwidth_mbps` → `bandwidth_limit_mbps` (and `egress_bandwidth_mbps` / `ingress_bandwidth_mbps` accordingly). The `_limit_` infix makes it self-documenting as a cap, not a measurement.
2. **`None` is now the sole "no limit" sentinel.** `0` is no longer a valid "no limit" value. The `congested` preset changed from `"bandwidth_limit_mbps": 0` to `"bandwidth_limit_mbps": null`. The `profile_from_dict` parser no longer uses `or 0`; it passes `None` directly from the JSON.
3. **Bonus fix:** The `tc qdisc show` parser had a unit conversion bug — it divided by 1000 (bps → kbps) but the field stores Mbps. Fixed to divide by 1,000,000.

**Resolution required:**
- [x] Rename field and eliminate `0` as "no limit" → **Done: `bandwidth_limit_mbps` with `None` only.**
- [x] Update `congested` preset → **Done: `null` in JSON / `None` in Python.**
- [x] Update canonical preset table in WAN_Edge §2.1 → **Table column already showed "Variable" for `congested`; field name updated in dataclass copy in §4.5.**

---

### A10 — LOW: `security_artifacts/` Directory Not in Architecture Document

**Affected docs:** `WAN_Edge_Appliance_testing.md`, `Boardfarm Test Automation Architecture.md`

**Problem:**  
`WAN_Edge_Appliance_testing.md` Section 2.4 specifies EICAR/PCAP/C2 files should be stored in `bf_config/security_artifacts/`. The Architecture document's Test Artifacts section only defines `bf_config/gui_artifacts/` and `tests/test_artifacts/`. The `security_artifacts/` convention is not anchored in the reference architecture.

**Resolution (applied):** `bf_config/security_artifacts/` added to the Architecture document's Test Artifacts section with a directory listing, a "Security Example" subsection (parallel to the existing GUI Example), and a new row in the decision table: "Security test payloads (EICAR, PCAP, C2 configs)" → `bf_config/security_artifacts/`.

**Resolution required:**
- [x] Add `bf_config/security_artifacts/` to Architecture doc Test Artifacts → **Done.**
- [x] Add row to decision table → **Done.**

---

### A11 — LOW: Architecture Document Not Updated for SD-WAN Modules

**Affected docs:** `Boardfarm Test Automation Architecture.md`

**Problem:**  
The `use_cases Module Reference` table lists legacy modules (`acs.py`, `cpe.py`, `voice.py`, etc.) but none of the new SD-WAN modules: `qoe.py`, `wan_edge.py`, `traffic_control.py`, `threat_use_cases.py`, `security_use_cases.py`. The document footer states `Implementation Status: ✅ Complete` (January 26, 2026) which predates the SD-WAN work.

**Resolution (applied):**
- `use_cases Module Reference` table split into "Legacy Modules" and "SD-WAN Modules (in development)" with all five SD-WAN modules added with key functions.
- Templates section updated: SD-WAN templates listed as a separate group with file locations and a cross-reference to `WAN_Edge_Appliance_testing.md §3.4`.
- Implementation Status footer updated to "Legacy complete · SD-WAN modules in development" with link to Component Readiness Map. Document version bumped to 1.3.

**Resolution required:**
- [x] Add SD-WAN use_cases modules to module reference table → **Done (5 modules).**
- [x] Add SD-WAN templates to Templates section → **Done (8 templates).**
- [x] Update Implementation Status footer → **Done.**

---

## Section B — Completeness Gaps (Missing Content)

### B1 — HIGH: `inject_transient()` Restoration Mechanism — Not Specified

**Affected docs:** `Traffic_Management_Components_Architecture.md`

**Problem:**  
The `TrafficController.inject_transient()` template method and its use-case wrappers (`inject_blackout`, `inject_brownout`, etc.) are defined, but **no document describes how and when the link state is restored** after `duration_ms` expires. Options include: background thread with sleep+restore, `tc netem limit` with packet count, or a scheduled OS timer. Without this, the failover convergence measurement (which injects a blackout then polls for recovery) may produce undefined behavior.

**Resolution (applied):** Section 7.3 added to `Traffic_Management_Components_Architecture.md` specifying:
- **Fire-and-forget contract**: `inject_transient()` returns immediately; automatic restoration after `duration_ms` — caller never restores state.
- **`LinuxTrafficController` implementation**: daemon background thread using `threading.Event.wait(timeout)` + `set_profile_via_tc(previous)` on expiry. Previous state read from kernel via `get_impairment_profile()` at injection time.
- **Cancellation mechanism**: `_cancel_restore()` helper called at entry of `inject_transient()`, `set_impairment_profile()`, and `clear()` — explicit calls always win.
- **`_build_transient_profile()` helper**: event-type-to-profile mapping table documented.
- **`SpirentTrafficController`**: delegates to native Spirent timed-event API — no thread needed.
- **Thread-safety table**: all concurrent-access scenarios documented.

**Resolution required:**
- [x] Specify restoration mechanism → **Done: fire-and-forget, background daemon thread.**
- [x] Specify caller responsibility → **None — fully automatic.**
- [x] Document thread-safety → **Done: cancellation-event pattern documented.**
- [x] Specify interaction with `set_impairment_profile()` → **Done: explicit call cancels pending restore.**

---

### B2 — HIGH: `MaliciousHost` Template — Formal Definition Missing

**Affected docs:** `WAN_Edge_Appliance_testing.md`, `Application_Services_Implementation_Plan.md`

**Problem:**  
`WAN_Edge_Appliance_testing.md` references `MaliciousHost` as a Boardfarm device type in Sections 2.4 and 4.4. No template definition exists: no abstract methods, no file location, no implementation class name. The `Application_Services_Implementation_Plan.md` `ThreatServer` covers part of this role but uses a different name.

**Resolution (applied):** Resolved as part of A1 and A7. The full `MaliciousHost` template (`boardfarm3/templates/malicious_host.py`) was defined with:
- `ScanResult` dataclass
- Active inbound attack methods: `run_port_scan()`, `inject_syn_flood()`
- Passive threat service methods: `start_c2_listener()`, `stop_c2_listener()`, `check_connection_received()`, `get_eicar_url()`
- `KaliMaliciousHost` implementation notes

Template definition added to both `WAN_Edge_Appliance_testing.md` §3.4 and `Application_Services_Implementation_Plan.md` §4.

**Resolution required:**
- [x] Define canonical `MaliciousHost` template → **Done in `WAN_Edge_Appliance_testing.md` §3.4 and `Application_Services_Implementation_Plan.md` §4.**

---

### B3 — HIGH: `TrafficGenerator` — No Implementation Plan Document

**Affected docs:** `WAN_Edge_Appliance_testing.md`

**Problem:**  
`WAN_Edge_Appliance_testing.md` defines the `TrafficGenerator` template and specifies "Implement `IperfTrafficGenerator` device class." Implementation plans exist for the Linux Router, QoE Client, Application Services, and Traffic Controller, but there is **no `TrafficGenerator_Implementation_Plan.md`**.

Missing specifics:
- Container base image and required packages
- Where iPerf3 server runs (same container as the QoE client? Separate container? On the service side?)
- How DSCP marking is set in iPerf3 to test QoS priority queues
- How `start_traffic()` / `stop_traffic()` async model is implemented

**Resolution required:**
- [ ] Create `TrafficGenerator_Implementation_Plan.md` covering: container spec, iPerf3 server placement, DSCP marking, async traffic model, and integration into Raikou topology.

---

### B4 — HIGH: `threat_use_cases.py` and `security_use_cases.py` — Never Defined

**Affected docs:** `WAN_Edge_Appliance_testing.md`

**Problem:**  
These use-case modules are referenced across multiple sections but no function signatures, descriptions, or contracts are provided. Referenced functions include:
- `threat_use_cases.run_port_scan()`
- `threat_use_cases.send_c2_callback()`
- `threat_use_cases.inject_syn_flood()`
- `security_use_cases.assert_traffic_blocked()`
- `security_use_cases.assert_download_blocked()`

Compare with `qoe.py` and `wan_edge.py`, which have full code examples with docstrings in the Technical Brief.

**Resolution required:**
- [ ] Add a Section to `WAN_Edge_Appliance_testing.md` (or a new `Security_UseCase_Design.md`) defining function signatures and docstrings for all security/threat use-case functions, following the same pattern as Section 3.5 (QoE) and Section 3.6 (Failover Convergence).

---

### B5 — HIGH: Security Pillar — No Quantitative SLOs or Pass/Fail Thresholds

**Affected docs:** `WAN_Edge_Appliance_testing.md`

**Problem:**  
The QoE pillar defines precise, measurable SLOs (page load < 2.5s/4s; MOS > 4.0/3.5; rebuffer < 1%; latency < 150ms). The Security pillar (Section 2.4) has no equivalent thresholds. Without these, tests cannot have deterministic pass/fail criteria.

Missing thresholds for:
- Maximum throughput reduction from enabling IPS/SSL Inspection (e.g., < 20% degradation)
- Port scan detection time (e.g., DUT logs event within 5s)
- SYN flood: packet rate that triggers rate-limiting (e.g., > 1000 SYN/s)
- C2 callback block rate (e.g., 100% of attempts must be blocked)
- EICAR download: must be blocked within 1 connection attempt

**Resolution required:**
- [ ] Add a Security SLO table to Section 2.4 of `WAN_Edge_Appliance_testing.md`, mirroring the format of the QoE metrics table in Section 2.1.

---

### B6 — HIGH: Raikou / Docker Compose Configuration — Not Provided

**Affected docs:** All implementation plan documents

**Problem:**  
Every implementation plan and the project phasing reference Raikou and Docker Compose as the testbed instantiation mechanism, but no example `docker-compose.yaml`, OVS bridge setup, or Raikou-specific configuration file is provided anywhere. Phase 2 of WAN_Edge says "Create Docker Compose for Raikou with Dual WAN topology; Configure OVS bridges" but gives no starting template.

**Resolution required:**
- [ ] Add an annotated reference `docker-compose.yaml` (or Raikou equivalent) covering all PoC containers: Linux Router DUT, WAN1 TrafficController, WAN2 TrafficController, Application Server, QoE Client.
- [ ] Document the OVS bridge topology: bridge names, port assignments, interface wiring between containers.
- [ ] This can be a new `Raikou_Topology_Configuration.md` document or an appendix to `WAN_Edge_Appliance_testing.md`.

---

### B7 — HIGH: Interface Name Translation Contract — Implementation Missing

*(Closely related to A2; resolved together with A2.)*

**Affected docs:** `LinuxSDWANRouter_Implementation_Plan.md`

**Problem:**  
Even once A2 is resolved in documentation, `LinuxSDWANRouter_Implementation_Plan.md` must be updated to include the actual code pattern for reading `wan_interfaces` from the merged config and using it in `get_active_wan_interface()`.

**Resolution (applied as part of A2):**

**Resolution required:**
- [x] Add a code snippet showing `self._wan_interfaces` init and reverse mapping → **`__init__` + `_to_logical()` pattern added to `LinuxSDWANRouter_Implementation_Plan.md` §3.3.**
- [x] Show how `eth2` → `"wan1"` translation works in `get_active_wan_interface()` → **Done with annotated example in §3.3 method 1.**

---

### B8 — MEDIUM: `wan_edge_use_cases.py` — Path Assertion Functions Undefined

**Affected docs:** `WAN_Edge_Appliance_testing.md`

**Problem:**  
Section 5 Phase 1 says "Develop `use_cases/wan_edge.py` (path assertions, failover convergence)" and Section 4.3 Pre-Hardware Validation Scenarios reference path assertions, but only `measure_failover_convergence()` is defined in the document. Functions like `assert_traffic_on_interface()` and `assert_path_steering_for_application()` are implied but never specified.

**Resolution required:**
- [ ] Define the remaining `use_cases/wan_edge.py` function signatures with docstrings in `WAN_Edge_Appliance_testing.md`, covering at minimum: path assertion after impairment, path assertion for policy-steered traffic, and interface status verification.

---

### B9 — MEDIUM: BFD Configuration — Incomplete in Linux Router Plan

**Affected docs:** `LinuxSDWANRouter_Implementation_Plan.md`, `WAN_Edge_Appliance_testing.md`

**Problem:**  
`WAN_Edge_Appliance_testing.md` repeatedly references BFD as the mechanism for sub-second failover detection. `LinuxSDWANRouter_Implementation_Plan.md` mentions BFD only in a code comment (`! Health check via static route tracking or BFD`) but provides no actual BFD configuration: peer IP addresses, detection multiplier, interval, minimum Rx/Tx intervals, or the FRR vtysh config stanza. Without BFD configuration, the Linux router cannot achieve the sub-second detection times asserted by `measure_failover_convergence()`.

**Resolution required:**
- [ ] Add a BFD configuration sub-section to `LinuxSDWANRouter_Implementation_Plan.md` Section 3.2 with: a sample FRR BFD peer config, recommended timers for sub-second detection (e.g., 100ms interval × 3 = 300ms detection), and integration with nexthop tracking.
- [ ] Clarify in `WAN_Edge_Appliance_testing.md` whether BFD is required for Phase 1/2 or deferred.

---

### B10 — MEDIUM: Test Teardown and Reset Between Tests — Not Addressed

**Affected docs:** All

**Problem:**  
No document addresses:
- How impairments are cleared if a test fails mid-execution
- Whether `TrafficController.clear()` is called in a pytest fixture teardown/finalizer
- How FRR policy rules applied via `apply_policy()` are cleaned up between scenarios
- Whether the testbed returns to a known initial state before each test

This is especially critical for the failover convergence test where an injected blackout could persist into the next scenario if cleanup fails.

**Resolution required:**
- [ ] Add a "Testbed Reset" or "Teardown Strategy" section to `WAN_Edge_Appliance_testing.md` specifying:
  - Which fixtures are responsible for cleanup (`autouse` teardown fixtures)
  - The reset sequence: clear impairments → restore default profile → flush PBR rules → verify baseline connectivity
- [ ] Add a note in `Traffic_Management_Components_Architecture.md` that `clear()` should be called in fixture teardown.

---

### B11 — MEDIUM: Network Addressing Scheme — Not Defined

**Affected docs:** All implementation plan documents

**Problem:**  
No document defines the IP addressing plan for the testbed. The Boardfarm inventory snippet shows `172.20.0.10` for the DUT but LAN subnets, WAN1/WAN2 transit subnets, service IP ranges, management network, and gateway addresses are unspecified. These are needed for FRR configuration, Docker Compose networking, PBR rules, and test assertions.

**Resolution required:**
- [ ] Add a network addressing table to `WAN_Edge_Appliance_testing.md` or the forthcoming Raikou topology document (B6), covering:
  - Management network (Docker bridge for SSH access)
  - LAN segment (DUT eth1 ↔ clients)
  - WAN1 transit segment (DUT eth2 ↔ WAN1 TrafficController ↔ services)
  - WAN2 transit segment (DUT eth3 ↔ WAN2 TrafficController ↔ services)
  - Service subnet (North-side application servers)

---

### B12 — MEDIUM: HTTP/3 (QUIC) Measurement — Not Addressed in QoE Client Plan

**Affected docs:** `Application_Services_Implementation_Plan.md`, `QoE_Client_Implementation_Plan.md`

**Problem:**  
`Application_Services_Implementation_Plan.md` Section 3.1 states the productivity server enables HTTP/3 (QUIC). The `QoE_Client_Implementation_Plan.md` does not address how to verify QUIC negotiation occurred or how QUIC-specific metrics differ from HTTP/2. Playwright supports HTTP/3 but the implementation plan is silent on this.

**Resolution required:**
- [ ] Add a note to `QoE_Client_Implementation_Plan.md` Section 3.2.1 specifying whether QUIC is tested and, if so, how protocol negotiation is verified (e.g., check `performance.getEntriesByType('navigation')[0].nextHopProtocol`).
- [ ] Decide whether `QoEResult` needs a `protocol` field to record which HTTP version was used.

---

### B13 — MEDIUM: Streaming Content Pipeline — Underspecified

**Affected docs:** `Application_Services_Implementation_Plan.md`

**Problem:**  
The streaming service mentions "Big Buck Bunny" as a test asset and a multi-bitrate ladder (360p, 720p, 1080p, 4K) but does not specify:
- How video segments are pre-transcoded (FFmpeg command? Pre-built asset download?)
- What the resulting container image size will be (4K segments are large)
- Whether segments are bundled in the image or mounted at runtime
- The exact HLS segment duration and playlist structure

**Resolution required:**
- [ ] Add a streaming content sub-section to `Application_Services_Implementation_Plan.md` Section 3.2 covering: transcoding tool and commands (or source of pre-built assets), bitrate ladder specification (bitrate + resolution per profile), HLS segment duration, and whether content is baked into the Docker image or volume-mounted.

---

### B14 — LOW: `Application_Services_Implementation_Plan.md` Missing Section 5

**Affected docs:** `Application_Services_Implementation_Plan.md`

**Problem:**  
Section numbering jumps from Section 4 to Section 6. Section 5 is missing — either it was removed and numbering was not updated, or content was accidentally deleted.

**Resolution required:**
- [ ] Determine what Section 5 was intended to cover (possibly "Service Configuration Details" or "Boardfarm Integration") and either write it or renumber Sections 6 and 7 to 5 and 6.

---

### B15 — LOW: Conferencing Server — STUN/TURN Configuration Not Covered

**Affected docs:** `Application_Services_Implementation_Plan.md`

**Problem:**  
WebRTC requires STUN/TURN servers to establish peer connections, especially when the client and server are on different network segments (as in this testbed). If Jitsi is chosen (per A6), Coturn is needed. If a WebRTC echo server is chosen, it still needs STUN configuration. Neither scenario is specified.

**Resolution required:**
- [ ] After resolving A6 (conferencing server choice), add STUN/TURN configuration requirements to `Application_Services_Implementation_Plan.md`: whether Coturn runs as a separate container, its IP/port, and how Playwright is configured to use it.

---

### B16 — LOW: Server-Side Session Metrics Correlation — No Use Case Defined

**Affected docs:** `Application_Services_Implementation_Plan.md`, `QoE_Client_Implementation_Plan.md`

**Problem:**  
`Application_Services_Implementation_Plan.md` `ConferencingServer` template includes `get_session_stats()` to return server-side RTCP metrics (packet loss, jitter). However, no use-case function is defined to correlate client-side `getStats()` data with server-side RTCP metrics. This correlation capability is mentioned in Application_Services but absent from the QoE use-case design.

**Resolution required:**
- [ ] Define (or explicitly defer) a `qoe_use_cases.correlate_conferencing_metrics(client_result, server_stats)` function, specifying what it checks and when it would be used.

---

## Summary by Priority

| ID  | Severity | Type        | Short Description |
|-----|----------|-------------|-------------------|
| A1  | ~~HIGH~~ | ~~Consistency~~ | ~~`ThreatSimulator` vs `ThreatServer` naming conflict~~ — **RESOLVED** |
| A2  | ~~HIGH~~ | ~~Consistency~~ | ~~`eth2` vs `wan1` interface name translation missing~~ — **RESOLVED** |
| A3  | ~~HIGH~~ | ~~Consistency~~ | ~~`apply_policy()`: vtysh vs ip-rule approaches differ~~ — **RESOLVED** |
| B1  | ~~HIGH~~ | ~~Completeness~~ | ~~`inject_transient()` restoration mechanism undefined~~ — **RESOLVED** |
| B2  | ~~HIGH~~ | ~~Completeness~~ | ~~`MaliciousHost` template formally undefined~~ — **RESOLVED** (as part of A1/A7) |
| B3  | HIGH     | Completeness | No implementation plan for `TrafficGenerator` |
| B4  | HIGH     | Completeness | `threat_use_cases.py` / `security_use_cases.py` undefined |
| B5  | HIGH     | Completeness | Security pillar has no quantitative SLOs |
| B6  | HIGH     | Completeness | No Raikou / Docker Compose example configuration |
| B7  | ~~HIGH~~ | ~~Completeness~~ | ~~Interface translation code pattern missing from router plan~~ — **RESOLVED** |
| A4  | ~~MEDIUM~~ | ~~Consistency~~ | ~~`get_wan_path_metrics()`: vtysh vs ping approach differs~~ — **RESOLVED** |
| A5  | ~~MEDIUM~~ | ~~Consistency~~ | ~~`get_impairment_profile()`: in-memory vs tc-parsed~~ — **RESOLVED** |
| A6  | ~~MEDIUM~~ | ~~Consistency~~ | ~~Conferencing server: Jitsi vs WebRTC Echo — three docs differ~~ — **RESOLVED** |
| A7  | ~~MEDIUM~~ | ~~Consistency~~ | ~~Server-side templates absent from WAN_Edge §3.4~~ — **RESOLVED** |
| A8  | ~~MEDIUM~~ | ~~Consistency~~ | ~~Component phase numbering not mapped to project phases~~ — **RESOLVED** |
| B8  | MEDIUM   | Completeness | `wan_edge_use_cases.py` path assertion functions undefined |
| B9  | MEDIUM   | Completeness | BFD configuration incomplete in Linux router plan |
| B10 | MEDIUM   | Completeness | Test teardown / testbed reset strategy not addressed |
| B11 | MEDIUM   | Completeness | Network addressing scheme not defined |
| B12 | MEDIUM   | Completeness | HTTP/3 (QUIC) measurement not in QoE client plan |
| B13 | MEDIUM   | Completeness | Streaming content pipeline underspecified |
| A9  | ~~LOW~~ | ~~Consistency~~ | ~~`congested` bandwidth: `0` vs `None` semantic ambiguity~~ — **RESOLVED** |
| A10 | ~~LOW~~ | ~~Consistency~~ | ~~`security_artifacts/` missing from Architecture doc~~ — **RESOLVED** |
| A11 | ~~LOW~~ | ~~Consistency~~ | ~~Architecture doc not updated for SD-WAN modules~~ — **RESOLVED** |
| B14 | LOW      | Completeness | Missing Section 5 in Application_Services doc |
| B15 | LOW      | Completeness | STUN/TURN configuration not covered |
| B16 | LOW      | Completeness | Server-side conferencing metrics correlation undefined |

---

*Total: 8 HIGH items (7 consistency + additional completeness), 10 MEDIUM items, 6 LOW items — 27 items total.*
