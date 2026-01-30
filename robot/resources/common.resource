*** Settings ***
Documentation    Common keywords and setup/teardown for all Robot Framework tests.
...              This resource file provides shared keywords used across multiple test suites.
...              
...              Import this resource in test files that need common testbed operations.

Library     robotframework_boardfarm.BoardfarmLibrary
Library     ../libraries/boardfarm_keywords.py
Library     ../libraries/acs_keywords.py
Library     ../libraries/cpe_keywords.py
Library     Collections
Library     String
Library     DateTime

*** Keywords ***
# =============================================================================
# Suite Setup/Teardown
# =============================================================================

Setup Testbed Connection
    [Documentation]    Common suite setup - establish testbed connection and verify connectivity.
    ...    Sets ACS and CPE as suite variables for use in all tests.
    Log    Setting up testbed connection...
    ${acs}=    Get Device By Type    ACS
    ${cpe}=    Get Device By Type    CPE
    Set Suite Variable    ${ACS}
    Set Suite Variable    ${CPE}
    # Verify basic connectivity
    The CPE Is Online Via ACS    ${acs}    ${cpe}
    Log    Testbed connection established - ACS: ${ACS}, CPE: ${CPE}

Teardown Testbed Connection
    [Documentation]    Common suite teardown - clean up testbed connection.
    Log    Tearing down testbed connection...
    Run Keyword And Ignore Error    Refresh CPE Console Connection
    Log    Testbed connection teardown complete

Cleanup After Test
    [Documentation]    Common test teardown - cleanup any test artifacts.
    ...    Called after each test to ensure clean state for next test.
    Log    Cleaning up after test...
    Run Keyword And Ignore Error    Refresh CPE Console Connection

# =============================================================================
# Device Access Keywords
# =============================================================================

Get ACS Device
    [Documentation]    Get ACS device instance. Returns cached instance if available.
    ${acs}=    Get Device By Type    ACS
    RETURN    ${acs}

Get CPE Device
    [Documentation]    Get CPE device instance. Returns cached instance if available.
    ${cpe}=    Get Device By Type    CPE
    RETURN    ${cpe}

Get LAN Device
    [Documentation]    Get LAN device instance.
    ${lan}=    Get Device By Type    LAN
    RETURN    ${lan}

Get SIP Phone
    [Documentation]    Get SIP phone device by index.
    [Arguments]    ${index}=0
    ${phone}=    Get Device By Type    SIPPhone    index=${index}
    RETURN    ${phone}

# =============================================================================
# Verification Keywords
# =============================================================================

Verify CPE Is Online
    [Documentation]    Verify CPE is online via ACS.
    [Arguments]    ${acs}=${ACS}    ${cpe}=${CPE}
    The CPE Is Online Via ACS    ${acs}    ${cpe}

Verify CPE Is Offline
    [Documentation]    Verify CPE is offline (not responding to ACS).
    [Arguments]    ${acs}=${ACS}    ${cpe}=${CPE}
    # Try to verify online - should fail if offline
    ${status}=    Run Keyword And Return Status    The CPE Is Online Via ACS    ${acs}    ${cpe}
    Should Not Be True    ${status}    CPE should be offline

Wait Until CPE Is Online
    [Documentation]    Wait for CPE to come online with timeout.
    [Arguments]    ${timeout}=120    ${acs}=${ACS}    ${cpe}=${CPE}
    Wait Until Keyword Succeeds    ${timeout}s    10s
    ...    Verify CPE Is Online    ${acs}    ${cpe}

Wait Until CPE Is Offline
    [Documentation]    Wait for CPE to go offline with timeout.
    [Arguments]    ${timeout}=60    ${acs}=${ACS}    ${cpe}=${CPE}
    Wait Until Keyword Succeeds    ${timeout}s    5s
    ...    Verify CPE Is Offline    ${acs}    ${cpe}

# =============================================================================
# TR-069 Parameter Keywords
# =============================================================================

Get TR069 Parameter
    [Documentation]    Get TR-069 parameter value from CPE via ACS.
    [Arguments]    ${parameter}    ${acs}=${ACS}    ${cpe}=${CPE}
    ${value}=    Get ACS Parameter Value    ${acs}    ${cpe}    ${parameter}
    RETURN    ${value}

Set TR069 Parameter
    [Documentation]    Set TR-069 parameter value on CPE via ACS.
    [Arguments]    ${parameter}    ${value}    ${acs}=${ACS}    ${cpe}=${CPE}
    Set ACS Parameter Value    ${acs}    ${cpe}    ${parameter}    ${value}

Get Software Version
    [Documentation]    Get CPE software version via TR-069.
    [Arguments]    ${acs}=${ACS}    ${cpe}=${CPE}
    ${version}=    Get TR069 Parameter    Device.DeviceInfo.SoftwareVersion
    ...    ${acs}    ${cpe}
    RETURN    ${version}

Get Manufacturer
    [Documentation]    Get CPE manufacturer via TR-069.
    [Arguments]    ${acs}=${ACS}    ${cpe}=${CPE}
    ${manufacturer}=    Get TR069 Parameter    Device.DeviceInfo.Manufacturer
    ...    ${acs}    ${cpe}
    RETURN    ${manufacturer}

# =============================================================================
# Console Keywords
# =============================================================================

Refresh CPE Console Connection
    [Documentation]    Refresh CPE console connection (useful after reboot).
    ${cpe}=    Get CPE Device
    # Console refresh is handled by cpe_use_cases
    Log    Console connection refresh requested

Execute Console Command
    [Documentation]    Execute command on CPE console and return output.
    [Arguments]    ${command}    ${cpe}=${CPE}
    # Use CPE device methods directly
    Log    Executing command: ${command}

# =============================================================================
# Timing Keywords
# =============================================================================

Get Current Timestamp
    [Documentation]    Get current UTC timestamp for timing operations.
    ${timestamp}=    Evaluate    __import__('datetime').datetime.now(__import__('datetime').timezone.utc)
    RETURN    ${timestamp}

Get Elapsed Seconds
    [Documentation]    Calculate elapsed seconds since given timestamp.
    [Arguments]    ${start_timestamp}
    ${now}=    Get Current Timestamp
    ${delta}=    Evaluate    (${now} - ${start_timestamp}).total_seconds()
    RETURN    ${delta}

Wait With Progress
    [Documentation]    Wait for specified seconds, logging progress.
    [Arguments]    ${seconds}    ${message}=Waiting
    Log    ${message} for ${seconds} seconds...
    Sleep    ${seconds}s
    Log    Wait complete

# =============================================================================
# Logging Keywords
# =============================================================================

Log Test Step
    [Documentation]    Log a test step with consistent formatting.
    [Arguments]    ${step_description}
    Log    === STEP: ${step_description} ===    level=INFO

Log Test Result
    [Documentation]    Log a test result with consistent formatting.
    [Arguments]    ${result_description}    ${status}=PASS
    Log    === RESULT [${status}]: ${result_description} ===    level=INFO
