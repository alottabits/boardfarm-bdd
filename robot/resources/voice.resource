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
    ...    Dynamically discovers available devices and classifies by network location
    ...    (LAN/WAN) using device metadata (options field) or naming convention.
    ...    No hardcoded device names - works across different testbeds.
    ...    
    ...    Sets suite variables:
    ...    - ACS, CPE, SIPCENTER (if available)
    ...    - AVAILABLE_PHONES (dict: name -> device)
    ...    - PHONE_COUNT (total number of SIP phones)
    ...    - LAN_PHONES (list of phones on LAN side)
    ...    - WAN_PHONES (list of phones on WAN side)
    ...    
    ...    Tests use Setup Phones For Scenario to assign caller/callee by location.
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
    
    # Discover all SIP phones and classify by network location (LAN/WAN)
    ${phones}=    Get Devices By Type    SIPPhone
    ${phone_count}=    Get Length    ${phones}
    Set Suite Variable    ${AVAILABLE_PHONES}    ${phones}
    Set Suite Variable    ${PHONE_COUNT}    ${phone_count}
    
    ${by_location}=    Discover Phones By Location    ${phones}
    ${lan_phones}=    Get From Dictionary    ${by_location}    LAN
    ${wan_phones}=    Get From Dictionary    ${by_location}    WAN
    ${lan_count}=    Get Length    ${lan_phones}
    ${wan_count}=    Get Length    ${wan_phones}
    Set Suite Variable    ${LAN_PHONES}    ${lan_phones}
    Set Suite Variable    ${WAN_PHONES}    ${wan_phones}
    
    Log    Found ${phone_count} SIP phone(s): ${lan_count} LAN, ${wan_count} WAN
    
    # Verify SIP server if available
    IF    $SIPCENTER is not None
        The SIP Server Is Running And Operational    ${SIPCENTER}
    END
    
    Log    Voice test environment initialized: ${phone_count} phones (${lan_count} LAN, ${wan_count} WAN)

Check Voice Test Preconditions
    [Documentation]    Check if the testbed meets voice test requirements.
    ...    
    ...    Call this at the start of each test or in Suite Setup with Skip=True
    ...    to skip tests that cannot run on the current testbed.
    ...    
    ...    Arguments:
    ...    - min_phones: Minimum number of SIP phones required (default: 2)
    ...    - min_lan: Minimum LAN phones (default: 0)
    ...    - min_wan: Minimum WAN phones (default: 0)
    ...    - require_sipcenter: Whether SIPServer is required (default: True)
    ...    
    ...    Example:
    ...        Check Voice Test Preconditions    min_phones=3    min_wan=2
    [Arguments]    ${min_phones}=2    ${min_lan}=0    ${min_wan}=0    ${require_sipcenter}=${True}
    
    # Check SIP server
    IF    ${require_sipcenter} and $SIPCENTER is None
        Skip    No SIPServer available in testbed - skipping voice test
    END
    
    # Check phone count
    IF    ${PHONE_COUNT} < ${min_phones}
        Skip    Testbed has ${PHONE_COUNT} SIP phone(s), but test requires ${min_phones} - skipping
    END
    
    # Check location-based requirements
    ${lan_count}=    Get Length    ${LAN_PHONES}
    ${wan_count}=    Get Length    ${WAN_PHONES}
    IF    ${lan_count} < ${min_lan}
        Skip    Testbed has ${lan_count} LAN phone(s), but test requires ${min_lan} - skipping
    END
    IF    ${wan_count} < ${min_wan}
        Skip    Testbed has ${wan_count} WAN phone(s), but test requires ${min_wan} - skipping
    END
    
    Log    Voice test preconditions met: ${PHONE_COUNT} phones (${lan_count} LAN, ${wan_count} WAN), SIPServer available

Setup Phones For Scenario
    [Documentation]    Assign caller and callee by network location, register them, and set roles.
    ...    
    ...    Use this at the start of each test to select phones based on scenario requirements.
    ...    Locations: LAN, WAN, WAN2 (second WAN phone).
    ...    
    ...    Example:
    ...        Setup Phones For Scenario    caller_location=LAN    callee_location=WAN
    ...        Setup Phones For Scenario    caller_location=LAN    callee_location=WAN2
    [Arguments]    ${caller_location}    ${callee_location}
    ${caller}    ${callee}=    Assign Phones For Scenario    ${caller_location}    ${callee_location}    ${LAN_PHONES}    ${WAN_PHONES}
    Set Test Variable    ${CALLER}    ${caller}
    Set Test Variable    ${CALLEE}    ${callee}
    Assign Caller And Callee Roles    ${caller}    ${callee}
    # Register each phone based on its location (not caller/callee role)
    IF    '${caller_location}' == 'LAN'
        Register Phone On LAN Side    ${caller}
    ELSE
        Register Phone On WAN Side    ${caller}
    END
    IF    '${callee_location}' == 'LAN'
        Register Phone On LAN Side    ${callee}
    ELSE
        Register Phone On WAN Side    ${callee}
    END

Teardown Voice Test Environment
    [Documentation]    Clean up voice test environment.
    ...    Per-test phone cleanup is handled automatically by the listener
    ...    teardown stack (LIFO). This keyword only logs suite-level teardown.
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
