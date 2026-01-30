*** Settings ***
Documentation    Basic smoke test to verify testbed connectivity.
...              Corresponds to tests/features/hello.feature

Library    robotframework_boardfarm.BoardfarmLibrary
Library    ../libraries/boardfarm_keywords.py
Library    ../libraries/acs_keywords.py
Library    ../libraries/hello_keywords.py

*** Test Cases ***
Say Hello - Verify Basic Connectivity
    [Documentation]    Basic test to verify testbed connectivity
    [Tags]    smoke    hello
    Say Hello
    ${acs}=    Get Device By Type    ACS
    ${cpe}=    Get Device By Type    CPE
    Should Not Be Equal    ${acs}    ${None}    ACS device should exist
    Should Not Be Equal    ${cpe}    ${None}    CPE device should exist
    Log    ACS: ${acs}
    Log    CPE: ${cpe}

Verify CPE Is Online
    [Documentation]    Verify CPE is online via ACS
    [Tags]    smoke    cpe    online
    ${acs}=    Get Device By Type    ACS
    ${cpe}=    Get Device By Type    CPE
    The CPE Is Online Via ACS    ${acs}    ${cpe}
