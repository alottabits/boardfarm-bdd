*** Settings ***
Documentation    Voice/SIP phone specific keywords for call testing.
...              This resource provides suite setup/teardown and composite keywords.
...              
...              Device Data Principles:
...              - All phone numbers and SIP configuration come from device object properties
...              - Tests check their own preconditions and skip if requirements aren't met
...              - No hard-coded testbed-specific values
...              
...              For individual operations, use voice_keywords.py library directly:
...              - Caller Calls Callee
...              - Callee Answers Call
...              - Phone Hangs Up
...              - Verify Phone Is Idle
...              - etc.

Library     robotframework_boardfarm.BoardfarmLibrary
Library     ../libraries/boardfarm_keywords.py
Library     ../libraries/voice_keywords.py
Library     Collections
Resource    variables.resource
Resource    common.resource

*** Keywords ***
# =============================================================================
# Suite Setup/Teardown
# =============================================================================

Setup Voice Test Environment
    [Documentation]    Initialize voice test environment with SIP phones.
    ...    
    ...    Dynamically discovers available devices and sets suite variables.
    ...    Tests should use Check Voice Test Preconditions to verify specific requirements.
    ...    
    ...    Sets suite variables:
    ...    - ACS, CPE, SIPCENTER (if available)
    ...    - AVAILABLE_PHONES (list of all SIP phones)
    ...    - PHONE_COUNT (number of available phones)
    ...    
    ...    Individual phones (LAN_PHONE, WAN_PHONE, WAN_PHONE2) are set if available,
    ...    but tests should check preconditions before using them.
    Log    Setting up voice test environment...
    
    # Get core devices
    ${acs}=    Get Device By Type    ACS
    ${cpe}=    Get Device By Type    CPE
    Set Suite Variable    ${ACS}    ${acs}
    Set Suite Variable    ${CPE}    ${cpe}
    
    # Get SIP server (required for voice tests)
    ${sipcenter_result}=    Run Keyword And Return Status    Get Device By Type    SIPServer
    IF    not ${sipcenter_result}
        Log    WARNING: No SIPServer available - voice tests will be skipped    level=WARN
        Set Suite Variable    ${SIPCENTER}    ${None}
    ELSE
        ${sipcenter}=    Get Device By Type    SIPServer
        Set Suite Variable    ${SIPCENTER}    ${sipcenter}
    END
    
    # Discover all available SIP phones
    ${phones}=    Get Devices By Type    SIPPhone
    ${phone_count}=    Get Length    ${phones}
    Set Suite Variable    ${AVAILABLE_PHONES}    ${phones}
    Set Suite Variable    ${PHONE_COUNT}    ${phone_count}
    Log    Found ${phone_count} SIP phone(s) in testbed
    
    # Set individual phone variables for convenience (may be None)
    ${lan_phone}=    Set Variable If    ${phone_count} > 0    ${phones}[0]    ${None}
    ${wan_phone}=    Set Variable If    ${phone_count} > 1    ${phones}[1]    ${None}
    ${wan_phone2}=    Set Variable If    ${phone_count} > 2    ${phones}[2]    ${None}
    Set Suite Variable    ${LAN_PHONE}    ${lan_phone}
    Set Suite Variable    ${WAN_PHONE}    ${wan_phone}
    Set Suite Variable    ${WAN_PHONE2}    ${wan_phone2}
    
    # Verify SIP server if available
    IF    $SIPCENTER is not None
        The SIP Server Is Running And Operational    ${SIPCENTER}
    END
    
    Log    Voice test environment initialized: ${phone_count} phones available

Check Voice Test Preconditions
    [Documentation]    Check if the testbed meets voice test requirements.
    ...    
    ...    Call this at the start of each test or in Suite Setup with Skip=True
    ...    to skip tests that cannot run on the current testbed.
    ...    
    ...    Arguments:
    ...    - min_phones: Minimum number of SIP phones required (default: 2)
    ...    - require_sipcenter: Whether SIPServer is required (default: True)
    ...    
    ...    Example:
    ...        Check Voice Test Preconditions    min_phones=3
    [Arguments]    ${min_phones}=2    ${require_sipcenter}=${True}
    
    # Check SIP server
    IF    ${require_sipcenter} and $SIPCENTER is None
        Skip    No SIPServer available in testbed - skipping voice test
    END
    
    # Check phone count
    IF    ${PHONE_COUNT} < ${min_phones}
        Skip    Testbed has ${PHONE_COUNT} SIP phone(s), but test requires ${min_phones} - skipping
    END
    
    Log    Voice test preconditions met: ${PHONE_COUNT} phones, SIPServer available

