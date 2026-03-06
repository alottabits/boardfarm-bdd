## Goal

An employee conducts a video conference call through the SD-WAN appliance with acceptable voice quality, and the conferencing quality remains within defined thresholds as WAN conditions degrade.

## Scope

The end-to-end conferencing path at a single-WAN branch site: the employee's browser (WebRTC client), the SD-WAN appliance, the single WAN uplink, and the conferencing server. These components form the system under consideration.

## Primary Actor

Employee (participant in a video conference call)

## Stakeholders

- Employee — expects clear, uninterrupted audio and video during the conference
- IT Operations — needs to verify that the SD-WAN deployment supports real-time communication
- Unified Communications Team — requires MOS baselines across deployment conditions for capacity planning
- Network Operations — needs to understand the relationship between WAN conditions and conferencing quality

## Level

user-goal

## Preconditions

1. The SD-WAN appliance is deployed at a site with a single WAN uplink. No alternative WAN path is available for failover or path steering.
2. The appliance is operational and forwarding traffic between LAN and the single WAN link.
3. The employee's device is connected on the LAN side of the appliance and has a WebRTC-capable browser available.
4. A conferencing server (WebRTC signalling and media) is running and reachable through the appliance.
5. The employee's browser trusts the conferencing server's TLS certificates (required for WSS signalling).
6. Baseline WAN conditions are nominal.

## Minimal Guarantees

- Every conferencing session attempt either establishes successfully and produces quality metrics (latency, jitter, packet loss, MOS) or fails explicitly (connection timeout, negotiation failure).
- The MOS score is always calculated using the ITU-T G.107 E-model and falls within the defined range [1.0, 4.5].
- If the conferencing session cannot be established, the employee receives a clear failure indication.
- After WAN conditions change, the system returns to its previous behaviour when nominal conditions are restored.

## Success Guarantees

1. Under nominal WAN conditions, the conferencing session produces MOS ≥ 4.0 (good quality) with round-trip latency < 50 ms and jitter < 10 ms.
2. Under typical subscriber WAN conditions, the conferencing session produces MOS ≥ 3.5 (acceptable quality).
3. Under satellite WAN conditions, the conferencing session still establishes and produces MOS ≥ 2.0 (poor but functional — media flows, session is not broken).
4. When the conferencing server is unreachable, the session fails explicitly with no hanging or ambiguous state.
5. The MOS score is consistent with the measured latency, jitter, and packet loss values.

## Trigger

The employee opens their browser, navigates to the conferencing application, and joins a conference session.

## Main Success Scenario

1. Under nominal WAN conditions, the employee joins a conference session through the SD-WAN appliance.
2. The employee's browser establishes a WebRTC session with the conferencing server.
3. The employee conducts the conference with bidirectional audio for the session duration.
4. The employee verifies that the session reports round-trip latency < 50 ms and jitter < 10 ms.
5. The employee verifies that the MOS score, derived from the session metrics using the E-model, is ≥ 4.0 (good quality).
6. The employee ends the conference and the session terminates cleanly.
7. Use case succeeds.

## Extensions

- **1.a Typical Subscriber WAN Conditions**:

  1. The WAN link exhibits typical subscriber conditions (moderate latency ~15 ms, minor jitter ~5 ms, minimal loss ~0.1%).
  2. The employee joins a conference session through the appliance.
  3. The employee conducts the conference with bidirectional audio for the session duration.
  4. The employee verifies that the MOS score is ≥ 3.5 (acceptable quality).
  5. The employee ends the conference.
  6. Use case succeeds under typical conditions.

- **1.b Satellite WAN Conditions**:

  1. The WAN link exhibits satellite conditions (very high latency ~600 ms, jitter ~50 ms, ~2% loss).
  2. The employee joins a conference session through the appliance.
  3. The employee conducts the conference with bidirectional audio for the session duration.
  4. The employee verifies that the MOS score is ≥ 2.0 (poor but functional — the call connects and media flows despite severe degradation).
  5. The employee ends the conference.
  6. Use case succeeds under satellite conditions.

- **2.a Conferencing Server Unreachable**:

  1. The employee attempts to join a conference, but the conferencing server is not reachable.
  2. The employee's browser fails to establish the WebRTC session (WSS connection timeout or ICE negotiation failure).
  3. The employee's browser reports a connection failure.
  4. Use case fails gracefully. Minimal guarantees are met.

- **5.a MOS Below Acceptable Threshold**:

  1. The employee verifies the session MOS and observes it is below the expected threshold for the current WAN conditions.
  2. The employee experiences noticeable audio quality issues (choppy audio, echo, delay).
  3. Use case fails. Minimal guarantees are met.

## Technology & Data Variations List

### WAN Condition Variations

| Condition | Latency | Jitter | Loss | Min MOS SLO | Quality Rating |
|-----------|---------|--------|------|-------------|----------------|
| **Nominal** | ~5 ms | ~1 ms | ~0% | ≥ 4.0 | Good |
| **Typical subscriber** | ~15 ms | ~5 ms | ~0.1% | ≥ 3.5 | Acceptable |
| **Satellite** | ~600 ms | ~50 ms | ~2% | ≥ 2.0 | Poor (functional) |

### MOS Score Interpretation (ITU-T G.107 E-model)

| MOS Range | Quality | User Perception |
|-----------|---------|-----------------|
| 4.0 – 4.5 | Good | Satisfied, no noticeable issues |
| 3.5 – 4.0 | Acceptable | Minor impairments, still usable |
| 3.0 – 3.5 | Poor | Noticeable quality issues |
| < 3.0 | Bad | Unusable for business communication |

### Conferencing Protocol Stack

| Layer | Protocol | Notes |
|-------|----------|-------|
| **Signalling** | WSS (WebSocket Secure) | Session establishment and negotiation |
| **Key exchange** | DTLS | Secure key exchange for media encryption |
| **Media transport** | SRTP | Encrypted real-time audio/video |
| **Connectivity** | ICE (STUN/TURN) | NAT traversal and candidate selection |

## Related Information

- This use case assumes a single-WAN deployment where no alternative path exists. For dual-WAN sites where the appliance can steer traffic to a healthier path under degradation, see UC-SDWAN-01 (WAN Failover Maintains Application Continuity).
- MOS (Mean Opinion Score) is calculated using the ITU-T G.107 E-model, which derives a quality estimate from measured network parameters (latency, jitter, packet loss) without requiring subjective human scoring.
- WebRTC provides built-in statistics (via the `RTCPeerConnection.getStats()` API) that report round-trip time, jitter, and packet loss for active media sessions.
- For real-time communication, ITU-T G.114 recommends one-way latency < 150 ms for acceptable conversational quality.
