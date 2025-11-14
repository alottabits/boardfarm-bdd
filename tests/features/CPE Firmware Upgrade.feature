Feature: CPE Firmware Upgrade
  As an operator of a network,
  I want to reliably upgrade the firmware of a CPE
  So that the device remains secure and up-to-date without service interruptions.

  Background:
    Given a CPE is online and fully provisioned

  @UC-12345-Main
  Scenario: Successful Firmware Upgrade
    Given the operator installs a new signed firmware file "prepared_upgrade.img" on the image server
    And the user has set the CPE GUI username to "john" and password to "pass"
    And the user has set the SSID to "mynetwork"
    And the ACS is configured to upgrade the CPE with "prepared_upgrade.img"
    When the CPE performs its periodic TR-069 check-in
    Then the ACS issues the Download RPC
    And the CPE downloads the firmware from the image server
    And the CPE validates the firmware
    And after successful validation, the CPE installs the firmware and reboots
    And the CPE reconnects to the ACS
    And the ACS reports the new firmware version for the CPE
    And the CPE's subscriber credentials and LAN configuration are preserved
    And internet connectivity for the subscriber is restored

  @UC-12345-6.a
  Scenario: Firmware Verification Fails due to Invalid Signature
    Given the operator installs a new firmware file "prplos_corrupt.img" with an invalid signature on the image server
    And the ACS is configured to upgrade the CPE with "prplos_corrupt.img"
    When the CPE performs its periodic TR-069 check-in
    Then the ACS issues the Download RPC
    And the CPE downloads the firmware from the image server
    And the CPE verifies the firmware but rejects it due to validation failure
    And the CPE reports the failed verification to the ACS
    And the ACS records the failure with a non-zero fault code
    And the CPE does not reboot
    And the CPE continues to run its original firmware version
    And the CPE's subscriber credentials and LAN configuration are preserved

  @UC-12345-8.a
  Scenario: Upgrade Fails and Rolls Back Due to Post-Reboot Provisioning Failure
    Given the operator installs a new signed firmware file "prplos_upgrade.img" on the image server
    And the ACS is configured to upgrade the CPE with "prplos_upgrade.img"
    When the CPE performs its periodic TR-069 check-in
    Then the ACS issues the Download RPC
    And the CPE downloads the firmware from the image server
    And the CPE validates the firmware
    And after successful validation, the CPE installs the firmware and reboots
    And after rebooting with the new firmware, the CPE fails to reconnect in a stable, provisioned state
    And the CPE autonomously rolls back to its previous firmware version and reboots
    And the CPE reconnects and resumes normal operation on the original firmware
    And the CPE's subscriber credentials and LAN configuration are preserved
    And the failed upgrade attempt is recorded by the ACS

  @UC-12345-10.a
  Scenario: Upgrade Succeeds but Device Configuration is Reset
    Given the operator installs a new signed firmware file "firmware-v2-resets-config.bin" on the image server
    And the ACS is configured to upgrade the CPE with "firmware-v2-resets-config.bin"
    When the CPE performs its periodic TR-069 check-in
    Then the ACS issues the Download RPC
    And the CPE downloads the firmware from the image server
    And the CPE validates the firmware
    And after successful validation, the CPE installs the firmware and reboots
    And the CPE reconnects to the ACS
    And the ACS reports the new firmware version for the CPE
    But the CPE's subscriber credentials and LAN configuration are reset to factory defaults
    And the subscriber re-configures user credentials and LAN settings
    And the use case succeeds with the configuration loss noted

