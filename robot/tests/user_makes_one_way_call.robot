*** Settings ***
Documentation    UC-12348: User Makes a One-Way Call
...              As a user, I want to make a voice call from one SIP phone to another
...              so that I can establish voice communication.
...
...              Corresponds to tests/features/UC-12348 User makes a one-way call.feature
...
...              Device Requirements:
...              - Most tests require 2 SIP phones minimum
...              - UC-12348-Main-V4 requires 3 SIP phones
...              - All phone numbers are obtained from device object properties

Library     robotframework_boardfarm.BoardfarmLibrary
Library     ../libraries/boardfarm_keywords.py
Library     ../libraries/voice_keywords.py
Resource    ../resources/common.resource
Resource    ../resources/voice.resource
Resource    ../resources/cleanup.resource
Resource    ../resources/variables.resource

Suite Setup       Setup Voice Test Environment
Suite Teardown    Teardown Voice Test Environment
Test Teardown     Cleanup Voice Test

*** Keywords ***
Cleanup Voice Test
    [Documentation]    Clean up phones after each test.
    ...    Uses Run Keyword And Ignore Error because variables may not be set
    ...    if test was skipped or failed early.
    Run Keyword And Ignore Error    Cleanup Single SIP Phone    ${CALLER}
    Run Keyword And Ignore Error    Cleanup Single SIP Phone    ${CALLEE}

*** Test Cases ***
UC-12348-Main-V1: LAN Phone Calls WAN Phone (NAT Outbound)
    [Documentation]    LAN phone calls WAN phone - tests NAT outbound traversal
    ...    Requires: 2 SIP phones, SIPServer
    [Tags]    UC-12348    voice    call    nat-outbound    main-scenario

    # Check preconditions - skip if testbed lacks required devices
    Check Voice Test Preconditions    min_phones=2

    # Given: Phones are registered (phone numbers from device objects)
    Register Phone On LAN Side    ${LAN_PHONE}
    Register Phone On WAN Side    ${WAN_PHONE}
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
    ...    Requires: 2 SIP phones, SIPServer
    [Tags]    UC-12348    voice    call    nat-inbound    main-scenario

    # Check preconditions - skip if testbed lacks required devices
    Check Voice Test Preconditions    min_phones=2

    # Given: Phones are registered (phone numbers from device objects)
    Register Phone On WAN Side    ${WAN_PHONE}
    Register Phone On LAN Side    ${LAN_PHONE}
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
    ...    Requires: 3 SIP phones, SIPServer
    [Tags]    UC-12348    voice    call    direct-wan    main-scenario

    # Check preconditions - this test requires 3 phones
    Check Voice Test Preconditions    min_phones=3

    # Given: Phones are registered (phone numbers from device objects)
    Register Phone On WAN Side    ${WAN_PHONE}
    Register Phone On WAN Side    ${WAN_PHONE2}
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
    ...    Requires: 2 SIP phones (caller only used, but setup needs 2)
    [Tags]    UC-12348    voice    error    invalid-number

    # Check preconditions
    Check Voice Test Preconditions    min_phones=2

    # Setup - use the two available phones
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
    ...    Requires: 2 SIP phones
    [Tags]    UC-12348    voice    error    busy

    # Check preconditions
    Check Voice Test Preconditions    min_phones=2

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
    ...    Requires: 2 SIP phones
    [Tags]    UC-12348    voice    error    timeout

    # Check preconditions
    Check Voice Test Preconditions    min_phones=2

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
    ...    Requires: 2 SIP phones
    [Tags]    UC-12348    voice    error    rejected

    # Check preconditions
    Check Voice Test Preconditions    min_phones=2

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
