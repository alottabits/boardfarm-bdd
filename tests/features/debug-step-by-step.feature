Feature: Debug Step by Step
  Scenario: Test Individual Steps
    # Use this file to test individual steps one at a time
    # Comment/uncomment steps as needed to debug
    
    # Background step
    Given a CPE is online and fully provisioned
    
    # Step 1: Install firmware
    Given the operator installs a new signed firmware file "prepared_upgrade.img" on the image server
    
    # Step 2: Set credentials
    And the user has set the CPE GUI username to "john" and password to "pass"
    
    # Step 3: Set SSID
    And the user has set the SSID to "mynetwork"
    
    # Step 4: Configure ACS
    And the ACS is configured to upgrade the CPE with "prepared_upgrade.img"
    
    # Step 5: Trigger check-in
    When the CPE performs its periodic TR-069 check-in
    
    # Step 6: Verify Download RPC
    Then the ACS issues the Download RPC
    
    # Step 7: Verify download
    And the CPE downloads the firmware from the image server
    
    # Step 8: Verify validation
    And the CPE validates the firmware
    
    # Step 9: Verify install and reboot
    And after successful validation, the CPE installs the firmware and reboots
    
    # Step 10: Verify reconnection
    And the CPE reconnects to the ACS
    
    # Step 11: Verify firmware version
    And the ACS reports the new firmware version for the CPE
    
    # Step 12: Verify config preservation
    And the CPE's subscriber credentials and LAN configuration are preserved
    
    # Step 13: Verify connectivity
    And internet connectivity for the subscriber is restored

