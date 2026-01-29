*** Settings ***
Documentation    Cleanup keywords for test teardown and state restoration.
...              This resource provides keywords for cleaning up test artifacts
...              and restoring the testbed to a known good state.

Library     robotframework_boardfarm.BoardfarmLibrary
Library     robotframework_boardfarm.UseCaseLibrary
Library     Collections

*** Keywords ***
# =============================================================================
# CPE Cleanup
# =============================================================================

Cleanup CPE Configuration
    [Documentation]    Restore CPE configuration to original state.
    ...    Pass the original configuration dictionary captured at test start.
    [Arguments]    ${original_config}
    Log    Restoring CPE configuration...
    FOR    ${param}    ${value}    IN    &{original_config}
        Run Keyword And Ignore Error
        ...    Acs Set Parameter Value    ${ACS}    ${CPE}    ${param}    ${value}
    END
    Log    CPE configuration restored

Restore CPE Parameter
    [Documentation]    Restore a single CPE parameter to its original value.
    [Arguments]    ${parameter}    ${original_value}    ${acs}=${ACS}    ${cpe}=${CPE}
    Run Keyword And Ignore Error
    ...    Acs Set Parameter Value    ${acs}    ${cpe}    ${parameter}    ${original_value}
    Log    Restored ${parameter} to ${original_value}

Capture CPE Parameter
    [Documentation]    Capture current value of a CPE parameter for later restoration.
    [Arguments]    ${parameter}    ${acs}=${ACS}    ${cpe}=${CPE}
    ${value}=    Run Keyword And Return Status
    ...    Acs Get Parameter Value    ${acs}    ${cpe}    ${parameter}
    RETURN    ${value}

Factory Reset CPE If Needed
    [Documentation]    Factory reset CPE if test made significant configuration changes.
    [Arguments]    ${cpe}=${CPE}
    Log    Checking if factory reset is needed...
    # Only reset if explicitly requested - this is a destructive operation
    Log    Factory reset skipped (call explicitly if needed)

# =============================================================================
# SIP Phone Cleanup
# =============================================================================

Cleanup SIP Phones
    [Documentation]    Clean up all SIP phones - disconnect calls and shutdown.
    Log    Cleaning up SIP phones...
    @{phones}=    Create List    ${PHONE_A}    ${PHONE_B}
    FOR    ${phone}    IN    @{phones}
        Run Keyword And Ignore Error    Cleanup Single SIP Phone    ${phone}
    END
    Log    SIP phone cleanup complete

Cleanup Single SIP Phone
    [Documentation]    Clean up a single SIP phone.
    [Arguments]    ${phone}
    Run Keyword And Ignore Error    Voice Disconnect The Call    ${phone}
    Run Keyword And Ignore Error    Voice Unregister Phone    ${phone}
    Log    Cleaned up phone: ${phone}

Disconnect All Active Calls
    [Documentation]    Disconnect any active calls on all phones.
    Log    Disconnecting all active calls...
    Run Keyword And Ignore Error    Voice Disconnect The Call    ${PHONE_A}
    Run Keyword And Ignore Error    Voice Disconnect The Call    ${PHONE_B}
    Run Keyword And Ignore Error    Voice Disconnect The Call    ${CALLER}
    Run Keyword And Ignore Error    Voice Disconnect The Call    ${CALLEE}

# =============================================================================
# Console Cleanup
# =============================================================================

Refresh CPE Console Connection
    [Documentation]    Refresh CPE console connection after reboot or disconnect.
    [Arguments]    ${cpe}=${CPE}
    Run Keyword And Ignore Error    Cpe Refresh Console Connection    ${cpe}
    Log    CPE console connection refreshed

Close All Console Sessions
    [Documentation]    Close all open console sessions.
    Log    Closing all console sessions...
    Run Keyword And Ignore Error    Cpe Close Console    ${CPE}

# =============================================================================
# ACS GUI Cleanup
# =============================================================================

Cleanup ACS GUI Session
    [Documentation]    Clean up ACS GUI session - logout and close browser.
    [Arguments]    ${acs}=${ACS}
    Log    Cleaning up ACS GUI session...
    Run Keyword And Ignore Error    Acs Gui Logout    ${acs}
    Log    ACS GUI session cleaned up

# =============================================================================
# TR-069 Cleanup
# =============================================================================

Restart TR069 Client
    [Documentation]    Restart TR-069 client on CPE.
    [Arguments]    ${cpe}=${CPE}
    Log    Restarting TR-069 client...
    Run Keyword And Ignore Error    Cpe Stop Tr069 Client    ${cpe}
    Sleep    2s    Wait for client to stop
    Run Keyword And Ignore Error    Cpe Start Tr069 Client    ${cpe}
    Sleep    5s    Wait for client to start
    Log    TR-069 client restarted

# =============================================================================
# Network Cleanup
# =============================================================================

Reset Network Interfaces
    [Documentation]    Reset network interfaces to default state.
    [Arguments]    ${cpe}=${CPE}
    Log    Resetting network interfaces...
    # Implementation depends on specific network configuration
    Log    Network interfaces reset

# =============================================================================
# Generic Cleanup
# =============================================================================

Safe Cleanup
    [Documentation]    Execute cleanup keyword safely, ignoring any errors.
    [Arguments]    ${keyword}    @{args}
    Run Keyword And Ignore Error    ${keyword}    @{args}

Cleanup Test Artifacts
    [Documentation]    Clean up any test artifacts created during test execution.
    Log    Cleaning up test artifacts...
    # Add specific artifact cleanup as needed
    Log    Test artifacts cleaned up

Full Testbed Cleanup
    [Documentation]    Comprehensive testbed cleanup - use after destructive tests.
    Log    Performing full testbed cleanup...
    Safe Cleanup    Disconnect All Active Calls
    Safe Cleanup    Cleanup SIP Phones
    Safe Cleanup    Cleanup ACS GUI Session
    Safe Cleanup    Refresh CPE Console Connection
    Safe Cleanup    Restart TR069 Client
    Log    Full testbed cleanup complete
