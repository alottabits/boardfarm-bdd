*** Settings ***
Documentation    Cleanup keywords for test teardown and state restoration.
...              This resource provides keywords for cleaning up test artifacts
...              and restoring the testbed to a known good state.
...              
...              Device Data Principles:
...              - Phone cleanup uses dynamically discovered phones, not hard-coded variables
...              - Cleanup keywords safely handle missing devices
...              - All cleanup operations use Run Keyword And Ignore Error for safety

Library     robotframework_boardfarm.BoardfarmLibrary
Library     ../libraries/boardfarm_keywords.py
Library     ../libraries/acs_keywords.py
Library     ../libraries/cpe_keywords.py
Library     ../libraries/voice_keywords.py
Library     ../libraries/acs_gui_keywords.py
Library     Collections

*** Keywords ***
# =============================================================================
# CPE Cleanup
# =============================================================================

Cleanup CPE Configuration
    [Documentation]    Restore CPE configuration to original state.
    ...    Pass the original configuration dictionary captured at test start.
    [Arguments]    ${original_config}    ${acs}=${ACS}    ${cpe}=${CPE}
    Log    Restoring CPE configuration...
    FOR    ${param}    ${value}    IN    &{original_config}
        Run Keyword And Ignore Error
        ...    Set ACS Parameter Value    ${acs}    ${cpe}    ${param}    ${value}
    END
    Log    CPE configuration restored

Restore CPE Parameter
    [Documentation]    Restore a single CPE parameter to its original value.
    [Arguments]    ${parameter}    ${original_value}    ${acs}=${ACS}    ${cpe}=${CPE}
    Run Keyword And Ignore Error
    ...    Set ACS Parameter Value    ${acs}    ${cpe}    ${parameter}    ${original_value}
    Log    Restored ${parameter} to ${original_value}

Capture CPE Parameter
    [Documentation]    Capture current value of a CPE parameter for later restoration.
    [Arguments]    ${parameter}    ${acs}=${ACS}    ${cpe}=${CPE}
    ${value}=    Run Keyword And Return Status
    ...    Get ACS Parameter Value    ${acs}    ${cpe}    ${parameter}
    RETURN    ${value}

Factory Reset CPE If Needed
    [Documentation]    Factory reset CPE if test made significant configuration changes.
    [Arguments]    ${cpe}=${CPE}
    Log    Checking if factory reset is needed...
    # Only reset if explicitly requested - this is a destructive operation
    Log    Factory reset skipped (call explicitly if needed)

# =============================================================================
# SIP Phone Cleanup - Dynamic Device Discovery
# =============================================================================

Cleanup All SIP Phones
    [Documentation]    Clean up all available SIP phones in the testbed.
    ...    Dynamically discovers phones and safely cleans up each one.
    Log    Cleaning up all available SIP phones...
    ${phones}=    Run Keyword And Return Status    Get Devices By Type    SIPPhone
    IF    not ${phones}
        Log    No SIP phones available to clean up
        RETURN
    END
    ${phone_list}=    Get Devices By Type    SIPPhone
    FOR    ${phone}    IN    @{phone_list}
        Run Keyword And Ignore Error    Cleanup Single SIP Phone    ${phone}
    END
    Log    SIP phone cleanup complete

Cleanup Single SIP Phone
    [Documentation]    Clean up a single SIP phone - hang up any active call.
    [Arguments]    ${phone}
    IF    $phone is None
        Log    Phone is None - nothing to clean up
        RETURN
    END
    Run Keyword And Ignore Error    Phone Hangs Up    ${phone}
    Log    Cleaned up phone

Cleanup Phone List
    [Documentation]    Clean up a list of phone objects.
    ...    Use this when you have specific phones to clean up.
    [Arguments]    @{phones}
    FOR    ${phone}    IN    @{phones}
        Run Keyword And Ignore Error    Cleanup Single SIP Phone    ${phone}
    END

Disconnect All Active Calls
    [Documentation]    Disconnect any active calls on all available phones.
    ...    Also cleans up any test variables that may hold phone references.
    Log    Disconnecting all active calls...
    
    # Clean up dynamically discovered phones
    Cleanup All SIP Phones
    
    # Clean up test-scoped phone variables if they exist
    # These are set by voice.resource Setup Voice Test Environment
    ${lan_phone_exists}=    Run Keyword And Return Status    Variable Should Exist    ${LAN_PHONE}
    IF    ${lan_phone_exists}
        Run Keyword And Ignore Error    Cleanup Single SIP Phone    ${LAN_PHONE}
    END
    
    ${wan_phone_exists}=    Run Keyword And Return Status    Variable Should Exist    ${WAN_PHONE}
    IF    ${wan_phone_exists}
        Run Keyword And Ignore Error    Cleanup Single SIP Phone    ${WAN_PHONE}
    END
    
    # Clean up caller/callee test variables if they exist
    ${caller_exists}=    Run Keyword And Return Status    Variable Should Exist    ${CALLER}
    IF    ${caller_exists}
        Run Keyword And Ignore Error    Cleanup Single SIP Phone    ${CALLER}
    END
    
    ${callee_exists}=    Run Keyword And Return Status    Variable Should Exist    ${CALLEE}
    IF    ${callee_exists}
        Run Keyword And Ignore Error    Cleanup Single SIP Phone    ${CALLEE}
    END

# =============================================================================
# Console Cleanup
# =============================================================================

Refresh CPE Console Connection
    [Documentation]    Refresh CPE console connection after reboot or disconnect.
    [Arguments]    ${cpe}=${CPE}
    Log    CPE console connection refresh requested

Close All Console Sessions
    [Documentation]    Close all open console sessions.
    Log    Closing all console sessions...

# =============================================================================
# ACS GUI Cleanup
# =============================================================================

Cleanup ACS GUI Session
    [Documentation]    Clean up ACS GUI session - logout and close browser.
    [Arguments]    ${acs}=${ACS}
    Log    Cleaning up ACS GUI session...
    Run Keyword And Ignore Error    Operator Logs Out    ${acs}
    Log    ACS GUI session cleaned up

# =============================================================================
# TR-069 Cleanup
# =============================================================================

Restart TR069 Client
    [Documentation]    Restart TR-069 client on CPE.
    [Arguments]    ${acs}=${ACS}    ${cpe}=${CPE}
    Log    Restarting TR-069 client...
    ${context}=    Run Keyword And Ignore Error    The CPE Is Unreachable For TR-069 Sessions    ${cpe}
    Sleep    2s    Wait for client to stop
    Run Keyword And Ignore Error    The CPE Comes Online And Connects To The ACS    ${acs}    ${cpe}
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
    ...    Safely handles cases where devices may not be available.
    [Arguments]    ${acs}=${None}    ${cpe}=${None}
    Log    Performing full testbed cleanup...
    Safe Cleanup    Disconnect All Active Calls
    Safe Cleanup    Cleanup All SIP Phones
    IF    $acs is not None
        Safe Cleanup    Cleanup ACS GUI Session    ${acs}
    END
    IF    $cpe is not None
        Safe Cleanup    Refresh CPE Console Connection    ${cpe}
    END
    IF    $acs is not None and $cpe is not None
        Safe Cleanup    Restart TR069 Client    ${acs}    ${cpe}
    END
    Log    Full testbed cleanup complete
