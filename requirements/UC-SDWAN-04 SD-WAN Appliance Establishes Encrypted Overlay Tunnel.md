## Goal

A network operations engineer configures the SD-WAN appliance to establish an encrypted IPsec/IKEv2 overlay tunnel to a remote endpoint, and the appliance successfully negotiates the tunnel, maintains it in a healthy state, and forwards traffic through the encrypted overlay so that data traversing the WAN is protected.

## Scope

The SD-WAN appliance, its WAN connectivity, the IPsec overlay tunnel, and the remote tunnel endpoint. The overlay tunnel and the traffic forwarded through it form the system under consideration.

## Primary Actor

Network Operations Engineer (configures and activates the overlay tunnel on the appliance)

## Stakeholders

- Network Operations Engineer — needs to configure and verify tunnel establishment
- Security Officer — requires confirmation that WAN traffic traverses the encrypted overlay
- IT Operations — needs assurance that overlay failures are detected and reported
- Remote Worker — depends on the overlay for secure application access

## Level

user-goal

## Preconditions

1. The SD-WAN appliance is operational with at least one WAN link in UP state.
2. No IPsec tunnel configuration is present on the appliance — the appliance is in its baseline routing state without an overlay.
3. A remote tunnel endpoint is reachable via the WAN and configured to accept IKEv2 negotiation.
4. Authentication credentials are available to the operator but not yet applied to the appliance:
   - For certificate-based authentication: a trusted CA has issued certificates for both the appliance and the remote endpoint.
   - For pre-shared key authentication: a shared secret has been agreed upon between both endpoints.
5. The operator has the tunnel parameters: remote endpoint address, authentication credentials, and desired encryption policy.

## Minimal Guarantees

- If tunnel establishment fails, the appliance reports a clear tunnel state (DOWN or NOT_ESTABLISHED) with a diagnostic reason (authentication failure, proposal mismatch, timeout).
- The appliance does not leave dangling Security Associations (SAs) after a failed or terminated tunnel.
- The appliance's tunnel configuration remains intact after a failure and allows re-establishment without reconfiguration.
- If the operator applies an invalid configuration, the appliance rejects it or reports a configuration error — it does not silently fail.

## Success Guarantees

1. The tunnel configuration is accepted by the appliance without errors.
2. The IKEv2 negotiation completes successfully and the tunnel transitions to ESTABLISHED state.
3. Both inbound and outbound IPsec SAs are present with valid SPI values.
4. The encryption algorithm reported by the tunnel status matches the configured policy (e.g., AES-256-GCM).
5. The tunnel data plane is functional: ICMP echo through the overlay interface to the remote endpoint succeeds.
6. Traffic from the LAN side routed through the overlay reaches the remote network — an application on the far side of the tunnel is accessible.

## Trigger

The network operations engineer applies the IPsec/IKEv2 tunnel configuration to the appliance and activates it.

## Main Success Scenario

1. The engineer verifies that the WAN link to the remote endpoint is UP and no tunnel is currently configured on the appliance.
2. The engineer configures the IKEv2/IPsec tunnel parameters on the appliance: remote endpoint address, authentication method and credentials, and encryption policy.
3. The engineer activates the tunnel configuration.
4. The appliance initiates IKEv2 negotiation with the remote endpoint.
5. The appliance and the remote endpoint complete IKEv2 Phase 1 (IKE SA): both sides authenticate and establish a secure control channel.
6. The appliance and the remote endpoint complete IKEv2 Phase 2 (Child SA / IPsec SA): both sides establish ESP Security Associations for encrypted data transport.
7. The engineer verifies that the tunnel reports ESTABLISHED state with valid inbound and outbound SAs.
8. The engineer verifies that the reported encryption algorithm matches the configured policy (e.g., AES-256-GCM for ESP).
9. The engineer sends ICMP echo requests through the tunnel overlay interface to the remote endpoint and confirms they succeed.
10. The remote worker accesses an application that is routed through the tunnel overlay and confirms the application responds.
11. Use case succeeds.

## Extensions

- **3.a Invalid Configuration (Rejected by Appliance)**:

  1. The engineer provides an invalid or incomplete tunnel configuration (e.g., missing remote endpoint, unsupported cipher).
  2. The appliance rejects the configuration and reports a configuration error to the engineer.
  3. The engineer verifies that no tunnel negotiation was attempted.
  4. Use case fails. Minimal guarantees are met.

- **5.a IKEv2 Negotiation Fails (Authentication Failure)**:

  1. The appliance fails to authenticate with the remote endpoint (invalid certificate, expired credential, or PSK mismatch).
  2. The appliance reports the authentication failure with the specific reason.
  3. The engineer verifies that the tunnel remains in DOWN state.
  4. Use case fails. Minimal guarantees are met.

- **5.b IKEv2 Negotiation Fails (Proposal Mismatch)**:

  1. The appliance and remote endpoint fail to agree on a common IKE or ESP proposal (cipher suite, key exchange group).
  2. The appliance reports the proposal mismatch.
  3. The engineer verifies that the tunnel remains in DOWN state.
  4. Use case fails. Minimal guarantees are met.

- **9.a Data-Plane Failure (Tunnel Established but No Connectivity)**:

  1. The engineer verifies that the tunnel is in ESTABLISHED state (IKE and IPsec SAs exist).
  2. The engineer sends ICMP echo requests through the overlay interface and observes they fail.
  3. Use case fails: control plane up, data plane down. Minimal guarantees are met.

- **10.a Application Unreachable Through Overlay**:

  1. The engineer confirms ICMP through the overlay succeeds.
  2. The remote worker accesses an application routed through the tunnel and observes that the application does not respond.
  3. Use case fails. Minimal guarantees are met.

## Technology & Data Variations List

### Authentication Method Variations

| Variation | Auth Type | Credential | Notes |
|-----------|----------|------------|-------|
| **Certificate-based** | X.509 | CA-issued certificates | Verifies PKI trust chain; standard for SD-WAN |
| **Pre-Shared Key** | PSK | Shared secret | Simpler setup; common in lab and branch deployments |

### Encryption Policy Variations

| Variation | IKE Cipher | ESP Cipher | Key Exchange | Notes |
|-----------|-----------|-----------|--------------|-------|
| **AES-256-GCM** | AES-256 | AES-256-GCM-128 | DH Group 14 | Modern AEAD suite |
| **AES-128-CBC** | AES-128 | AES-128-CBC + SHA-256 | DH Group 14 | Legacy compatibility |

### Tunnel Health Verification

| Method | Target | Pass Criteria |
|--------|--------|---------------|
| **ICMP echo** | Remote tunnel endpoint IP | Reply received within timeout |
| **Application reachability** | Application on the remote network | Application responds through overlay |

## Related Information

- IKEv2 is defined in RFC 7296. IPsec ESP is defined in RFC 4303.
- AES-GCM for ESP is defined in RFC 4106 and provides authenticated encryption (AEAD), combining confidentiality and integrity in a single algorithm.
- Certificate-based IKEv2 authentication uses X.509 certificates per RFC 7296 Section 3.6.
- Tunnel health is distinct from tunnel establishment: a tunnel may be established (SAs present) but non-functional at the data plane due to MTU, routing, or firewall issues.
