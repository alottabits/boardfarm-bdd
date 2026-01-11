Feature: Device Class Initialization
  As a Test Engineer
  I want Boardfarm to support RPi prplOS CPEs
  So that I can test physical devices in the testbed

  Background:
    Given the testbed is configured with RPi prplOS CPE

  Scenario: UC-Device-Init-Main: Successful Device Initialization
    Given Boardfarm instantiates the device from configuration
    When Boardfarm connects to the serial console
    And Boardfarm boots the device
    Then the device comes online
    And the device registers with ACS

  Scenario: UC-Device-Init-1.a: Device Not Found in Configuration
    Given the testbed configuration is missing the device
    When Boardfarm attempts to instantiate the device
    Then a configuration error is raised

  Scenario: UC-Device-Init-4.a: ACS Registration Failure
    Given Boardfarm instantiates the device from configuration
    And Boardfarm boots the device
    When the ACS is unreachable
    Then the device fails to register with ACS
