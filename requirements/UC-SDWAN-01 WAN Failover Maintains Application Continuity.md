## Goal

When the primary WAN link fails, the SD-WAN appliance automatically detects the failure and fails over to a backup WAN link, maintaining application continuity for the end user throughout the transition.

## Scope

The SD-WAN appliance with dual WAN connectivity and the LAN-side user's application session. The appliance, its WAN links, and the application delivery path form the system under consideration.

## Primary Actor

Remote Worker (end user accessing applications through the SD-WAN appliance)

## Stakeholders

- Remote Worker — expects uninterrupted application access during WAN events
- Network Operations — needs confidence that failover is automatic and convergence is fast
- Application Owner — requires SLA compliance even during link failures
- SD-WAN Appliance — must detect failure and converge to backup path

## Level

user-goal

## Preconditions

1. The SD-WAN appliance is operational with two WAN links (WAN1 and WAN2) in UP state.
2. WAN1 is the primary (preferred) path with a lower routing metric than WAN2.
3. Application services are reachable from the LAN side via both WAN paths through the appliance.
4. The remote worker has an active application session through the appliance.
5. Baseline network conditions are nominal (minimal latency, no packet loss on either link).

## Minimal Guarantees

- The SD-WAN appliance does not enter an indeterminate routing state (both links down, routing loop, or split-brain).
- After recovery of a failed link, both WAN links return to UP state and the appliance resumes its baseline routing configuration.
- The remote worker's traffic is never silently black-holed; it is either forwarded via an available link or the connection fails explicitly.

## Success Guarantees

1. When WAN1 fails, the appliance detects the failure and switches forwarding to WAN2 within the convergence SLO (< 1000 ms).
2. After failover, WAN2 is the active forwarding path for LAN-to-WAN traffic.
3. The remote worker's application session remains functional after failover — the productivity application loads successfully with TTFB < 200 ms via the backup path.
4. When WAN1 recovers, the appliance fails back to WAN1 as the preferred path.
5. After failback, WAN1 is again the active forwarding path.

## Trigger

The primary WAN link (WAN1) experiences a complete link failure (blackout).

## Main Success Scenario

1. The remote worker verifies that both WAN links are UP and that WAN1 is the active forwarding path.
2. The remote worker accesses a productivity application through the appliance and confirms the application loads successfully over WAN1.
3. WAN1 experiences a complete link failure (100% packet loss).
4. The appliance detects the WAN1 failure and converges routing to WAN2 within the convergence SLO.
5. The remote worker verifies that WAN2 is now the active forwarding path.
6. The remote worker accesses the same productivity application and confirms it loads successfully over WAN2 with TTFB < 200 ms.
7. WAN1 recovers and returns to healthy state.
8. The appliance detects WAN1 recovery and fails back to WAN1 as the preferred path.
9. The remote worker verifies that WAN1 is again the active forwarding path.
10. The remote worker verifies that both WAN links are UP. Use case succeeds.

## Extensions

- **3.a Degradation Instead of Blackout (Quality-Triggered Failover)**:

  1. WAN1 experiences degraded conditions (elevated latency, jitter, and packet loss consistent with a congested or unstable link).
  2. The appliance detects that WAN1 quality has dropped below the configured SLA threshold and steers traffic to WAN2.
  3. The remote worker verifies that WAN2 is the active forwarding path.
  4. The remote worker accesses the productivity application and confirms it remains accessible.
  5. Continue from step 7 of the main scenario.

- **4.a Convergence Exceeds SLO**:

  1. The appliance does not converge routing to WAN2 within the convergence SLO (1000 ms).
  2. The remote worker observes the application session is disrupted for longer than acceptable.
  3. Use case fails. Minimal guarantees are met.

- **6.a Application Unreachable After Failover**:

  1. The remote worker accesses the productivity application after failover to WAN2 and observes that the page does not load or TTFB exceeds the SLO.
  2. Use case fails. Minimal guarantees are met.

- **8.a Appliance Does Not Fail Back to WAN1**:

  1. The remote worker verifies that the appliance has not returned to WAN1 within a reasonable period after WAN1 recovery.
  2. The remote worker confirms that traffic continues to flow via WAN2.
  3. Use case fails. Minimal guarantees are met (both links are UP, traffic flows via WAN2).

## Technology & Data Variations List

### Failure Mode Variations

| Variation | WAN1 Condition | Detection Mechanism | Expected Convergence |
|-----------|---------------|---------------------|---------------------|
| **Blackout** | 100% packet loss | BFD / SLA probe timeout | < 1000 ms |
| **Brownout (congested link)** | Elevated latency (~80 ms), jitter (~30 ms), ~1% loss | SLA threshold breach | Appliance-dependent |
| **Brownout (high-latency link)** | Very high latency (~600 ms), ~2% loss | SLA threshold breach | Appliance-dependent |

### Failover Symmetry Variations

| Variation | Failed Link | Failover Target | Description |
|-----------|------------|-----------------|-------------|
| **WAN1 → WAN2** | WAN1 | WAN2 | Primary fails, backup takes over |
| **WAN2 → WAN1** | WAN2 | WAN1 | Backup fails, primary retains traffic |

### Application Continuity Verification

| Application Type | SLO After Failover |
|-----------------|-------------------|
| **Productivity (HTTP)** | TTFB < 200 ms, page load < 2500 ms |
| **Productivity (HTTPS)** | TTFB < 200 ms, page load < 2500 ms |

## Related Information

- Sub-second failure detection is typically achieved via BFD (Bidirectional Forwarding Detection) echo mode or SLA-probe-based monitoring, depending on the appliance implementation.
- Failback behaviour (automatic vs. manual) may vary by appliance configuration and vendor policy.
- For system topology and addressing, see `docs/SDWAN_Testbed_Configuration.md`.
