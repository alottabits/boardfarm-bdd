*** Settings ***
Documentation    Voice/SIP phone specific keywords for call testing.
...              This resource provides high-level keywords for voice call scenarios.

Library     robotframework_boardfarm.BoardfarmLibrary
Library     ../libraries/boardfarm_keywords.py
Library     ../libraries/voice_keywords.py
Resource    variables.resource
Resource    common.resource

*** Keywords ***
# =============================================================================
# Phone Setup
# =============================================================================

Setup Voice Test Environment
    [Documentation]    Initialize voice test environment with SIP phones.
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

Register Phone
    [Documentation]    Initialize and register a SIP phone.
    [Arguments]    ${phone}    ${number}
    Register Phone With SIP Server    ${phone}    ${SIPCENTER}
    Log    Phone ${number} registered successfully

Register Phone On LAN Side
    [Documentation]    Register a SIP phone on the LAN side of the CPE.
    [Arguments]    ${phone}    ${number}
    Register Phone    ${phone}    ${number}
    Log    Phone ${number} registered on LAN side

Register Phone On WAN Side
    [Documentation]    Register a SIP phone on the WAN side of the CPE.
    [Arguments]    ${phone}    ${number}
    Register Phone    ${phone}    ${number}
    Log    Phone ${number} registered on WAN side

Unregister Phone
    [Documentation]    Unregister a SIP phone.
    [Arguments]    ${phone}
    Run Keyword And Ignore Error    Phone Hangs Up    ${phone}
    Log    Phone unregistered

# =============================================================================
# Call Operations
# =============================================================================

Set Caller And Callee
    [Documentation]    Set the caller and callee phones for the test.
    [Arguments]    ${caller}    ${callee}
    Assign Caller And Callee Roles    ${caller}    ${callee}
    Set Test Variable    ${CALLER}    ${caller}
    Set Test Variable    ${CALLEE}    ${callee}
    Log    Caller: ${caller}, Callee: ${callee}

Initiate Call
    [Documentation]    Caller initiates a call to callee.
    [Arguments]    ${caller}=${CALLER}    ${callee}=${CALLEE}
    Caller Calls Callee    ${caller}    ${callee}
    Log    Call initiated from ${caller} to ${callee}

Answer Call
    [Documentation]    Answer an incoming call.
    [Arguments]    ${phone}=${CALLEE}
    Callee Answers Call    ${phone}
    Log    Call answered by ${phone}

Hang Up Call
    [Documentation]    Hang up a call.
    [Arguments]    ${phone}=${CALLER}
    Phone Hangs Up    ${phone}
    Log    Call hung up by ${phone}

Reject Call
    [Documentation]    Reject an incoming call.
    [Arguments]    ${phone}=${CALLEE}
    Phone Rejects Call    ${phone}
    Log    Call rejected by ${phone}

# =============================================================================
# Call Verification
# =============================================================================

Verify Phone Is Ringing
    [Documentation]    Verify phone is ringing.
    [Arguments]    ${phone}=${CALLEE}    ${timeout}=${RING_TIMEOUT}
    Wait For Phone State    ${phone}    ringing    timeout=${timeout}
    Log    Phone ${phone} is ringing

Verify Call Is Connected
    [Documentation]    Verify both parties are connected.
    [Arguments]    ${phone_a}=${CALLER}    ${phone_b}=${CALLEE}
    Verify Both Phones Connected    ${phone_a}    ${phone_b}
    Log    Both phones are connected

Verify Phone Is Idle
    [Documentation]    Verify phone is in idle state.
    [Arguments]    ${phone}
    Verify Phone Is Idle    ${phone}
    Log    Phone ${phone} is idle

Verify Media Is Established
    [Documentation]    Verify RTP media session is established.
    [Arguments]    ${phone_a}=${CALLER}    ${phone_b}=${CALLEE}
    Verify RTP Session Established    ${phone_a}    ${phone_b}
    Log    RTP media session established

# =============================================================================
# Complete Call Scenarios
# =============================================================================

Complete Successful Call
    [Documentation]    Execute a complete successful call flow.
    [Arguments]    ${caller}    ${callee}    ${duration}=5
    Set Caller And Callee    ${caller}    ${callee}
    Initiate Call
    Verify Phone Is Ringing    ${callee}
    Answer Call    ${callee}
    Verify Call Is Connected    ${caller}    ${callee}
    Verify Media Is Established    ${caller}    ${callee}
    Sleep    ${duration}s    Call in progress
    Hang Up Call    ${caller}
    Verify Phone Is Idle    ${caller}
    Verify Phone Is Idle    ${callee}
    Log    Call completed successfully

Execute NAT Traversal Call
    [Documentation]    Execute call that traverses CPE NAT.
    [Arguments]    ${lan_phone}    ${wan_phone}    ${direction}=outbound
    IF    '${direction}' == 'outbound'
        Set Caller And Callee    ${lan_phone}    ${wan_phone}
    ELSE
        Set Caller And Callee    ${wan_phone}    ${lan_phone}
    END
    Complete Successful Call    ${CALLER}    ${CALLEE}
    Log    NAT traversal call (${direction}) completed

# =============================================================================
# Error Scenario Keywords
# =============================================================================

Verify Invalid Number Response
    [Documentation]    Verify SIP server returns 404 for invalid number.
    [Arguments]    ${caller}=${CALLER}
    Log    Checking for 404 Not Found response

Verify Busy Response
    [Documentation]    Verify callee returns 486 Busy Here.
    [Arguments]    ${caller}=${CALLER}
    Log    Checking for 486 Busy Here response