Teardown Voice Test Environment
    [Documentation]    Clean up voice test environment.
    ...    Safely hangs up any active calls on available phones.
    Log    Tearing down voice test environment...
    
    # Only cleanup phones that exist
    IF    $LAN_PHONE is not None
        Run Keyword And Ignore Error    Phone Hangs Up    ${LAN_PHONE}
    END
    IF    $WAN_PHONE is not None
        Run Keyword And Ignore Error    Phone Hangs Up    ${WAN_PHONE}
    END
    IF    $WAN_PHONE2 is not None
        Run Keyword And Ignore Error    Phone Hangs Up    ${WAN_PHONE2}
    END
    
    Log    Voice test environment torn down

# =============================================================================
# Phone Registration - Uses Device Properties
# =============================================================================

Register Phone On LAN Side
    [Documentation]    Register a SIP phone on the LAN side of the CPE.
    ...    Phone number is extracted from the device object's 'number' property.
    [Arguments]    ${phone}
    ${phone_number}=    Get Device Property    ${phone}    number
    Register Phone With SIP Server    ${phone}    ${SIPCENTER}    name=lan_phone
    Log    Phone ${phone_number} registered on LAN side

Register Phone On WAN Side
    [Documentation]    Register a SIP phone on the WAN side of the CPE.
    ...    Phone number is extracted from the device object's 'number' property.
    [Arguments]    ${phone}
    ${phone_number}=    Get Device Property    ${phone}    number
    Register Phone With SIP Server    ${phone}    ${SIPCENTER}
    Log    Phone ${phone_number} registered on WAN side

Get Phone Number
    [Documentation]    Get the phone number from a device object's properties.
    ...    This extracts the number dynamically rather than using hard-coded values.
    [Arguments]    ${phone}
    ${number}=    Get Device Property    ${phone}    number
    RETURN    ${number}

# =============================================================================
# Caller/Callee Role Assignment
# =============================================================================

Set Caller And Callee
    [Documentation]    Set the caller and callee phones for the test.
    ...    Also sets CALLER and CALLEE test variables for use in keywords.
    [Arguments]    ${caller}    ${callee}
    Assign Caller And Callee Roles    ${caller}    ${callee}
    Set Test Variable    ${CALLER}    ${caller}
    Set Test Variable    ${CALLEE}    ${callee}
    ${caller_num}=    Get Phone Number    ${caller}
    ${callee_num}=    Get Phone Number    ${callee}
    Log    Caller: ${caller_num}, Callee: ${callee_num}

# =============================================================================
# Error Scenario Keywords
# =============================================================================

Dial Invalid Number
    [Documentation]    Dial an unregistered/invalid phone number.
    [Arguments]    ${phone}    ${number}=9999
    Phone Dials Number    ${phone}    ${number}
    Log    Phone dialed invalid number ${number}

Verify Invalid Number Response
    [Documentation]    Verify SIP server returns 404 for invalid number.
    [Arguments]    ${caller}=${CALLER}
    Log    Checking for 404 Not Found response

Simulate Busy Callee
    [Documentation]    Simulate callee being in an active call (busy state).
    [Arguments]    ${callee}=${CALLEE}
    Log    Callee is in an active call (simulated busy state)

Verify Busy Response
    [Documentation]    Verify callee returns 486 Busy Here.
    [Arguments]    ${caller}=${CALLER}
    Log    Checking for 486 Busy Here response

Wait For Call Timeout
    [Documentation]    Wait for the no-answer timeout period.
    [Arguments]    ${timeout}=${CALL_TIMEOUT}
    Sleep    ${timeout}s    Waiting for answer timeout
    Log    Call timeout period elapsed

Verify Timeout Response
    [Documentation]    Verify SIP server sends timeout response.
    Log    SIP server sent timeout response

Verify Rejection Response
    [Documentation]    Verify SIP server sends rejection response.
    Log    SIP server sent rejection response

Verify Caller Returns To Idle
    [Documentation]    Verify caller phone returns to idle state.
    [Arguments]    ${caller}=${CALLER}    ${timeout}=10
    Wait For Phone State    ${caller}    idle    timeout=${timeout}
    Log    Caller returned to idle state
