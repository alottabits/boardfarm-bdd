## Goal

When the primary WAN link carrying an encrypted IPsec overlay tunnel fails, the SD-WAN appliance re-establishes the tunnel over the backup WAN link and restores encrypted application connectivity, so that the remote worker's traffic remains protected throughout the WAN failover.

## Scope

The SD-WAN appliance with dual WAN connectivity, the IPsec/IKEv2 overlay tunnel, the remote tunnel endpoint, and the application delivery path through the overlay. These components form the system under consideration.

## Primary Actor

Network Operations Engineer (responsible for overlay and WAN resilience)

## Stakeholders

- Network Operations Engineer — needs confidence that the overlay survives WAN failover
- Security Officer — requires that traffic is never sent unencrypted during or after failover
- Remote Worker — expects uninterrupted secure application access
- SD-WAN Appliance — must detect tunnel loss, re-negotiate over backup path, and restore overlay

## Level

user-goal

## Preconditions

1. The SD-WAN appliance is operational with two WAN links (WAN1 and WAN2) in UP state.
2. WAN1 is the primary (preferred) path with a lower routing metric than WAN2.
3. No IPsec tunnel configuration is present on the appliance — the appliance is in its baseline routing state without an overlay.
4. A remote tunnel endpoint is reachable from both WAN1 and WAN2 and configured to accept IKEv2 negotiation.
5. Authentication credentials are available to the engineer (certificate-based or pre-shared key) but not yet applied to the appliance.
6. The engineer has the tunnel parameters: remote endpoint address, authentication credentials, and desired encryption policy.
7. Baseline network conditions are nominal on both WAN links.

## Minimal Guarantees

- The appliance does not forward LAN-side traffic unencrypted over the WAN during or after the failover — traffic is either routed through the overlay or not forwarded at all.
- The appliance does not leave dangling Security Associations from the failed WAN1 tunnel.
- After WAN1 recovers, the appliance returns to a stable state with the tunnel operational over a single WAN path.
- If the tunnel cannot be re-established over WAN2, the appliance reports a clear tunnel state (DOWN) with a diagnostic reason.

## Success Guarantees

1. The tunnel configuration is accepted by the appliance and the tunnel is established over WAN1 with valid SAs and encryption matching the configured policy.
2. The remote worker accesses an application through the overlay and confirms it responds.
3. After WAN1 fails, the appliance detects the tunnel loss over WAN1.
4. The appliance re-negotiates the IKEv2/IPsec tunnel over WAN2 and the tunnel returns to ESTABLISHED state with valid SAs.
5. The tunnel data plane is functional over WAN2: ICMP echo through the overlay interface to the remote endpoint succeeds.
6. The remote worker accesses the application through the overlay and confirms it responds — encrypted connectivity is restored.
7. After WAN1 recovers, the appliance re-establishes the tunnel over WAN1 (preferred path) and the overlay remains functional.

## Trigger

The network operations engineer configures the appliance with an encrypted overlay tunnel and then the primary WAN link fails while the tunnel is active.

## Main Success Scenario

1. The engineer verifies that both WAN links are UP and no tunnel is currently configured on the appliance.
2. The engineer configures the IKEv2/IPsec tunnel parameters on the appliance: remote endpoint address, authentication method and credentials, and encryption policy.
3. The engineer activates the tunnel configuration.
4. The appliance initiates IKEv2 negotiation with the remote endpoint over WAN1 (the preferred path).
5. The appliance and the remote endpoint complete IKEv2 negotiation and establish IPsec SAs over WAN1.
6. The engineer verifies that the tunnel reports ESTABLISHED state over WAN1 with valid SAs and encryption matching the configured policy.
7. The engineer sends ICMP echo requests through the overlay interface to the remote endpoint and confirms they succeed.
8. The remote worker accesses an application through the overlay tunnel and confirms it responds.
9. WAN1 experiences a complete link failure (100% packet loss).
10. The appliance detects the WAN1 failure and the associated tunnel loss.
11. The appliance initiates IKEv2 re-negotiation with the remote endpoint over WAN2.
12. The appliance and the remote endpoint complete IKEv2 negotiation over WAN2 and establish new IPsec SAs.
13. The engineer verifies that the tunnel reports ESTABLISHED state over WAN2 with valid SAs and encryption matching the configured policy.
14. The engineer sends ICMP echo requests through the overlay interface to the remote endpoint and confirms they succeed over the WAN2 path.
15. The remote worker accesses the application through the overlay and confirms it responds — encrypted connectivity is restored.
16. WAN1 recovers and returns to healthy state.
17. The appliance detects WAN1 recovery and re-establishes the tunnel over WAN1 as the preferred path.
18. The engineer verifies that the tunnel is ESTABLISHED over WAN1 with valid SAs.
19. The remote worker accesses the application through the overlay and confirms it responds over the restored WAN1 path.
20. The engineer verifies that both WAN links are UP and the tunnel is operational over WAN1. Use case succeeds.

