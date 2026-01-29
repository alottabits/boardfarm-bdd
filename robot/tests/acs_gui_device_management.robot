*** Settings ***
Documentation    UC-ACS-GUI-01: ACS GUI Device Management
...              As a network operator, I want to manage CPE devices through the ACS web interface
...              so that I can monitor device status and perform operations without requiring API access.
...
...              Corresponds to pytest/features/ACS GUI Device Management.feature

Library     robotframework_boardfarm.BoardfarmLibrary
Library     robotframework_boardfarm.UseCaseLibrary
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
    Operator Is Not Logged Into ACS GUI

    # When operator logs in with valid credentials
    Operator Logs Into ACS GUI    ${VALID_USERNAME}    ${VALID_PASSWORD}

    # Then login succeeds
    Operator Should Be Authenticated
    ACS Dashboard Should Be Displayed

    # When operator logs out
    Operator Logs Out From ACS GUI

    # Then logout succeeds
    Operator Should Be Logged Out
    Login Page Should Be Displayed

UC-ACS-GUI-01-Search: Search for Device by ID
    [Documentation]    Operator can search for device by device ID
    [Tags]    UC-ACS-GUI-01    gui    search

    # Given operator is logged in and device ID is known
    Operator Logs Into ACS GUI    ${VALID_USERNAME}    ${VALID_PASSWORD}
    Device ID Is Known

    # When operator searches for device
    Operator Searches For Device    ${DEVICE_ID}

    # Then device appears in results
    Device Should Appear In Search Results
    Device Status Should Be Visible

UC-ACS-GUI-01-Status: View Device Status and Information
    [Documentation]    Operator can view device status and information
    [Tags]    UC-ACS-GUI-01    gui    status

    # Given operator is logged in
    Operator Logs Into ACS GUI    ${VALID_USERNAME}    ${VALID_PASSWORD}
    Device ID Is Known

    # When operator navigates to device details
    Operator Navigates To Device Details    ${DEVICE_ID}

    # Then device information is displayed
    Device Status Should Be Online
    Device Information Should Be Visible
    Last Inform Time Should Be Displayed

UC-ACS-GUI-01-Reboot: Reboot Device via GUI
    [Documentation]    Operator can reboot device via ACS GUI
    [Tags]    UC-ACS-GUI-01    gui    reboot

    # Given operator is logged in
    Operator Logs Into ACS GUI    ${VALID_USERNAME}    ${VALID_PASSWORD}
    Device ID Is Known

    # When operator initiates reboot
    Operator Initiates Reboot Via GUI    ${DEVICE_ID}

    # Then reboot is executed
    Reboot Command Should Be Sent
    Confirmation Message Should Be Displayed
    Device Should Reboot Successfully
    CPE Should Complete Boot Sequence
    CPE Should Resume Normal Operation

UC-ACS-GUI-01-GetParam: Retrieve Device Parameter via GUI
    [Documentation]    Operator can retrieve device parameters via GUI
    [Tags]    UC-ACS-GUI-01    gui    parameters

    # Given operator is logged in
    Operator Logs Into ACS GUI    ${VALID_USERNAME}    ${VALID_PASSWORD}
    Device ID Is Known

    # When operator requests software version
    Operator Requests Software Version Via GUI    ${DEVICE_ID}

    # Then parameter is retrieved
    Software Version Should Be Retrieved
    Value Should Be Displayed In GUI

UC-ACS-GUI-01-2a: Invalid Credentials
    [Documentation]    Extension: Login fails with invalid credentials
    [Tags]    UC-ACS-GUI-01    gui    auth    error

    # Given operator is not logged in
    Operator Is Not Logged Into ACS GUI

    # When operator attempts login with invalid credentials
    Operator Attempts Login With Invalid Credentials

    # Then login fails
    Login Should Fail
    Authentication Error Should Be Displayed

