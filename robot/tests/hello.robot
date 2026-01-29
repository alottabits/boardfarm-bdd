*** Settings ***
Documentation    Basic smoke test to verify testbed connectivity.
...              Corresponds to pytest/features/hello.feature

Library    robotframework_boardfarm.BoardfarmLibrary
Library    robotframework_boardfarm.UseCaseLibrary

*** Test Cases ***
Say Hello - Verify Basic Connectivity
    [Documentation]    Basic test to verify testbed connectivity
    [Tags]    smoke    hello
    Log    Hello from Robot Framework!
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
    ${online}=    Acs Is Cpe Online    ${acs}    ${cpe}
    Should Be True    ${online}    CPE should be online
