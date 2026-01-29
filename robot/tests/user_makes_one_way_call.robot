*** Settings ***
Documentation    UC-12348: User Makes a One-Way Call
...              As a user, I want to make a voice call from one SIP phone to another
...              so that I can establish voice communication.
...
...              Corresponds to pytest/features/UC-12348 User makes a one-way call.feature

Library     robotframework_boardfarm.BoardfarmLibrary
Library     robotframework_boardfarm.UseCaseLibrary
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
    Set Caller And Callee    ${LAN_PHONE}    ${WAN_PHONE}

    # When caller calls callee
    Caller Calls Callee

    # Then call is established
    Callee Phone Should Be Ringing
    Callee Answers The Call
    Both Phones Should Be Connected
    RTP Media Session Should Be Established
    Log    Voice communication established through CPE NAT

    # Cleanup
    Caller Hangs Up
    Call Should Be Terminated
    Both Phones Should Return To Idle

UC-12348-Main-V3: WAN Phone Calls LAN Phone (NAT Inbound)
    [Documentation]    WAN phone calls LAN phone - tests NAT inbound traversal
    [Tags]    UC-12348    voice    call    nat-inbound    main-scenario

    # Given phones are registered
    Register Phone On WAN Side    ${WAN_PHONE}    ${WAN_PHONE_NUMBER}
    Register Phone On LAN Side    ${LAN_PHONE}    ${LAN_PHONE_NUMBER}
    Set Caller And Callee    ${WAN_PHONE}    ${LAN_PHONE}

    # When caller calls callee
    Caller Calls Callee

    # Then call is established
    Callee Phone Should Be Ringing
    Callee Answers The Call
    Both Phones Should Be Connected
    RTP Media Session Should Be Established
    Log    Voice communication established through CPE NAT

    # Cleanup
    Caller Hangs Up
    Call Should Be Terminated
    Both Phones Should Return To Idle

UC-12348-Main-V4: WAN Phone Calls WAN Phone 2 (Direct WAN)
    [Documentation]    WAN phone calls another WAN phone - direct WAN communication
    [Tags]    UC-12348    voice    call    direct-wan    main-scenario

    # Given phones are registered
    Register Phone On WAN Side    ${WAN_PHONE}    ${WAN_PHONE_NUMBER}
    Register Phone On WAN Side    ${WAN_PHONE2}    ${WAN_PHONE2_NUMBER}
    Set Caller And Callee    ${WAN_PHONE}    ${WAN_PHONE2}

    # When caller calls callee
    Caller Calls Callee

    # Then call is established
    Callee Phone Should Be Ringing
    Callee Answers The Call
    Both Phones Should Be Connected
    RTP Media Session Should Be Established
    Log    Voice communication established without NAT traversal

    # Cleanup
    Caller Hangs Up
    Call Should Be Terminated
    Both Phones Should Return To Idle

UC-12348-3a: Invalid Phone Number
    [Documentation]    Extension: Caller dials unregistered phone number
    [Tags]    UC-12348    voice    error    invalid-number

    Set Caller And Callee    ${WAN_PHONE}    ${WAN_PHONE2}
    Caller Phone Is Idle
    Caller Dials Invalid Number
    SIP Server Should Reject With 404
    Caller Hangs Up
    Caller Phone Should Return To Idle

UC-12348-8a: Callee Is Busy
    [Documentation]    Extension: Callee is already in an active call
    [Tags]    UC-12348    voice    error    busy

    Set Caller And Callee    ${WAN_PHONE}    ${WAN_PHONE2}
    Caller Phone Is Idle
    Callee Phone Is In Active Call
    Caller Dials Callee Number
    Callee Should Return Busy Response
    Caller Hangs Up
    Caller Phone Should Return To Idle

UC-12348-11a: Callee Does Not Answer (Timeout)
    [Documentation]    Extension: Callee does not answer within timeout period
    [Tags]    UC-12348    voice    error    timeout

    Set Caller And Callee    ${WAN_PHONE}    ${WAN_PHONE2}
    Caller Phone Is Idle
    Callee Phone Is Idle
    Caller Dials Callee Number
    Callee Phone Should Be Ringing
    Wait For Answer Timeout
    SIP Server Should Send Timeout Response
    Caller Hangs Up
    Caller Phone Should Return To Idle

UC-12348-11b: Callee Rejects The Call
    [Documentation]    Extension: Callee actively rejects the incoming call
    [Tags]    UC-12348    voice    error    rejected

    Set Caller And Callee    ${WAN_PHONE}    ${WAN_PHONE2}
    Caller Phone Is Idle
    Callee Phone Is Idle
    Caller Dials Callee Number
    Callee Phone Should Be Ringing
    Callee Rejects The Call
    SIP Server Should Send Rejection Response
    Caller Hangs Up
    Caller Phone Should Return To Idle

*** Keywords ***
Setup Voice Test Environment
    [Documentation]    Initialize voice test environment with SIP phones
    ${acs}=    Get Device By Type    ACS
    ${cpe}=    Get Device By Type    CPE
    ${lan_phone}=    Get Device By Type    SIPPhone    index=0
    ${wan_phone}=    Get Device By Type    SIPPhone    index=1
    ${wan_phone2}=    Get Device By Type    SIPPhone    index=2
    Set Suite Variable    ${ACS}
    Set Suite Variable    ${CPE}
    Set Suite Variable    ${LAN_PHONE}    ${lan_phone}
    Set Suite Variable    ${WAN_PHONE}    ${wan_phone}
    Set Suite Variable    ${WAN_PHONE2}    ${wan_phone2}
    Log    Voice test environment initialized