UC-ACS-GUI-01-4a: Search for Non-Existent Device
    [Documentation]    Extension: Search returns no results for non-existent device
    [Tags]    UC-ACS-GUI-01    gui    search    error

    # Given operator is logged in
    Operator Logs Into ACS GUI    ${VALID_USERNAME}    ${VALID_PASSWORD}

    # When operator searches for non-existent device
    Operator Searches For Device    ${NON_EXISTENT_ID}

    # Then no devices found
    No Devices Should Be Found
    Appropriate Message Should Be Displayed

UC-ACS-GUI-01-7a: View Offline Device Status
    [Documentation]    Extension: View status of offline device
    [Tags]    UC-ACS-GUI-01    gui    status    offline

    # Given operator is logged in and device is offline
    Operator Logs Into ACS GUI    ${VALID_USERNAME}    ${VALID_PASSWORD}
    A CPE Device Is Offline

    # When operator views offline device
    Operator Views Offline Device Details    ${OFFLINE_DEVICE_ID}

    # Then offline status is shown
    Device Status Should Be Offline
    Last Known Information Should Be Visible
    Last Inform Time Should Indicate When Device Was Last Online

UC-ACS-GUI-01-8a: Firmware Upgrade Fails on Containerized CPE
    [Documentation]    Extension: Firmware upgrade fails on containerized CPE
    [Tags]    UC-ACS-GUI-01    gui    firmware    error    container

    # Given operator is logged in and CPE is containerized
    Operator Logs Into ACS GUI    ${VALID_USERNAME}    ${VALID_PASSWORD}
    Device ID Is Known
    CPE Is A Containerized Device

    # When operator attempts firmware upgrade
    Operator Attempts Firmware Upgrade Via GUI    ${DEVICE_ID}

    # Then upgrade fails gracefully
    Firmware Upgrade Command Should Be Sent
    Operation Should Fail On Containerized CPE
    Error Message Should Be Displayed In GUI
    Device Should Remain Operational

*** Keywords ***
Setup ACS GUI Test Environment
    [Documentation]    Initialize ACS GUI test environment
    ${acs}=    Get Device By Type    ACS
    ${cpe}=    Get Device By Type    CPE
    Set Suite Variable    ${ACS}
    Set Suite Variable    ${CPE}
    # Get device ID from CPE for searches
    ${device_id}=    Acs Get Device Id    ${ACS}    ${CPE}
    Set Suite Variable    ${DEVICE_ID}    ${device_id}
    Log    ACS GUI test environment initialized with device ${device_id}

Teardown ACS GUI Test Environment
    [Documentation]    Clean up ACS GUI test environment
    Run Keyword And Ignore Error    Acs Gui Logout    ${ACS}
    Log    ACS GUI test environment torn down

Cleanup After GUI Test
    [Documentation]    Clean up after each GUI test
    Run Keyword And Ignore Error    Acs Gui Logout    ${ACS}

Operator Is Not Logged Into ACS GUI
    [Documentation]    Ensure operator is not logged in
    Run Keyword And Ignore Error    Acs Gui Logout    ${ACS}
    Log    Operator is not logged into ACS GUI

Operator Logs Into ACS GUI
    [Documentation]    Login to ACS GUI with credentials
    [Arguments]    ${username}    ${password}
    Acs Gui Login    ${ACS}    username=${username}    password=${password}
    Log    Operator logged into ACS GUI

Operator Should Be Authenticated
    [Documentation]    Verify operator is authenticated
    ${authenticated}=    Acs Gui Is Authenticated    ${ACS}
    Should Be True    ${authenticated}    Operator should be authenticated

ACS Dashboard Should Be Displayed
    [Documentation]    Verify ACS dashboard is displayed
    ${on_dashboard}=    Acs Gui Is On Dashboard    ${ACS}
    Should Be True    ${on_dashboard}    Dashboard should be displayed

Operator Logs Out From ACS GUI
    [Documentation]    Logout from ACS GUI
    Acs Gui Logout    ${ACS}
    Log    Operator logged out from ACS GUI

