Feature: UC-12348 User Makes a One-Way Call
  
  As a user
  I want to make a voice call from one SIP phone to another
  So that I can establish voice communication

  Background:
    Given the SIP server is running and operational
    And the following phones are required for this use case:
      | phone_name | network_location |
      | lan_phone  | LAN              |
      | wan_phone  | WAN              |
      | wan_phone2 | WAN              |

  # Main Success Scenario - Network Topology Variations
  # The main scenario is tested across all 6 phone location combinations
  # to validate call functionality in different network paths (NAT traversal, direct WAN)

  Scenario: UC-12348-Main-V1: LAN Phone Calls WAN Phone (NAT Outbound)
    Given "lan_phone" with number "1000" is registered on the LAN side
    And "wan_phone" with number "2000" is registered on the WAN side
    And "lan_phone" is the caller and "wan_phone" is the callee
    When the caller calls the callee
    Then the callee phone should start ringing
    When the callee answers the call
    Then both phones should be connected
    And a bidirectional RTP media session should be established
    And voice communication should be established through CPE NAT
    When the caller hangs up
    Then the SIP server should terminate the call
    And both phones should return to idle state

  Scenario: UC-12348-Main-V2: LAN Phone Calls WAN Phone 2 (NAT Outbound)
    Given "lan_phone" with number "1000" is registered on the LAN side
    And "wan_phone2" with number "3000" is registered on the WAN side
    And "lan_phone" is the caller and "wan_phone2" is the callee
    When the caller calls the callee
    Then the callee phone should start ringing
    When the callee answers the call
    Then both phones should be connected
    And a bidirectional RTP media session should be established
    And voice communication should be established through CPE NAT
    When the caller hangs up
    Then the SIP server should terminate the call
    And both phones should return to idle state

  Scenario: UC-12348-Main-V3: WAN Phone Calls LAN Phone (NAT Inbound)
    Given "wan_phone" with number "2000" is registered on the WAN side
    And "lan_phone" with number "1000" is registered on the LAN side
    And "wan_phone" is the caller and "lan_phone" is the callee
    When the caller calls the callee
    Then the callee phone should start ringing
    When the callee answers the call
    Then both phones should be connected
    And a bidirectional RTP media session should be established
    And voice communication should be established through CPE NAT
    When the caller hangs up
    Then the SIP server should terminate the call
    And both phones should return to idle state

  Scenario: UC-12348-Main-V4: WAN Phone Calls WAN Phone 2 (Direct WAN)
    Given "wan_phone" with number "2000" is registered on the WAN side
    And "wan_phone2" with number "3000" is registered on the WAN side
    And "wan_phone" is the caller and "wan_phone2" is the callee
    When the caller calls the callee
    Then the callee phone should start ringing
    When the callee answers the call
    Then both phones should be connected
    And a bidirectional RTP media session should be established
    And voice communication should be established without NAT traversal
    When the caller hangs up
    Then the SIP server should terminate the call
    And both phones should return to idle state

  Scenario: UC-12348-Main-V5: WAN Phone 2 Calls LAN Phone (NAT Inbound)
    Given "wan_phone2" with number "3000" is registered on the WAN side
    And "lan_phone" with number "1000" is registered on the LAN side
    And "wan_phone2" is the caller and "lan_phone" is the callee
    When the caller calls the callee
    Then the callee phone should start ringing
    When the callee answers the call
    Then both phones should be connected
    And a bidirectional RTP media session should be established
    And voice communication should be established through CPE NAT
    When the caller hangs up
    Then the SIP server should terminate the call
    And both phones should return to idle state

  Scenario: UC-12348-Main-V6: WAN Phone 2 Calls WAN Phone (Direct WAN)
    Given "wan_phone2" with number "3000" is registered on the WAN side
    And "wan_phone" with number "2000" is registered on the WAN side
    And "wan_phone2" is the caller and "wan_phone" is the callee
    When the caller calls the callee
    Then the callee phone should start ringing
    When the callee answers the call
    Then both phones should be connected
    And a bidirectional RTP media session should be established
    And voice communication should be established without NAT traversal
    When the caller hangs up
    Then the SIP server should terminate the call
    And both phones should return to idle state

  # Extension Scenarios - Error Handling (Network Topology Independent)
  # These scenarios test error conditions that behave the same regardless of network path

  Scenario: UC-12348-3.a: Invalid Phone Number
    Given "wan_phone" is the caller and "wan_phone2" is the callee
    And the caller phone is idle
    When the caller takes the phone off-hook
    And the caller dials an unregistered phone number
    Then the SIP server should send a "404 Not Found" response
    And the caller phone should play busy tone or error message
    When the caller hangs up
    Then the caller phone should return to idle state

  Scenario: UC-12348-8.a: Callee is Busy
    Given "wan_phone" is the caller and "wan_phone2" is the callee
    And the caller phone is idle
    And the callee phone is in an active call
    When the caller takes the phone off-hook
    And the caller dials the callee's number
    Then the callee phone should send a "486 Busy Here" response
    And the caller phone should play busy tone
    When the caller hangs up
    Then the caller phone should return to idle state

  Scenario: UC-12348-11.a: Callee Does Not Answer (Timeout)
    Given "wan_phone" is the caller and "wan_phone2" is the callee
    And the caller phone is idle
    And the callee phone is idle
    When the caller takes the phone off-hook
    And the caller dials the callee's number
    Then the callee phone should start ringing
    When the callee does not answer within the timeout period
    Then the SIP server should send a timeout response
    And the caller phone should stop ringing indication
    When the caller hangs up
    Then the caller phone should return to idle state

  Scenario: UC-12348-11.b: Callee Rejects the Call
    Given "wan_phone" is the caller and "wan_phone2" is the callee
    And the caller phone is idle
    And the callee phone is idle
    When the caller takes the phone off-hook
    And the caller dials the callee's number
    Then the callee phone should start ringing
    When the callee rejects the call
    Then the SIP server should send a rejection response
    And the caller phone should play busy tone or rejection message
    When the caller hangs up
    Then the caller phone should return to idle state

  Scenario: UC-12348-15.a: RTP Media Fails to Establish
    Given "wan_phone" is the caller and "wan_phone2" is the callee
    And the caller phone is idle
    And the callee phone is idle
    When the caller takes the phone off-hook
    And the caller dials the callee's number
    And the callee answers the call
    Then the SIP signaling should complete successfully
    But the RTP media path should fail to establish
    And one or both parties should experience no audio
    When either party hangs up due to communication failure
    Then the SIP server should terminate the call
    And both phones should return to idle state
