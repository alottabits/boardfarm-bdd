# Use Case: QoS Priority Under WAN Contention

| Field | Value |
| --- | --- |
| ID | UC-SDWAN-06 |
| Status | Draft |
| Author(s) | |
| Date | |
| Test specifications | see [Traceability](#traceability) |

## Goal

The SD-WAN appliance's QoS policy ensures that priority application traffic (e.g., conferencing marked EF/DSCP 46) maintains acceptable quality when the WAN link is saturated by best-effort background traffic.

## Scope

The contention scenario at a single-WAN branch site: the remote worker's application session, the SD-WAN appliance with QoS policy, a single WAN uplink at known bandwidth, and competing background traffic flows at varying DSCP priorities. These components form the system under consideration.

This use case differs from UC-SDWAN-02/03 which test QoE under WAN *impairment* (latency, jitter, loss from TrafficController). UC-SDWAN-06 tests QoE under *contention* from competing traffic flows at different DSCP priorities. The WAN link has healthy characteristics but is bandwidth-saturated.

## Primary Actor

Remote Worker (conducting a priority application session while background load is present)

## Stakeholders

| Stakeholder | Interest |
| --- | --- |
| Remote Worker | Expects the appliance to protect their real-time session from background bulk transfers |
| IT Operations | Needs to verify that QoS policy correctly prioritises traffic classes under saturation |
| Network Operations | Needs to understand how much background load the appliance can manage while maintaining priority traffic quality |
| Application Owner | Requires consistent conferencing/streaming quality even during peak utilisation periods |

## Level

User-goal

## Preconditions

1. The SD-WAN appliance is operational with dual WAN connectivity.
2. The network conditions are set to "cable_typical" on all WAN links (100 Mbps, 15 ms latency, 5 ms jitter, 0.1% loss).
3. Traffic generators are available on both sides of the appliance (LAN-side and north-side).
4. A conferencing server (WebRTC signalling and media) is running and reachable through the appliance.
5. The appliance's QoS policy is configured to prioritise EF-marked traffic (DSCP 46) over best-effort traffic (DSCP 0).

## Minimal Guarantees

- Every conferencing session attempt either establishes successfully and produces quality metrics (latency, jitter, packet loss, MOS) or fails explicitly.
- The MOS score is always calculated using the ITU-T G.107 E-model and falls within the defined range [1.0, 4.5].
- If the conferencing session cannot be established under contention, the remote worker receives a clear failure indication.

## Success Guarantees

1. Under upstream WAN saturation (85% link utilisation with BE traffic), the remote worker's conferencing session produces MOS >= 3.5 (acceptable quality).
2. Under downstream WAN saturation, the remote worker's conferencing session produces MOS >= 3.5.
3. Under asymmetric WAN saturation (upstream and downstream simultaneously), the remote worker's conferencing session produces MOS >= 3.5.
4. The MOS score is consistent with the measured latency, jitter, and packet loss values.

## Trigger

The remote worker needs to conduct a conferencing call while other applications and users at the branch are saturating the WAN link with bulk data transfers.

## Main Success Scenario

1. Network operations starts 85 Mbps of best-effort upstream background traffic through the appliance.
2. The remote worker starts a "conferencing" session through the appliance.
3. The remote worker confirms the "conferencing" session remains functional within the continuity SLO.
4. Network operations stops the upstream background traffic.
5. Use case succeeds.

## Extensions

- **1.a Downstream WAN Saturation**:

  1. Network operations starts 85 Mbps of best-effort downstream background traffic through the appliance.
  2. The remote worker starts a "conferencing" session through the appliance.
  3. The remote worker confirms the "conferencing" session remains functional within the continuity SLO.
  4. Network operations stops the downstream background traffic.
  5. Use case succeeds under downstream contention.

- **1.b Asymmetric WAN Saturation**:

  1. Network operations starts asymmetric background traffic with 80 Mbps upstream and 40 Mbps downstream through the appliance.
  2. The remote worker starts a "conferencing" session through the appliance.
  3. The remote worker confirms the "conferencing" session remains functional within the continuity SLO.
  4. Network operations stops all background traffic.
  5. Use case succeeds under asymmetric contention.

## Technology and Data Variations

### Background Traffic Parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| **Protocol** | UDP | Constant bitrate, predictable load |
| **DSCP (background)** | 0 (BE) | Best effort -- lowest QoS priority |
| **Target saturation** | 85% of link bandwidth | Enough to create contention without total starvation |

### DSCP Priority Classes

| Class | DSCP | Per-hop behaviour | Typical use |
|-------|------|-------------------|-------------|
| Best Effort | 0 | Default | Bulk data, web browsing |
| AF41 | 34 | Assured Forwarding | Streaming video |
| EF | 46 | Expedited Forwarding | Real-time conferencing |

### Application Type Variations Under Contention

| Application | Session type | Continuity SLO | Key metric |
|-------------|-------------|----------------|------------|
| **Conferencing** | WebRTC audio | MOS >= 3.5 | MOS score (E-model) |
| **Streaming** | HLS video | Rebuffer ratio < 5% | Startup time, rebuffer ratio |

### Link Bandwidth and Saturation

| WAN profile | Bandwidth | Saturation rate (85%) |
|-------------|-----------|----------------------|
| cable_typical | 100 Mbps | 85 Mbps |

## Traceability

| Artifact | pytest-bdd | Robot Framework |
| --- | --- | --- |
| Test specification | | |
| Step / keyword impl | `tests/step_defs/sdwan_steps.py` | |
| Use case code | `boardfarm3/use_cases/traffic_generator.py`, `boardfarm3/use_cases/qoe.py` | |

## Related Information

- This use case tests QoS under **contention** (competing traffic at different priorities). For QoE under **impairment** (latency, jitter, loss), see UC-SDWAN-02 (Remote Worker Accesses Cloud Application) and UC-SDWAN-03 (Video Conference Quality Under WAN Degradation).
- The TrafficGenerator component is independent of the TrafficController. TrafficController shapes the WAN link characteristics (latency, jitter, loss, bandwidth cap). TrafficGenerator injects competing traffic flows at specified rates and DSCP markings.
- For WAN failover under complete link failure, see UC-SDWAN-01 (WAN Failover Maintains Application Continuity).
- Background traffic uses UDP at a constant bitrate to provide a predictable, steady load. TCP-based background traffic would back off under congestion, making the saturation level unpredictable.
- Steps 2 and 3 of the main scenario and all extensions reuse the same formulations as UC-SDWAN-01/02/03, enabling step definition reuse across the test suite.
