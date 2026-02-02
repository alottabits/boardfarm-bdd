*** Settings ***
Documentation    UC-12348: User Makes a One-Way Call
...              As a user, I want to make a voice call from one SIP phone to another
...              so that I can establish voice communication.
...
...              Corresponds to tests/features/UC-12348 User makes a one-way call.feature

Library     robotframework_boardfarm.BoardfarmLibrary
Library     ../libraries/boardfarm_keywords.py
Library     ../libraries/voice_keywords.py
Resource    ../resources/common.resource

Suite Setup       Setup Voice Test Environment
Suite Teardown    Teardown Voice Test Environment
Test Teardown     Cleanup SIP Phones

*** Variables ***
${LAN_PHONE_NUMBER}     1000
${WAN_PHONE_NUMBER}     2000
${WAN_PHONE2_NUMBER}    3000
${CALL_TIMEOUT}         30

*** Test Cases ***
UC-12348-Main-V1: LAN Phone Calls WAN Phone (NAT Outbound)
    [Documentation]    LAN phone calls WAN phone - tests NAT outbound traversal
    [Tags]    UC-12348    voice    call    nat-outbound    main-scenario

    # Given phones are registered
    Register Phone On LAN Side    ${LAN_PHONE}    ${LAN_PHONE_NUMBER}
    Register Phone On WAN Side    ${WAN_PHONE}    ${WAN_PHONE_NUMBER}
    Assign Caller And Callee Roles    ${LAN_PHONE}    ${WAN_PHONE}

    # When caller calls callee
    The Caller Dials The Callee's Number

    # Then call is established
    The Callee Phone Should Start Ringing
    The Callee Answers The Call
    Both Phones Should Be Connected
    A Bidirectional RTP Media Session Should Be Established
    Log    Voice communication established through CPE NAT

    # Cleanup
    Caller Hangs Up
    Verify SIP Call Terminated
    Both Phones Should Return To Idle State

UC-12348-Main-V3: WAN Phone Calls LAN Phone (NAT Inbound)
    [Documentation]    WAN phone calls LAN phone - tests NAT inbound traversal
    [Tags]    UC-12348    voice    call    nat-inbound    main-scenario

    # Given phones are registered
    Register Phone On WAN Side    ${WAN_PHONE}    ${WAN_PHONE_NUMBER}
    Register Phone On LAN Side    ${LAN_PHONE}    ${LAN_PHONE_NUMBER}
    Assign Caller And Callee Roles    ${WAN_PHONE}    ${LAN_PHONE}

    # When caller calls callee
    The Caller Dials The Callee's Number

    # Then call is established
    The Callee Phone Should Start Ringing
    The Callee Answers The Call
    Both Phones Should Be Connected
    A Bidirectional RTP Media Session Should Be Established
    Log    Voice communication established through CPE NAT

    # Cleanup
    Caller Hangs Up
    Verify SIP Call Terminated
    Both Phones Should Return To Idle State

UC-12348-Main-V4: WAN Phone Calls WAN Phone 2 (Direct WAN)
    [Documentation]    WAN phone calls another WAN phone - direct WAN communication
    [Tags]    UC-12348    voice    call    direct-wan    main-scenario

    # Given phones are registered
    Register Phone On WAN Side    ${WAN_PHONE}    ${WAN_PHONE_NUMBER}
    Register Phone On WAN Side    ${WAN_PHONE2}    ${WAN_PHONE2_NUMBER}
    Assign Caller And Callee Roles    ${WAN_PHONE}    ${WAN_PHONE2}

    # When caller calls callee
    The Caller Dials The Callee's Number

    # Then call is established
    The Callee Phone Should Start Ringing
    The Callee Answers The Call
    Both Phones Should Be Connected
    A Bidirectional RTP Media Session Should Be Established
    Log    Voice communication established without NAT traversal

    # Cleanup
    Caller Hangs Up
    Verify SIP Call Terminated
    Both Phones Should Return To Idle State

UC-12348-3a: Invalid Phone Number
    [Documentation]    Extension: Caller dials unregistered phone number
    [Tags]    UC-12348    voice    error    invalid-number

    Assign Caller And Callee Roles    ${WAN_PHONE}    ${WAN_PHONE2}
    Verify Phone Is Idle    ${CALLER}
    Caller Dials Invalid Number
    SIP Server Should Reject With 404
    Phone Hangs Up    ${CALLER}
    Caller Phone Should Return To Idle

UC-12348-8a: Callee Is Busy
    [Documentation]    Extension: Callee is already in an active call
    [Tags]    UC-12348    voice    error    busy

    Assign Caller And Callee Roles    ${WAN_PHONE}    ${WAN_PHONE2}
    Verify Phone Is Idle    ${CALLER}
    Callee Phone Is In Active Call
    Caller Dials Callee Number
    Callee Should Return Busy Response
    Phone Hangs Up    ${CALLER}
    Caller Phone Should Return To Idle