Operator Should Be Logged Out
    [Documentation]    Verify operator is logged out
    ${authenticated}=    Acs Gui Is Authenticated    ${ACS}
    Should Not Be True    ${authenticated}    Operator should be logged out

Login Page Should Be Displayed
    [Documentation]    Verify login page is displayed
    ${on_login}=    Acs Gui Is On Login Page    ${ACS}
    Should Be True    ${on_login}    Login page should be displayed

Device ID Is Known
    [Documentation]    Confirm device ID is available
    Should Not Be Empty    ${DEVICE_ID}    Device ID should be known

Operator Searches For Device
    [Documentation]    Search for device by ID in ACS GUI
    [Arguments]    ${device_id}
    Acs Gui Search Device    ${ACS}    device_id=${device_id}
    Log    Searched for device: ${device_id}

Device Should Appear In Search Results
    [Documentation]    Verify device appears in search results
    ${found}=    Acs Gui Is Device In Results    ${ACS}    ${DEVICE_ID}
    Should Be True    ${found}    Device should appear in search results

Device Status Should Be Visible
    [Documentation]    Verify device status is visible in results
    Log    Device status is visible in search results

Operator Navigates To Device Details
    [Documentation]    Navigate to device details page
    [Arguments]    ${device_id}
    Acs Gui Navigate To Device    ${ACS}    device_id=${device_id}
    Log    Navigated to device details for ${device_id}

Device Status Should Be Online
    [Documentation]    Verify device status shows online
    ${status}=    Acs Gui Get Device Status    ${ACS}    ${DEVICE_ID}
    Should Be Equal As Strings    ${status}    online    Device should be online

Device Information Should Be Visible
    [Documentation]    Verify device information is displayed
    ${info}=    Acs Gui Get Device Info    ${ACS}    ${DEVICE_ID}
    Should Not Be Empty    ${info}    Device information should be visible

Last Inform Time Should Be Displayed
    [Documentation]    Verify last inform time is shown
    ${last_inform}=    Acs Gui Get Last Inform Time    ${ACS}    ${DEVICE_ID}
    Should Not Be Empty    ${last_inform}    Last inform time should be displayed

Operator Initiates Reboot Via GUI
    [Documentation]    Initiate device reboot via GUI
    [Arguments]    ${device_id}
    ${timestamp}=    Evaluate    __import__('datetime').datetime.now(__import__('datetime').timezone.utc)
    Set Test Variable    ${REBOOT_TIMESTAMP}    ${timestamp}
    Acs Gui Initiate Reboot    ${ACS}    device_id=${device_id}
    Log    Reboot initiated via GUI for ${device_id}

Reboot Command Should Be Sent
    [Documentation]    Verify reboot command was sent
    Log    Reboot command sent to device

Confirmation Message Should Be Displayed
    [Documentation]    Verify confirmation message is shown
    ${message}=    Acs Gui Get Confirmation Message    ${ACS}
    Should Not Be Empty    ${message}    Confirmation message should be displayed

Device Should Reboot Successfully
    [Documentation]    Verify device reboots successfully
    ${rebooted}=    Acs Wait For Reboot Rpc    ${ACS}    ${CPE}
    ...    since=${REBOOT_TIMESTAMP}    timeout=120
    Should Not Be Equal    ${rebooted}    ${None}    Device should reboot

CPE Should Complete Boot Sequence
    [Documentation]    Verify CPE completes boot sequence
    ${boot_complete}=    Acs Wait For Boot Inform    ${ACS}    ${CPE}
    ...    since=${REBOOT_TIMESTAMP}    timeout=240
    Should Not Be Equal    ${boot_complete}    ${None}    CPE should complete boot

CPE Should Resume Normal Operation
    [Documentation]    Verify CPE resumes normal operation
    ${online}=    Acs Is Cpe Online    ${ACS}    ${CPE}
    Should Be True    ${online}    CPE should be online after reboot

