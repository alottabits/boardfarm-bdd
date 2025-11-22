Feature: Remote CPE Reboot
  As an operator of a network,
  I want to remotely reboot a CPE device
  So that I can restore connectivity, apply configuration changes, or resolve operational issues without physical access to the device.

  Background:
    Given a CPE is online and fully provisioned
    And the user has set the CPE GUI password to "p@ssw0rd123!"

  Scenario: UC-12347-Main: Successful Remote Reboot
    Given the operator initiates a reboot task on the ACS for the CPE
    When the ACS sends a connection request to the CPE
    And the CPE receives the connection request and initiates a session with the ACS
    And the CPE sends an Inform message to the ACS
    Then the ACS responds to the Inform message by issuing the Reboot RPC to the CPE
    And after completing the boot sequence, the CPE sends an Inform message to the ACS indicating that the boot sequence has been completed
    And the CPE resumes normal operation, continuing periodic communication with the ACS
    And the CPE's configuration and operational state are preserved after reboot
    And use case succeeds and all success guarantees are met

  Scenario: UC-12347-3.a: CPE Not Connected When Reboot Requested
    Given the CPE is unreachable for TR-069 sessions
    When the operator initiates a reboot task on the ACS for the CPE
    Then the ACS cannot send the connection request to the CPE
    And the ACS queues the Reboot RPC as a pending task
    And when the CPE comes online, it connects to the ACS
    And the CPE sends an Inform message to the ACS
    And the ACS issues the queued Reboot RPC
    And after completing the boot sequence, the CPE sends an Inform message to the ACS indicating that the boot sequence has been completed
    And the CPE resumes normal operation, continuing periodic communication with the ACS
    And the CPE's configuration and operational state are preserved after reboot
    And use case succeeds and all success guarantees are met



