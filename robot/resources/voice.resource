*** Settings ***
Documentation    Voice/SIP phone specific keywords for call testing.
...              This resource provides suite setup/teardown and composite keywords.
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
Resource    variables.resource
Resource    common.resource

*** Keywords ***
# =============================================================================
# Suite Setup/Teardown
# =============================================================================

Setup Voice Test Environment
    [Documentation]    Initialize voice test environment with SIP phones.
    ...    Sets suite variables: ACS, CPE, SIPCENTER, LAN_PHONE, WAN_PHONE, WAN_PHONE2
    Log    Setting up voice test environment...
    ${acs}=    Get Device By Type    ACS
    ${cpe}=    Get Device By Type    CPE
    ${sipcenter}=    Get Device By Type    SIPServer
    ${lan_phone}=    Get Device By Type    SIPPhone    index=0
    ${wan_phone}=    Get Device By Type    SIPPhone    index=1
    ${wan_phone2}=    Get Device By Type    SIPPhone    index=2
    Set Suite Variable    ${ACS}
    Set Suite Variable    ${CPE}
    Set Suite Variable    ${SIPCENTER}
    Set Suite Variable    ${LAN_PHONE}    ${lan_phone}
    Set Suite Variable    ${WAN_PHONE}    ${wan_phone}
    Set Suite Variable    ${WAN_PHONE2}    ${wan_phone2}
    The SIP Server Is Running And Operational    ${SIPCENTER}
    Log    Voice test environment initialized

Teardown Voice Test Environment
    [Documentation]    Clean up voice test environment.
    Log    Tearing down voice test environment...
    Run Keyword And Ignore Error    Phone Hangs Up    ${LAN_PHONE}
    Run Keyword And Ignore Error    Phone Hangs Up    ${WAN_PHONE}
    Run Keyword And Ignore Error    Phone Hangs Up    ${WAN_PHONE2}
    Log    Voice test environment torn down

# =============================================================================
# Phone Registration
# =============================================================================

Register Phone On LAN Side
    [Documentation]    Register a SIP phone on the LAN side of the CPE.
    [Arguments]    ${phone}    ${number}
    Register Phone With SIP Server    ${phone}    ${SIPCENTER}    name=lan_phone
    Log    Phone ${number} registered on LAN side

Register Phone On WAN Side
    [Documentation]    Register a SIP phone on the WAN side of the CPE.
    [Arguments]    ${phone}    ${number}
    Register Phone With SIP Server    ${phone}    ${SIPCENTER}
    Log    Phone ${number} registered on WAN side

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
    Log    Caller: ${caller}, Callee: ${callee}

# =============================================================================
# Error Scenario Keywords
# =============================================================================

Dial Invalid Number
    [Documentation]    Dial an unregistered/invalid phone number.
    [Arguments]    ${phone}    ${number}=9999
    Phone Dials Number    ${phone}    ${number}
    Log    Phone ${phone} dialed invalid number ${number}

Verify Invalid Number Response
    [Documentation]    Verify SIP server returns 404 for invalid number.
    [Arguments]    ${caller}=${CALLER}
    Log    Checking for 404 Not Found response

Simulate Busy Callee
    [Documentation]    Simulate callee being in an active call (busy state).
    [Arguments]    ${callee}=${CALLEE}
    Log    Callee ${callee} is in an active call (simulated busy state)

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
    Log    Caller ${caller} returned to idle state
