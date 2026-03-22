Feature: WAN Failover Maintains Application Continuity
  As a remote worker accessing applications through the SD-WAN appliance,
  I want the appliance to automatically fail over to a backup WAN link when the primary fails
  So that my application sessions continue without disruption.

  Background:
    Given the SD-WAN appliance is operational with dual WAN connectivity
    And the network conditions are set to "pristine" on all WAN links

  Scenario Outline: UC-SDWAN-01-Main: WAN1 Blackout Triggers Failover and Failback Restores Primary
    Given network operations verifies that both WAN links are in UP state
    And network operations verifies that "wan1" is the active forwarding path
    When the remote worker starts a "<app_type>" session through the appliance
    And the remote worker confirms the "<app_type>" session is responsive
    And "wan1" experiences a complete link failure
    Then the appliance detects the failure and converges to "wan2" within 1000 ms
    And network operations verifies that "wan2" is the active forwarding path
    And the remote worker confirms the "<app_type>" session remains functional within the continuity SLO
    When "wan1" recovers and returns to healthy state
    Then the appliance fails back to "wan1" as the preferred path
    And network operations verifies that "wan1" is the active forwarding path
    And the remote worker confirms the "<app_type>" session remains functional within the continuity SLO
    And network operations verifies that both WAN links are in UP state

    Examples: Application types
    | app_type      |
    | productivity  |
    | streaming     |
    | conferencing  |

  Scenario Outline: UC-SDWAN-01-5.a: Quality Degradation Triggers Failover
    Given network operations verifies that both WAN links are in UP state
    And network operations verifies that "wan1" is the active forwarding path
    When the remote worker starts a "<app_type>" session through the appliance
    And the remote worker confirms the "<app_type>" session is responsive
    And "wan1" experiences degraded conditions consistent with "4g_mobile"
    Then the appliance steers traffic to "wan2"
    And network operations verifies that "wan2" is the active forwarding path
    And the remote worker confirms the "<app_type>" session remains functional within the continuity SLO
    When "wan1" recovers and returns to healthy state
    Then the appliance fails back to "wan1" as the preferred path
    And network operations verifies that "wan1" is the active forwarding path
    And the remote worker confirms the "<app_type>" session remains functional within the continuity SLO
    And network operations verifies that both WAN links are in UP state

    Examples: Application types
    | app_type      |
    | productivity  |
    | streaming     |
    | conferencing  |
