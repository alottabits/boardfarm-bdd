Feature: QoS Priority Under WAN Contention
  As a remote worker accessing applications through the SD-WAN appliance,
  I want the appliance's QoS policy to protect my priority application traffic
  So that my conferencing sessions maintain acceptable quality when the WAN link
  is saturated by best-effort background traffic.

  Background:
    Given the SD-WAN appliance is operational with dual WAN connectivity
    And the network conditions are set to "cable_typical" on all WAN links
    And traffic generators are available on both sides of the appliance

  Scenario: UC-SDWAN-06-Main: Upstream WAN Saturation Preserves Conferencing Quality
    Given network operations verifies that both WAN links are in UP state
    When network operations starts 85 Mbps of best-effort upstream background traffic through the appliance
    And the remote worker starts a "conferencing" session through the appliance
    Then the remote worker confirms the "conferencing" session remains functional within the continuity SLO
    When network operations stops the upstream background traffic
