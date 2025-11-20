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
    Given the operator initiates a reboot task on the ACS for the CPE
    When the ACS attempts to send the connection request, but the CPE is offline or unreachable
    Then the ACS cannot send the connection request to the CPE
    And the ACS queues the Reboot RPC as a pending task
    And when the CPE comes online, it connects to the ACS
    And the CPE sends an Inform message to the ACS
    And the ACS issues the queued Reboot RPC
    And after completing the boot sequence, the CPE sends an Inform message to the ACS indicating that the boot sequence has been completed
    And the CPE resumes normal operation, continuing periodic communication with the ACS

  Scenario: UC-12347-6.a: CPE Rejects Reboot RPC
    Given the operator initiates a reboot task on the ACS for the CPE
    When the ACS sends a connection request to the CPE
    And the CPE receives the connection request and initiates a session with the ACS
    And the CPE sends an Inform message to the ACS
    And the ACS responds to the Inform message by issuing the Reboot RPC to the CPE
    Then the CPE receives the Reboot RPC but rejects it due to access rights, invalid state, or security policy
    And the CPE responds with a fault code indicating the rejection
    And the ACS records the failure with the fault code and logs the rejection
    And the CPE does not reboot
    And the CPE remains in its current operational state
    And the CPE completes the session normally

  Scenario: UC-12347-9.a: CPE Fails to Complete Boot Sequence
    Given the operator initiates a reboot task on the ACS for the CPE
    When the ACS sends a connection request to the CPE
    And the CPE receives the connection request and initiates a session with the ACS
    And the CPE sends an Inform message to the ACS
    And the ACS responds to the Inform message by issuing the Reboot RPC to the CPE
    Then the CPE executes the reboot command but fails to complete the boot sequence
    And the CPE does not reconnect to the ACS within the expected time window
    And the ACS does not receive Inform messages from the CPE after the expected reconnection window
    And the ACS detects the absence of periodic Inform messages
    And the ACS logs the failure and may trigger alerts
    And the device record is preserved in the ACS, but the CPE is non-operational

  Scenario: UC-12347-10.a: CPE Fails to Reconnect After Reboot
    Given the operator initiates a reboot task on the ACS for the CPE
    When the ACS sends a connection request to the CPE
    And the CPE receives the connection request and initiates a session with the ACS
    And the CPE sends an Inform message to the ACS
    And the ACS responds to the Inform message by issuing the Reboot RPC to the CPE
    And the CPE executes the reboot command and restarts
    Then the CPE successfully reboots but fails to reconnect to the ACS
    And the ACS does not receive Inform messages from the CPE after the expected reconnection window
    And the ACS logs the disconnection and may trigger alerts
    And the device record is preserved in the ACS, but the CPE is disconnected

  Scenario: UC-12347-11.a: CPE Configuration Lost During Reboot
    Given the operator initiates a reboot task on the ACS for the CPE
    When the ACS sends a connection request to the CPE
    And the CPE receives the connection request and initiates a session with the ACS
    And the CPE sends an Inform message to the ACS
    And the ACS responds to the Inform message by issuing the Reboot RPC to the CPE
    And after completing the boot sequence, the CPE sends an Inform message to the ACS indicating that the boot sequence has been completed
    Then the reboot succeeds, but some configuration parameters are reset to defaults or lost
    And the CPE reconnects to the ACS and sends Inform message, but with default or partial configuration
    And the ACS detects configuration discrepancies
    And the ACS may trigger reprovisioning to restore the correct configuration
    And the use case succeeds with comments, noting the configuration loss and reprovisioning