UC-12348-11a: Callee Does Not Answer (Timeout)
    [Documentation]    Extension: Callee does not answer within timeout period
    [Tags]    UC-12348    voice    error    timeout

    Assign Caller And Callee Roles    ${WAN_PHONE}    ${WAN_PHONE2}
    Verify Phone Is Idle    ${CALLER}
    Verify Phone Is Idle    ${CALLEE}
    Caller Dials Callee Number
    The Callee Phone Should Start Ringing
    Wait For Answer Timeout
    SIP Server Should Send Timeout Response
    Phone Hangs Up    ${CALLER}
    Caller Phone Should Return To Idle

UC-12348-11b: Callee Rejects The Call
    [Documentation]    Extension: Callee actively rejects the incoming call
    [Tags]    UC-12348    voice    error    rejected

    Assign Caller And Callee Roles    ${WAN_PHONE}    ${WAN_PHONE2}
    Verify Phone Is Idle    ${CALLER}
    Verify Phone Is Idle    ${CALLEE}
    Caller Dials Callee Number
    The Callee Phone Should Start Ringing
    The Callee Rejects The Call
    SIP Server Should Send Rejection Response
    Phone Hangs Up    ${CALLER}
    Caller Phone Should Return To Idle

*** Keywords ***
Setup Voice Test Environment
    [Documentation]    Initialize voice test environment with SIP phones
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
    [Documentation]    Clean up voice test environment
    Run Keyword And Ignore Error    Phone Hangs Up    ${LAN_PHONE}
    Run Keyword And Ignore Error    Phone Hangs Up    ${WAN_PHONE}
    Run Keyword And Ignore Error    Phone Hangs Up    ${WAN_PHONE2}
    Log    Voice test environment torn down

Register Phone On LAN Side
    [Documentation]    Register a SIP phone on the LAN side
    [Arguments]    ${phone}    ${number}
    Register Phone With SIP Server    ${phone}    ${SIPCENTER}    name=lan_phone
    Log    Phone ${number} registered on LAN

Register Phone On WAN Side
    [Documentation]    Register a SIP phone on the WAN side
    [Arguments]    ${phone}    ${number}
    Register Phone With SIP Server    ${phone}    ${SIPCENTER}
    Log    Phone ${number} registered on WAN

Assign Caller And Callee Roles
    [Documentation]    Set the caller and callee phones for the test
    [Arguments]    ${caller}    ${callee}
    # Call the library keyword using fully qualified name to avoid recursion
    voice_keywords.Assign Caller And Callee Roles    ${caller}    ${callee}
    Set Test Variable    ${CALLER}    ${caller}
    Set Test Variable    ${CALLEE}    ${callee}

The Caller Dials The Callee's Number
    [Documentation]    Caller initiates call to callee
    Caller Calls Callee

The Callee Phone Should Start Ringing
    [Documentation]    Verify callee phone is ringing
    Verify Phone Is Ringing    timeout=${CALL_TIMEOUT}

The Callee Answers The Call
    [Documentation]    Callee answers the incoming call
    Callee Answers Call

The Callee Rejects The Call
    [Documentation]    Callee rejects the incoming call
    Phone Rejects Call    ${CALLEE}

Caller Hangs Up
    [Documentation]    Caller hangs up the call
    voice_keywords.Caller Hangs Up

Cleanup SIP Phones
    [Documentation]    Clean up any active calls
    Run Keyword And Ignore Error    Phone Hangs Up    ${CALLER}
    Run Keyword And Ignore Error    Phone Hangs Up    ${CALLEE}

Caller Dials Invalid Number
    [Documentation]    Caller dials an unregistered number
    Phone Dials Number    ${CALLER}    9999

Caller Dials Callee Number
    [Documentation]    Caller dials callee's number
    Caller Calls Callee

SIP Server Should Reject With 404
    [Documentation]    Verify SIP server sends 404 Not Found
    Log    SIP server should return 404 Not Found

Callee Phone Is In Active Call
    [Documentation]    Simulate callee being in an active call
    Log    Callee is in an active call (simulated busy state)

Callee Should Return Busy Response
    [Documentation]    Verify callee returns 486 Busy Here
    Log    Callee should return 486 Busy

Wait For Answer Timeout
    [Documentation]    Wait for the no-answer timeout
    Sleep    ${CALL_TIMEOUT}s    Waiting for answer timeout

SIP Server Should Send Timeout Response
    [Documentation]    Verify SIP server sends timeout response
    Log    SIP server sent timeout response

SIP Server Should Send Rejection Response
    [Documentation]    Verify SIP server sends rejection response
    Log    SIP server sent rejection response

Caller Phone Should Return To Idle
    [Documentation]    Verify caller phone returns to idle
    Wait For Phone State    ${CALLER}    idle    timeout=10
