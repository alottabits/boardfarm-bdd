## Goal

Enable a user to successfully make a one-way voice call from one SIP phone to another SIP phone, establishing a voice communication session.

## Scope

The E2E system, including the SIP phones (LAN and WAN), SIP server (Kamailio), CPE, and network infrastructure.

## Primary Actor

User (caller)

## Stakeholders

- User (caller)
- User (callee)
- SIP Server Administrator
- Network Operations
- CPE
- SIP Server (Kamailio)

## Level

user-goal

## Preconditions

1. Both SIP phones are powered on and have network connectivity.
2. Both SIP phones are registered with the SIP server.
3. The SIP server (Kamailio) is running and operational.
4. The caller knows the phone number of the callee.
5. If calling through CPE, the CPE is online and NAT/SIP ALG is properly configured.

## Minimal Guarantees

- The SIP server logs all call-related activities, including failures.
- If the call fails to establish, both phones return to idle state.
- No partial call state is left in the system (proper cleanup occurs).
- The SIP server maintains registration status for both phones.

## Success Guarantees

1. The caller successfully dials the callee's number.
2. The SIP server routes the call to the correct callee.
3. The callee's phone rings.
4. The callee successfully answers the call.
5. A bidirectional voice path (RTP session) is established between caller and callee.
6. Both parties can communicate via voice.
7. The call can be terminated cleanly by either party.
8. After call termination, both phones return to idle state.

## Trigger

A user picks up a SIP phone (or takes it off-hook) and dials another phone's number.

## Main Success Scenario

1. The caller takes the phone off-hook.
2. The caller's phone plays dial tone.
3. The caller dials the callee's phone number.
4. The caller's phone sends a SIP INVITE message to the SIP server.
5. The SIP server receives the INVITE and validates the request.
6. The SIP server routes the call to the callee's registered endpoint.
7. The SIP server sends a SIP INVITE to the callee's phone.
8. The callee's phone receives the INVITE and starts ringing.
9. The SIP server sends a "180 Ringing" response back to the caller.
10. The caller's phone receives the ringing indication.
11. The callee answers the call (goes off-hook or presses answer).
12. The callee's phone sends a "200 OK" response to the SIP server.
13. The SIP server forwards the "200 OK" to the caller's phone.
14. The caller's phone sends an ACK to complete the SIP handshake.
15. RTP media session is established between the two phones.
16. Both parties can communicate via voice.
17. Either party hangs up (goes on-hook).
18. The hanging-up phone sends a SIP BYE message.
19. The SIP server routes the BYE to the other party.
20. The other party's phone sends a "200 OK" response.
21. Both phones return to idle state.
22. Use case succeeds and all success guarantees are met.

## Extensions

- **3.a Invalid Phone Number**:
  
  1. The caller dials the incorrect phone number.
  2. The SIP server determines the dialed number is not registered.
  3. The SIP server sends a "404 Not Found" response to the caller.
  4. The caller's phone plays a busy tone or error message.
  5. The caller hangs up.
  6. Use case fails. Minimal guarantees are met.

- **8.a Callee is Busy**:
  
  1. The callee's phone is already in an active call.
  2. The SIP server determines the callee is busy.
  3. The SIP server sends a "486 Busy Here" response to the caller.
  4. The caller's phone plays a busy tone.
  5. The caller hangs up.
  6. Use case fails. Minimal guarantees are met.

- **11.a Callee Does Not Answer (Timeout)**:
  
  1. The callee's phone rings but is not answered within the timeout period.
  2. The callee's phone or SIP server sends a "408 Request Timeout" or "480 Temporarily Unavailable" response.
  3. The SIP server forwards the timeout response to the caller.
  4. The caller's phone stops ringing indication.
  5. The caller hangs up.
  6. Use case fails. Minimal guarantees are met.

- **11.b Callee Rejects the Call**:
  
  1. The callee actively rejects the incoming call.
  2. The callee's phone sends a "603 Decline" or "486 Busy Here" response.
  3. The SIP server forwards the rejection to the caller.
  4. The caller's phone plays a busy tone or rejection message.
  5. The caller hangs up.
  6. Use case fails. Minimal guarantees are met.

- **15.a RTP Media Fails to Establish**:
  
  1. The SIP signaling completes successfully but RTP media path fails.
  2. One or both parties experience no audio (one-way or no audio).
  3. Either party hangs up due to communication failure.
  4. Continue from step 18 of the main success scenario.
  5. Use case fails. Minimal guarantees are met.

## Technology & Data Variations List

### Phone Location Combinations

The following table shows all possible combinations of caller and callee locations. Each combination represents a distinct test scenario due to different network paths and NAT traversal requirements:

| Variation ID | Caller Location | Caller Number | Callee Location | Callee Number | Network Path | NAT Traversal |
|--------------|----------------|---------------|-----------------|---------------|--------------|---------------|
| **V1** | LAN | 1000 | WAN | 2000 | LAN → CPE → Router → WAN | Yes (outbound) |
| **V2** | LAN | 1000 | WAN2 | 3000 | LAN → CPE → Router → WAN | Yes (outbound) |
| **V3** | WAN | 2000 | LAN | 1000 | WAN → Router → CPE → LAN | Yes (inbound) |
| **V4** | WAN | 2000 | WAN2 | 3000 | WAN → Router → WAN | No (direct WAN) |
| **V5** | WAN2 | 3000 | LAN | 1000 | WAN → Router → CPE → LAN | Yes (inbound) |
| **V6** | WAN2 | 3000 | WAN | 2000 | WAN → Router → WAN | No (direct WAN) |

**Phone Locations:**
- **LAN**: lan-phone (number 1000) - Behind CPE on LAN side, obtains IP via DHCP
- **WAN**: wan-phone (number 2000) - Direct WAN connection at 172.25.1.3/24
- **WAN2**: wan-phone2 (number 3000) - Direct WAN connection at 172.25.1.4/24

**Network Path Characteristics:**
- **LAN → WAN**: Tests CPE NAT traversal for outbound calls, SIP ALG functionality
- **WAN → LAN**: Tests CPE NAT traversal for inbound calls, port forwarding, SIP ALG
- **WAN → WAN**: Tests direct SIP communication without CPE involvement, baseline scenario

### Additional Technology Variations

- **SIP Transport**: UDP (default), TCP, TLS
- **Audio Codecs**: G.711 (μ-law/a-law), G.729, Opus
- **IP Version**: IPv4, IPv6, dual-stack
- **DTMF Method**: In-band, RFC 2833, SIP INFO
- **Call Duration**: Short (< 1 minute), medium (1-5 minutes), long (> 5 minutes)
- **Network Conditions**: Normal, packet loss, jitter, latency

## Related information

- This use case assumes the use of SIP (Session Initiation Protocol) for call signaling.
- RTP (Real-time Transport Protocol) is used for voice media transmission.
- The SIP server (Kamailio) includes RTPEngine for media relay and NAT traversal support.
- NAT traversal is critical for LAN-to-WAN and WAN-to-LAN call scenarios.
- The CPE's SIP ALG (Application Layer Gateway) may modify SIP messages for NAT traversal.
- For detailed network topology, see: `boardfarm-bdd/docs/Testbed Network Topology.md`
- For SIP phone configuration details, see: `boardfarm-bdd/docs/sip_phone_configuration.md`
- Phone numbers registered on SIP server:
  - 1000: lan-phone (LAN side)
  - 2000: wan-phone (WAN side)
  - 3000: wan-phone2 (WAN side)
