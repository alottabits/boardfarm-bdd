Feature: Remote CPE Reboot
  As an operator of a network,
  I want to remotely reboot a CPE device
  So that I can restore connectivity, apply configuration changes, or resolve operational issues without physical access to the device.

  Background:
    Given a CPE is online and fully provisioned

  Scenario: UC-12347-Main: Successful Remote Reboot
    Given the operator configures the ACS to issue a Reboot RPC for the CPE
    When the ACS triggers an immediate connection request to the CPE
    And the CPE sends an Inform message to the ACS
    Then the ACS issues the Reboot RPC to the CPE
    And the CPE receives and acknowledges the Reboot RPC with a RebootResponse
    And the CPE initiates the reboot sequence
    And the CPE shuts down gracefully and restarts
    And after completing the boot sequence, the CPE reconnects to the ACS by sending an Inform message with event code "1 BOOT" and "M Reboot"
    And the ACS acknowledges the Inform and may issue follow-up RPCs to verify device state
    And the CPE resumes normal operation and periodic Inform sessions
    And the CPE's configuration and operational state are preserved after reboot

  Scenario: UC-12347-4.a: CPE Not Connected When Reboot Requested
    Given the operator configures the ACS to issue a Reboot RPC for the CPE
    And the CPE is not currently connected to the ACS
    When the ACS attempts to send the Reboot RPC
    Then the ACS queues the Reboot RPC as a pending task
    And when the CPE's next periodic Inform interval elapses, it connects to the ACS
    And the ACS issues the queued Reboot RPC
    And the CPE receives and acknowledges the Reboot RPC with a RebootResponse
    And the CPE initiates the reboot sequence
    And the CPE shuts down gracefully and restarts
    And after completing the boot sequence, the CPE reconnects to the ACS
    And the CPE resumes normal operation

  Scenario: UC-12347-5.a: CPE Rejects Reboot RPC
    Given the operator configures the ACS to issue a Reboot RPC for the CPE
    When the ACS triggers an immediate connection request to the CPE
    And the CPE sends an Inform message to the ACS
    And the ACS issues the Reboot RPC to the CPE
    Then the CPE receives the Reboot RPC but rejects it due to access rights or invalid state
    And the CPE responds with a RebootResponse containing a fault code
    And the ACS records the failure with the fault code
    And the CPE does not reboot
    And the CPE remains in its current operational state

  Scenario: UC-12347-7.a: CPE Fails to Complete Boot Sequence
    Given the operator configures the ACS to issue a Reboot RPC for the CPE
    When the ACS triggers an immediate connection request to the CPE
    And the CPE sends an Inform message to the ACS
    And the ACS issues the Reboot RPC to the CPE
    And the CPE receives and acknowledges the Reboot RPC with a RebootResponse
    And the CPE initiates the reboot sequence
    Then the CPE fails to complete the boot sequence
    And the CPE does not reconnect to the ACS within the expected time window
    And the ACS detects the absence of periodic Inform messages
    And the ACS logs the failure and may trigger alerts
    And the device record is preserved in the ACS, but the CPE is non-operational

  Scenario: UC-12347-8.a: CPE Fails to Reconnect After Reboot
    Given the operator configures the ACS to issue a Reboot RPC for the CPE
    When the ACS triggers an immediate connection request to the CPE
    And the CPE sends an Inform message to the ACS
    And the ACS issues the Reboot RPC to the CPE
    And the CPE receives and acknowledges the Reboot RPC with a RebootResponse
    And the CPE initiates the reboot sequence
    And the CPE shuts down gracefully and restarts
    Then the CPE successfully reboots but fails to reconnect to the ACS
    And the ACS does not receive Inform messages from the CPE after the expected reconnection window
    And the ACS logs the disconnection and may trigger alerts
    And the device record is preserved in the ACS, but the CPE is disconnected

  Scenario: UC-12347-10.a: CPE Configuration Lost During Reboot
    Given the operator configures the ACS to issue a Reboot RPC for the CPE
    When the ACS triggers an immediate connection request to the CPE
    And the CPE sends an Inform message to the ACS
    And the ACS issues the Reboot RPC to the CPE
    And the CPE receives and acknowledges the Reboot RPC with a RebootResponse
    And the CPE initiates the reboot sequence
    And the CPE shuts down gracefully and restarts
    And after completing the boot sequence, the CPE reconnects to the ACS
    Then the reboot succeeds, but some configuration parameters are reset to defaults
    And the CPE reconnects to the ACS with default or partial configuration
    And the ACS detects configuration discrepancies and may trigger reprovisioning
    And the use case succeeds with the configuration loss noted