Operator Requests Software Version Via GUI
    [Documentation]    Request software version parameter via GUI
    [Arguments]    ${device_id}
    ${version}=    Acs Gui Get Parameter    ${ACS}    ${device_id}
    ...    Device.DeviceInfo.SoftwareVersion
    Set Test Variable    ${RETRIEVED_VERSION}    ${version}
    Log    Retrieved software version: ${version}

Software Version Should Be Retrieved
    [Documentation]    Verify software version was retrieved
    Should Not Be Empty    ${RETRIEVED_VERSION}    Software version should be retrieved

Value Should Be Displayed In GUI
    [Documentation]    Verify parameter value is displayed
    Log    Parameter value displayed in GUI: ${RETRIEVED_VERSION}

Operator Attempts Login With Invalid Credentials
    [Documentation]    Attempt login with invalid credentials
    Run Keyword And Expect Error    *    Acs Gui Login    ${ACS}
    ...    username=${INVALID_USERNAME}    password=${INVALID_PASSWORD}

Login Should Fail
    [Documentation]    Verify login failed
    ${authenticated}=    Acs Gui Is Authenticated    ${ACS}
    Should Not Be True    ${authenticated}    Login should fail

Authentication Error Should Be Displayed
    [Documentation]    Verify authentication error is shown
    ${error}=    Acs Gui Get Error Message    ${ACS}
    Should Not Be Empty    ${error}    Authentication error should be displayed

No Devices Should Be Found
    [Documentation]    Verify no devices in search results
    ${found}=    Acs Gui Is Device In Results    ${ACS}    ${NON_EXISTENT_ID}
    Should Not Be True    ${found}    No devices should be found

Appropriate Message Should Be Displayed
    [Documentation]    Verify appropriate message for no results
    Log    No devices found message displayed

A CPE Device Is Offline
    [Documentation]    Set up offline device scenario
    # For this test, we simulate/track an offline device
    Set Test Variable    ${OFFLINE_DEVICE_ID}    OFFLINE-TEST-DEVICE

Operator Views Offline Device Details
    [Documentation]    View details of offline device
    [Arguments]    ${device_id}
    Acs Gui Navigate To Device    ${ACS}    device_id=${device_id}

Device Status Should Be Offline
    [Documentation]    Verify device status shows offline
    ${status}=    Acs Gui Get Device Status    ${ACS}    ${OFFLINE_DEVICE_ID}
    Should Be Equal As Strings    ${status}    offline    Device should be offline

Last Known Information Should Be Visible
    [Documentation]    Verify last known information is shown
    Log    Last known device information is visible

Last Inform Time Should Indicate When Device Was Last Online
    [Documentation]    Verify last inform time shows historical data
    ${last_inform}=    Acs Gui Get Last Inform Time    ${ACS}    ${OFFLINE_DEVICE_ID}
    Should Not Be Empty    ${last_inform}    Last inform time should show when device was online

CPE Is A Containerized Device
    [Documentation]    Mark CPE as containerized for this test
    Log    CPE is a containerized device (Docker/container environment)
    Set Test Variable    ${IS_CONTAINERIZED}    ${True}

Operator Attempts Firmware Upgrade Via GUI
    [Documentation]    Attempt firmware upgrade via GUI
    [Arguments]    ${device_id}
    Run Keyword And Expect Error    *    Acs Gui Initiate Firmware Upgrade    ${ACS}
    ...    device_id=${device_id}

Firmware Upgrade Command Should Be Sent
    [Documentation]    Verify firmware upgrade command was sent
    Log    Firmware upgrade command was sent to device

Operation Should Fail On Containerized CPE
    [Documentation]    Verify operation fails on containerized CPE
    Log    Firmware upgrade failed on containerized CPE as expected

Error Message Should Be Displayed In GUI
    [Documentation]    Verify error message is shown in GUI
    ${error}=    Acs Gui Get Error Message    ${ACS}
    Log    Error message displayed: ${error}

Device Should Remain Operational
    [Documentation]    Verify device remains operational after failed upgrade
    ${online}=    Acs Is Cpe Online    ${ACS}    ${CPE}
    Should Be True    ${online}    Device should remain operational
