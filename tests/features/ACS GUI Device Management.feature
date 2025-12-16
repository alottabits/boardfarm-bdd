Feature: ACS GUI Device Management
  As a network operator,
  I want to manage CPE devices through the ACS web interface
  So that I can monitor device status and perform operations without requiring API access.

  Background:
    Given the ACS GUI is configured and available
    And a CPE is online and fully provisioned

  Scenario: UC-ACS-GUI-01-Auth: Successful GUI Login and Logout
    Given the operator is not logged into the ACS GUI
    When the operator logs into the ACS GUI with valid credentials
    Then the operator should be successfully authenticated
    And the ACS dashboard should be displayed
    When the operator logs out from the ACS GUI
    Then the operator should be logged out successfully
    And the login page should be displayed

  Scenario: UC-ACS-GUI-01-Search: Search for Device by ID
    Given the operator is logged into the ACS GUI
    And the CPE device ID is known
    When the operator searches for the device in the ACS GUI
    Then the device should appear in the search results
    And the device status should be visible

  Scenario: UC-ACS-GUI-01-Status: View Device Status and Information
    Given the operator is logged into the ACS GUI
    And the CPE device ID is known
    When the operator navigates to the device details page
    Then the device status should be displayed as "online"
    And the device information should be visible
    And the last inform time should be displayed

  Scenario: UC-ACS-GUI-01-Reboot: Reboot Device via GUI
    Given the operator is logged into the ACS GUI
    And the CPE device ID is known
    When the operator initiates a reboot via the ACS GUI
    Then the reboot command should be sent to the device
    And a confirmation message should be displayed
    And the device should reboot successfully
    And after completing the boot sequence, the CPE sends an Inform message to the ACS indicating that the boot sequence has been completed
    And the CPE resumes normal operation, continuing periodic communication with the ACS

  Scenario: UC-ACS-GUI-01-GetParam: Retrieve Device Parameter via GUI
    Given the operator is logged into the ACS GUI
    And the CPE device ID is known
    When the operator requests the device software version via GUI
    Then the software version parameter should be retrieved
    And the value should be displayed in the GUI

  Scenario: UC-ACS-GUI-01-2a: Invalid Credentials
    Given the operator is not logged into the ACS GUI
    When the operator attempts to login with invalid credentials
    Then the login should fail
    And an authentication error should be displayed

  Scenario: UC-ACS-GUI-01-4a: Search for Non-Existent Device
    Given the operator is logged into the ACS GUI
    When the operator searches for a non-existent device ID
    Then no devices should be found in the search results
    And an appropriate message should be displayed

  Scenario: UC-ACS-GUI-01-7a: View Offline Device Status
    Given the operator is logged into the ACS GUI
    And a CPE device is offline
    When the operator views the offline device details
    Then the device status should be displayed as "offline"
    And the last known information should be visible
    And the last inform time should indicate when device was last online

  Scenario: UC-ACS-GUI-01-8a: Firmware Upgrade Fails on Containerized CPE
    Given the operator is logged into the ACS GUI
    And the CPE device ID is known
    And the CPE is a containerized device
    When the operator attempts to trigger a firmware upgrade via the GUI
    Then the firmware upgrade command should be sent
    But the operation should fail on the containerized CPE
    And an error message should be displayed in the GUI
    And the device should remain in operational state

