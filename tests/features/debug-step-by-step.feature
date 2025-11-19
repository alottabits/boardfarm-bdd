Feature: Debug Step by Step
  Scenario: Test Individual Steps
    # Use this file to test individual steps one at a time
    # Comment/uncomment steps as needed to debug
    
    # Background step
    Given a CPE is online and fully provisioned
    
    # Step 1: Operator initiates reboot task
    Given the operator initiates a reboot task on the ACS for the CPE
    
    # Step 2: ACS sends connection request
    When the ACS sends a connection request to the CPE
    
    # Step 3: CPE receives connection request and initiates session
    And the CPE receives the connection request and initiates a session with the ACS
    
    # Step 4: CPE sends Inform message
    And the CPE sends an Inform message to the ACS
    
    # Step 5: ACS responds to Inform and issues Reboot RPC
    Then the ACS responds to the Inform message by issuing the Reboot RPC to the CPE
    
    # Step 6: CPE acknowledges Reboot RPC
    And the CPE receives and acknowledges the Reboot RPC
    
    # Step 7: CPE completes boot and sends post-reboot Inform
    And after completing the boot sequence, the CPE sends an Inform message to the ACS indicating that the boot sequence has been completed
    
    # Step 8: ACS responds to Inform
    And the ACS responds to the Inform message
    
    # Step 11: ACS may verify device state
    # And the ACS may verify device state
    
    # Step 12: CPE resumes normal operation
    # And the CPE resumes normal operation, continuing periodic communication with the ACS
    
    # Step 13: Verify config preservation
    # And the CPE's configuration and operational state are preserved after reboot
    
    # Step 14: Verify success
    # And use case succeeds and all success guarantees are met

