Feature: Remote Worker Accesses Cloud Application
  As a remote worker accessing a cloud-hosted productivity application,
  I want the page to load with acceptable performance under varying WAN conditions
  So that I can work productively from any location.

  Background:
    Given the SD-WAN appliance is operational with dual WAN connectivity
    And the appliance is configured for single-WAN operation on "wan1"
    And the network conditions on the active WAN link are set to "pristine"
    When the remote worker starts a "productivity" session through the appliance
    And the remote worker confirms the "productivity" session is responsive

  Scenario Outline: UC-SDWAN-02-Main: Productivity Page Load Under Varying WAN Conditions
    Given the network conditions on the active WAN link are set to "<wan_preset>"
    When the remote worker loads the productivity page through the appliance
    Then the remote worker confirms the productivity page loads within <max_ttfb> ms TTFB and <max_load_time> ms total

    Examples: WAN condition variations
    | wan_preset      | max_ttfb | max_load_time |
    | pristine        | 200      | 2500          |
    | cable_typical   | 300      | 4000          |
    | 4g_mobile       | 500      | 6000          |
    | satellite       | 3000     | 12000         |

  Scenario: UC-SDWAN-02-1.a: HTTPS with HTTP/3 Protocol Negotiation
    Given the network conditions on the active WAN link are set to "pristine"
    When the remote worker starts a "productivity" session over "https" through the appliance
    Then the remote worker confirms the productivity page loads within 500 ms TTFB and 8000 ms total
    And the remote worker confirms the negotiated protocol is "h3"

  Scenario: UC-SDWAN-02-2.a: Application Unreachable
    Given the network conditions on the active WAN link are set to "pristine"
    When the remote worker navigates to an unreachable application URL
    Then the remote worker's browser reports a connection failure