## Extensions

- **5.a Initial Tunnel Establishment Fails**:

  1. The appliance fails to establish the IKEv2/IPsec tunnel over WAN1 (authentication failure, proposal mismatch, or remote endpoint unreachable via WAN1).
  2. The appliance reports the tunnel as DOWN with the specific failure reason.
  3. The engineer verifies that no tunnel is established.
  4. Use case fails. Minimal guarantees are met.

- **10.a Appliance Does Not Detect Tunnel Loss**:

  1. The appliance does not detect the WAN1 tunnel loss within a reasonable period after link failure.
  2. The engineer verifies that the tunnel remains in a stale ESTABLISHED state despite WAN1 being down.
  3. The remote worker attempts to access the application through the overlay and observes it is unreachable.
  4. Use case fails. Minimal guarantees are met (no unencrypted traffic is forwarded).

- **12.a Tunnel Re-Negotiation Over WAN2 Fails**:

  1. The appliance attempts IKEv2 negotiation over WAN2 but fails (authentication failure, routing issue to remote endpoint via WAN2, or proposal mismatch).
  2. The appliance reports the tunnel as DOWN with the specific failure reason.
  3. The remote worker attempts to access the application and observes it is unreachable through the overlay.
  4. Use case fails. Minimal guarantees are met.

- **15.a Application Unreachable After Tunnel Re-Establishment**:

  1. The engineer verifies that the tunnel is ESTABLISHED over WAN2 and ICMP through the overlay succeeds.
  2. The remote worker accesses the application through the overlay and observes it does not respond.
  3. Use case fails. Minimal guarantees are met.

- **17.a Appliance Does Not Fail Back Tunnel to WAN1**:

  1. After WAN1 recovery, the appliance does not re-establish the tunnel over WAN1 within a reasonable period.
  2. The engineer verifies that the tunnel remains operational over WAN2.
  3. The remote worker confirms the application is still accessible through the overlay via WAN2.
  4. Use case fails. Minimal guarantees are met (tunnel is functional, but not on the preferred path).

## Technology & Data Variations List

### Tunnel Re-Establishment Behaviour

| Variation | Behaviour After WAN1 Failure | Notes |
|-----------|------------------------------|-------|
| **Automatic re-negotiation** | Appliance detects tunnel loss and initiates IKEv2 over WAN2 without operator intervention | Expected for SD-WAN appliances |
| **DPD-triggered** | Dead Peer Detection (DPD) timeout triggers SA cleanup, then appliance re-initiates over WAN2 | Common IKEv2 implementation |

### Failover Timing

| Phase | Expected Duration | Notes |
|-------|------------------|-------|
| **WAN1 failure detection** | < 1000 ms | BFD or SLA probe timeout |
| **Stale SA cleanup** | Immediate to DPD timeout | Depends on DPD interval configuration |
| **IKEv2 re-negotiation over WAN2** | < 5 seconds | Full IKE + IPsec SA establishment |
| **Total overlay restoration** | < 10 seconds | Combined detection + cleanup + re-negotiation |

### Authentication and Encryption

Same as UC-SDWAN-04 Technology & Data Variations (authentication method and encryption policy variations apply).

## Related Information

- This use case covers the intersection of overlay tunnel establishment (see also UC-SDWAN-04) and WAN failover (see also UC-SDWAN-01): overlay resilience during path failover. It is self-contained and does not depend on prior execution of those use cases.
- IKEv2 Dead Peer Detection (DPD, RFC 3706) is the standard mechanism for detecting a lost tunnel peer. DPD interval and timeout determine how quickly a stale SA is cleaned up.
- Tunnel re-establishment over a different WAN interface requires that the remote endpoint accepts IKEv2 INIT from the appliance's WAN2 address. This may require the remote endpoint to be configured with multiple allowed peer addresses or to accept any authenticated peer.
- A key security requirement is that the appliance must not fall back to forwarding LAN traffic unencrypted over the WAN when the tunnel is down — traffic must be held or dropped until the overlay is restored.
