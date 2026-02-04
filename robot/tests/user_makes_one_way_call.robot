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
Resource    ../resources/voice.resource

Suite Setup       Setup Voice Test Environment
Suite Teardown    Teardown Voice Test Environment
Test Teardown     Cleanup SIP Phones After Test    ${CALLER}    ${CALLEE}

*** Variables ***
${LAN_PHONE_NUMBER}     1000
${WAN_PHONE_NUMBER}     2000
${WAN_PHONE2_NUMBER}    3000
${CALL_TIMEOUT}         30

*** Test Cases ***
UC-12348-Main-V1: LAN Phone Calls WAN Phone (NAT Outbound)
    [Documentation]    LAN phone calls WAN phone - tests NAT outbound traversal
    [Tags]    UC-12348    voice    call    nat-outbound    main-scenario

    # Given: Phones are registered
    Register Phone On LAN Side    ${LAN_PHONE}    ${LAN_PHONE_NUMBER}
    Register Phone On WAN Side    ${WAN_PHONE}    ${WAN_PHONE_NUMBER}
    Set Caller And Callee    ${LAN_PHONE}    ${WAN_PHONE}

    # When: Caller calls callee
    Caller Calls Callee

    # Then: Call is established
    The Callee Phone Should Start Ringing
    Callee Answers Call
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

    # Given: Phones are registered
    Register Phone On WAN Side    ${WAN_PHONE}    ${WAN_PHONE_NUMBER}
    Register Phone On LAN Side    ${LAN_PHONE}    ${LAN_PHONE_NUMBER}
    Set Caller And Callee    ${WAN_PHONE}    ${LAN_PHONE}

    # When: Caller calls callee
    Caller Calls Callee

    # Then: Call is established
    The Callee Phone Should Start Ringing
    Callee Answers Call
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

    # Given: Phones are registered
    Register Phone On WAN Side    ${WAN_PHONE}    ${WAN_PHONE_NUMBER}
    Register Phone On WAN Side    ${WAN_PHONE2}    ${WAN_PHONE2_NUMBER}
    Set Caller And Callee    ${WAN_PHONE}    ${WAN_PHONE2}

    # When: Caller calls callee
    Caller Calls Callee

    # Then: Call is established
    The Callee Phone Should Start Ringing
    Callee Answers Call
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

    # Setup
    Set Caller And Callee    ${WAN_PHONE}    ${WAN_PHONE2}
    Verify Phone Is Idle    ${CALLER}

    # Action: Dial invalid number
    Dial Invalid Number    ${CALLER}    9999

    # Verification
    Verify Invalid Number Response
    Phone Hangs Up    ${CALLER}
    Verify Caller Returns To Idle

UC-12348-8a: Callee Is Busy
    [Documentation]    Extension: Callee is already in an active call
    [Tags]    UC-12348    voice    error    busy

    # Setup
    Set Caller And Callee    ${WAN_PHONE}    ${WAN_PHONE2}
    Verify Phone Is Idle    ${CALLER}
    Simulate Busy Callee

    # Action: Dial callee
    Caller Calls Callee

    # Verification
    Verify Busy Response
    Phone Hangs Up    ${CALLER}
    Verify Caller Returns To Idle

UC-12348-11a: Callee Does Not Answer (Timeout)
    [Documentation]    Extension: Callee does not answer within timeout period
    [Tags]    UC-12348    voice    error    timeout

    # Setup
    Set Caller And Callee    ${WAN_PHONE}    ${WAN_PHONE2}
    Verify Phone Is Idle    ${CALLER}
    Verify Phone Is Idle    ${CALLEE}

    # Action: Dial and wait for timeout
    Caller Calls Callee
    The Callee Phone Should Start Ringing
    Wait For Call Timeout    ${CALL_TIMEOUT}

    # Verification
    Verify Timeout Response
    Phone Hangs Up    ${CALLER}
    Verify Caller Returns To Idle

UC-12348-11b: Callee Rejects The Call
    [Documentation]    Extension: Callee actively rejects the incoming call
    [Tags]    UC-12348    voice    error    rejected

    # Setup
    Set Caller And Callee    ${WAN_PHONE}    ${WAN_PHONE2}
    Verify Phone Is Idle    ${CALLER}
    Verify Phone Is Idle    ${CALLEE}

    # Action: Dial and callee rejects
    Caller Calls Callee
    The Callee Phone Should Start Ringing
    Phone Rejects Call    ${CALLEE}

    # Verification
    Verify Rejection Response
    Phone Hangs Up    ${CALLER}
    Verify Caller Returns To Idle
