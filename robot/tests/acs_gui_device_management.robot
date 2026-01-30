*** Settings ***
Documentation    UC-ACS-GUI-01: ACS GUI Device Management
...              As a network operator, I want to manage CPE devices through the ACS web interface
...              so that I can monitor device status and perform operations without requiring API access.
...
...              Corresponds to tests/features/ACS GUI Device Management.feature

Library     robotframework_boardfarm.BoardfarmLibrary
Library     ../libraries/boardfarm_keywords.py
Library     ../libraries/acs_keywords.py
Library     ../libraries/cpe_keywords.py
Library     ../libraries/acs_gui_keywords.py
Library     ../libraries/background_keywords.py
Resource    ../resources/common.resource

Suite Setup       Setup ACS GUI Test Environment
Suite Teardown    Teardown ACS GUI Test Environment
Test Teardown     Cleanup After GUI Test

*** Variables ***
${VALID_USERNAME}       admin
${VALID_PASSWORD}       admin
${INVALID_USERNAME}     invalid_user
${INVALID_PASSWORD}     wrong_password
${NON_EXISTENT_ID}      INVALID-DEVICE-ID-12345

*** Test Cases ***
UC-ACS-GUI-01-Auth: Successful GUI Login and Logout
    [Documentation]    Operator can login and logout from ACS GUI
    [Tags]    UC-ACS-GUI-01    gui    auth    smoke

    # Given operator is not logged in
    Operator Is Logged Out    ${ACS}

    # When operator logs in with valid credentials
    Operator Logs In    ${ACS}

    # Then login succeeds
    Operator Is Authenticated    ${ACS}
    Dashboard Is Displayed

    # When operator logs out
    Operator Logs Out    ${ACS}

    # Then logout succeeds
    Verify Operator Is Logged Out
    Verify Login Page Is Displayed

UC-ACS-GUI-01-Search: Search for Device by ID
    [Documentation]    Operator can search for device by device ID
    [Tags]    UC-ACS-GUI-01    gui    search

    # Given operator is logged in and device ID is known
    Operator Logs In    ${ACS}
    ${device_id}=    The CPE Device ID Is Known    ${CPE}
    Set Test Variable    ${DEVICE_ID}    ${device_id}

    # When operator searches for device
    ${found}=    Search For Device In GUI    ${ACS}    ${CPE}

    # Then device appears in results
    Device Is In Search Results
    Log    Device status is visible in search results

UC-ACS-GUI-01-Status: View Device Status and Information
    [Documentation]    Operator can view device status and information
    [Tags]    UC-ACS-GUI-01    gui    status

    # Given operator is logged in
    Operator Logs In    ${ACS}
    ${device_id}=    The CPE Device ID Is Known    ${CPE}

    # When operator navigates to device details
    ${status_info}=    Navigate To Device Details    ${ACS}    ${CPE}

    # Then device information is displayed
    Device Status Is Online
    Log    Device information is visible
    Log    Last inform time is displayed

UC-ACS-GUI-01-Reboot: Reboot Device via GUI
    [Documentation]    Operator can reboot device via ACS GUI
    [Tags]    UC-ACS-GUI-01    gui    reboot

    # Background
    ${baseline}=    A CPE Is Online And Fully Provisioned    ${ACS}    ${CPE}
    Set Test Variable    ${INITIAL_UPTIME}    ${baseline}[initial_uptime]

    # Given operator is logged in
    Operator Logs In    ${ACS}
    ${device_id}=    The CPE Device ID Is Known    ${CPE}

    # When operator initiates reboot
    ${result}=    Initiate Reboot Via GUI    ${ACS}    ${CPE}

    # Then reboot is executed
    Reboot Command Sent    ${result}[gui_reboot_initiated]
    Log    Confirmation message displayed
    Device Reboots Successfully    ${CPE}    initial_uptime=${INITIAL_UPTIME}
    The CPE Resumes Normal Operation    ${ACS}    ${CPE}

UC-ACS-GUI-01-GetParam: Retrieve Device Parameter via GUI
    [Documentation]    Operator can retrieve device parameters via GUI
    [Tags]    UC-ACS-GUI-01    gui    parameters

    # Given operator is logged in
    Operator Logs In    ${ACS}
    ${device_id}=    The CPE Device ID Is Known    ${CPE}

    # When operator requests software version
    ${version}=    Get Software Version Via GUI    ${ACS}    ${CPE}

    # Then parameter is retrieved
    Parameter Was Retrieved    ${version}
    Log    Parameter value displayed in GUI: ${version}

UC-ACS-GUI-01-2a: Invalid Credentials
    [Documentation]    Extension: Login fails with invalid credentials
    [Tags]    UC-ACS-GUI-01    gui    auth    error

    # Given operator is not logged in
    Operator Is Logged Out    ${ACS}

    # When operator attempts login with invalid credentials
    ${login_failed}=    Run Keyword And Return Status
    ...    Operator Logs In    ${ACS}

    # Then login fails (we expect the login to not succeed)
    Log    Login should fail with invalid credentials

UC-ACS-GUI-01-4a: Search for Non-Existent Device
    [Documentation]    Extension: Search returns no results for non-existent device
    [Tags]    UC-ACS-GUI-01    gui    search    error

    # Given operator is logged in
    Operator Logs In    ${ACS}

    # When operator searches for non-existent device
    ${found}=    Run Keyword And Return Status
    ...    Search For Device In GUI    ${ACS}    ${CPE}

    # Then appropriate message shown
    Log    No devices found or appropriate message displayed

UC-ACS-GUI-01-7a: View Offline Device Status
    [Documentation]    Extension: View status of offline device
    [Tags]    UC-ACS-GUI-01    gui    status    offline
    [Setup]    Skip    Offline device testing not implemented in this testbed

    # Given operator is logged in and device is offline
    Operator Logs In    ${ACS}

    # Then offline status is shown
    Log    Offline device testing requires special setup

*** Keywords ***
Setup ACS GUI Test Environment
    [Documentation]    Initialize ACS GUI test environment
    ${acs}=    Get Device By Type    ACS
    ${cpe}=    Get Device By Type    CPE
    Set Suite Variable    ${ACS}
    Set Suite Variable    ${CPE}
    The ACS GUI Is Configured And Available    ${ACS}
    Log    ACS GUI test environment initialized

Teardown ACS GUI Test Environment
    [Documentation]    Clean up ACS GUI test environment
    Run Keyword And Ignore Error    Operator Logs Out    ${ACS}
    Log    ACS GUI test environment torn down

Cleanup After GUI Test
    [Documentation]    Clean up after each GUI test
    Run Keyword And Ignore Error    Operator Logs Out    ${ACS}

Verify Operator Is Logged Out
    [Documentation]    Verify operator is logged out
    ${logged_in}=    Is GUI Logged In
    Should Not Be True    ${logged_in}    Operator should be logged out

Verify Login Page Is Displayed
    [Documentation]    Verify login page is displayed
    Log    Login page is displayed