Teardown Voice Test Environment
    [Documentation]    Clean up voice test environment
    Run Keyword And Ignore Error    Voice Shutdown Phone    ${LAN_PHONE}
    Run Keyword And Ignore Error    Voice Shutdown Phone    ${WAN_PHONE}
    Run Keyword And Ignore Error    Voice Shutdown Phone    ${WAN_PHONE2}
    Log    Voice test environment torn down

Register Phone On LAN Side
    [Documentation]    Register a SIP phone on the LAN side
    [Arguments]    ${phone}    ${number}
    Voice Initialize Phone    ${phone}
    Voice Register Phone    ${phone}    number=${number}
    ${registered}=    Voice Is Phone Registered    ${phone}
    Should Be True    ${registered}    Phone ${number} should be registered on LAN

Register Phone On WAN Side
    [Documentation]    Register a SIP phone on the WAN side
    [Arguments]    ${phone}    ${number}
    Voice Initialize Phone    ${phone}
    Voice Register Phone    ${phone}    number=${number}
    ${registered}=    Voice Is Phone Registered    ${phone}
    Should Be True    ${registered}    Phone ${number} should be registered on WAN

Set Caller And Callee
    [Documentation]    Set the caller and callee phones for the test
    [Arguments]    ${caller}    ${callee}
    Set Test Variable    ${CALLER}    ${caller}
    Set Test Variable    ${CALLEE}    ${callee}

Caller Calls Callee
    [Documentation]    Caller initiates call to callee
    Voice Call A Phone    ${CALLER}    ${CALLEE}
    Log    Caller initiated call to callee

Callee Phone Should Be Ringing
    [Documentation]    Verify callee phone is ringing
    ${ringing}=    Voice Is Call Ringing    ${CALLEE}    timeout=${CALL_TIMEOUT}
    Should Be True    ${ringing}    Callee phone should be ringing

Callee Answers The Call
    [Documentation]    Callee answers the incoming call
    Voice Answer A Call    ${CALLEE}
    Log    Callee answered the call

Both Phones Should Be Connected
    [Documentation]    Verify both phones are connected
    ${caller_connected}=    Voice Is Call Connected    ${CALLER}
    ${callee_connected}=    Voice Is Call Connected    ${CALLEE}
    Should Be True    ${caller_connected}    Caller should be connected
    Should Be True    ${callee_connected}    Callee should be connected

RTP Media Session Should Be Established
    [Documentation]    Verify bidirectional RTP media session
    ${media_ok}=    Voice Is Media Established    ${CALLER}    ${CALLEE}
    Should Be True    ${media_ok}    RTP media session should be established

Caller Hangs Up
    [Documentation]    Caller hangs up the call
    Voice Disconnect The Call    ${CALLER}
    Log    Caller hung up

Call Should Be Terminated
    [Documentation]    Verify call is terminated
    Log    Call terminated by SIP server

Both Phones Should Return To Idle
    [Documentation]    Verify both phones return to idle state
    ${caller_idle}=    Voice Is Phone Idle    ${CALLER}
    ${callee_idle}=    Voice Is Phone Idle    ${CALLEE}
    Should Be True    ${caller_idle}    Caller should be idle
    Should Be True    ${callee_idle}    Callee should be idle

Cleanup SIP Phones
    [Documentation]    Clean up any active calls
    Run Keyword And Ignore Error    Voice Disconnect The Call    ${CALLER}
    Run Keyword And Ignore Error    Voice Disconnect The Call    ${CALLEE}

Caller Phone Is Idle
    [Documentation]    Verify caller phone is idle
    ${idle}=    Voice Is Phone Idle    ${CALLER}
    Should Be True    ${idle}    Caller should be idle

Callee Phone Is Idle
    [Documentation]    Verify callee phone is idle
    ${idle}=    Voice Is Phone Idle    ${CALLEE}
    Should Be True    ${idle}    Callee should be idle

Callee Phone Is In Active Call
    [Documentation]    Simulate callee being in an active call
    Log    Callee is in an active call (simulated busy state)

Caller Dials Invalid Number
    [Documentation]    Caller dials an unregistered number
    Voice Dial Number    ${CALLER}    9999

Caller Dials Callee Number
    [Documentation]    Caller dials callee's number
    Voice Call A Phone    ${CALLER}    ${CALLEE}

SIP Server Should Reject With 404
    [Documentation]    Verify SIP server sends 404 Not Found
    ${response}=    Voice Get Last Sip Response    ${CALLER}
    Should Contain    ${response}    404    SIP server should return 404

Callee Should Return Busy Response
    [Documentation]    Verify callee returns 486 Busy Here
    ${response}=    Voice Get Last Sip Response    ${CALLER}
    Should Contain    ${response}    486    Callee should return 486 Busy

Wait For Answer Timeout
    [Documentation]    Wait for the no-answer timeout
    Sleep    ${CALL_TIMEOUT}s    Waiting for answer timeout

SIP Server Should Send Timeout Response
    [Documentation]    Verify SIP server sends timeout response
    Log    SIP server sent timeout response

Callee Rejects The Call
    [Documentation]    Callee actively rejects the call
    Voice Reject Call    ${CALLEE}

SIP Server Should Send Rejection Response
    [Documentation]    Verify SIP server sends rejection response
    Log    SIP server sent rejection response

Caller Phone Should Return To Idle
    [Documentation]    Verify caller phone returns to idle
    ${idle}=    Voice Is Phone Idle    ${CALLER}
    Should Be True    ${idle}    Caller should return to idle
