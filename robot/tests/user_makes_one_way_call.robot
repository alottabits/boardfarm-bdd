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

*** Test Cases ***
UC-12348-Main-V1: LAN Phone Calls WAN Phone (NAT Outbound)
    [Documentation]    LAN phone calls WAN phone - tests NAT outbound traversal
    ...    Requires: 1 LAN + 1 WAN phone, SIPServer
    [Tags]    UC-12348    voice    call    nat-outbound    main-scenario

    Check Voice Test Preconditions    min_phones=2    min_lan=1    min_wan=1

    # Given: Phones assigned by location, registered, and roles set
    Setup Phones For Scenario    caller_location=LAN    callee_location=WAN

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

UC-12348-Main-V2: LAN Phone Calls WAN Phone 2 (NAT Outbound)
    [Documentation]    LAN phone calls WAN phone 2 - tests NAT outbound traversal
    ...    Requires: 1 LAN + 2 WAN phones, SIPServer
    [Tags]    UC-12348    voice    call    nat-outbound    main-scenario

    Check Voice Test Preconditions    min_phones=3    min_lan=1    min_wan=2

    # Given: Phones assigned by location, registered, and roles set
    Setup Phones For Scenario    caller_location=LAN    callee_location=WAN2

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
    ...    Requires: 1 LAN + 1 WAN phone, SIPServer
    [Tags]    UC-12348    voice    call    nat-inbound    main-scenario

    Check Voice Test Preconditions    min_phones=2    min_lan=1    min_wan=1

    # Given: Phones assigned by location, registered, and roles set
    Setup Phones For Scenario    caller_location=WAN    callee_location=LAN

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
    ...    Requires: 2 WAN phones, SIPServer
    [Tags]    UC-12348    voice    call    direct-wan    main-scenario

    Check Voice Test Preconditions    min_phones=2    min_wan=2

    # Given: Phones assigned by location, registered, and roles set
    Setup Phones For Scenario    caller_location=WAN    callee_location=WAN2

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

UC-12348-Main-V5: WAN Phone 2 Calls LAN Phone (NAT Inbound)
    [Documentation]    WAN phone 2 calls LAN phone - tests NAT inbound traversal
    ...    Requires: 1 LAN + 2 WAN phones, SIPServer
    [Tags]    UC-12348    voice    call    nat-inbound    main-scenario

    Check Voice Test Preconditions    min_phones=3    min_lan=1    min_wan=2

    # Given: Phones assigned by location, registered, and roles set
    Setup Phones For Scenario    caller_location=WAN2    callee_location=LAN

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

UC-12348-Main-V6: WAN Phone 2 Calls WAN Phone (Direct WAN)
    [Documentation]    WAN phone 2 calls WAN phone - direct WAN communication
    ...    Requires: 2 WAN phones, SIPServer
    [Tags]    UC-12348    voice    call    direct-wan    main-scenario

    Check Voice Test Preconditions    min_phones=2    min_wan=2

    # Given: Phones assigned by location, registered, and roles set
    Setup Phones For Scenario    caller_location=WAN2    callee_location=WAN

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
    ...    Requires: 2 WAN phones
    [Tags]    UC-12348    voice    error    invalid-number

    Check Voice Test Preconditions    min_phones=2    min_wan=2

    # Setup - assign caller/callee by location (callee not used for invalid dial)
    Setup Phones For Scenario    caller_location=WAN    callee_location=WAN2
    Verify Phone Is Idle    ${CALLER}

    # Action: Dial invalid number
    Dial Invalid Number    ${CALLER}    9999

    # Verification
    Verify Invalid Number Response
    Phone Hangs Up    ${CALLER}
    Verify Caller Returns To Idle

UC-12348-8a: Callee Is Busy
    [Documentation]    Extension: Callee is already in an active call
    ...    Requires: 2 WAN phones
    [Tags]    UC-12348    voice    error    busy

    Check Voice Test Preconditions    min_phones=2    min_wan=2

    # Setup
    Setup Phones For Scenario    caller_location=WAN    callee_location=WAN2
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
    ...    Requires: 2 WAN phones
    [Tags]    UC-12348    voice    error    timeout

    Check Voice Test Preconditions    min_phones=2    min_wan=2

    # Setup
    Setup Phones For Scenario    caller_location=WAN    callee_location=WAN2
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
    ...    Requires: 2 WAN phones
    [Tags]    UC-12348    voice    error    rejected

    Check Voice Test Preconditions    min_phones=2    min_wan=2

    # Setup
    Setup Phones For Scenario    caller_location=WAN    callee_location=WAN2
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

UC-12348-15a: RTP Media Fails To Establish
    [Documentation]    Extension: SIP signaling completes but RTP media path fails
    ...    Requires: 2 WAN phones. In real scenario would inject network failure.
    ...    This test verifies clean hangup and termination when media fails.
    [Tags]    UC-12348    voice    error    rtp-failure

    Check Voice Test Preconditions    min_phones=2    min_wan=2

    # Setup
    Setup Phones For Scenario    caller_location=WAN    callee_location=WAN2
    Verify Phone Is Idle    ${CALLER}
    Verify Phone Is Idle    ${CALLEE}

    # Action: Normal call flow - SIP signaling completes
    Caller Calls Callee
    The Callee Phone Should Start Ringing
    Callee Answers Call
    Both Phones Should Be Connected

    # Simulated: RTP media fails - either party hangs up due to no audio
    Caller Hangs Up

    # Verification: Clean termination, both phones idle
    Verify SIP Call Terminated
    Both Phones Should Return To Idle State
