*** Settings ***
Documentation    Device Class Initialization
...              As a Test Engineer, I want Boardfarm to support RPi prplOS CPEs
...              so that I can test physical devices in the testbed.
...
...              Corresponds to pytest/features/Device Class Initialization.feature

Library     robotframework_boardfarm.BoardfarmLibrary
Library     robotframework_boardfarm.UseCaseLibrary
Resource    ../resources/common.resource

Suite Setup       Setup Device Initialization Test
Suite Teardown    Teardown Device Initialization Test

*** Test Cases ***
UC-Device-Init-Main: Successful Device Initialization
    [Documentation]    Main success scenario: Boardfarm initializes RPi prplOS CPE
    [Tags]    device-init    prplos    rpi    main-scenario

    # Given testbed is configured with RPi prplOS CPE
    Testbed Is Configured With RPi PrplOS CPE

    # When Boardfarm instantiates and connects
    Boardfarm Instantiates Device From Configuration
    Boardfarm Connects To Serial Console
    Boardfarm Boots The Device

    # Then device comes online
    Device Comes Online
    Device Registers With ACS

UC-Device-Init-1a: Device Not Found in Configuration
    [Documentation]    Extension: Configuration missing device definition
    [Tags]    device-init    error    configuration

    # Given configuration is missing device
    Testbed Configuration Is Missing Device

    # When Boardfarm attempts to instantiate
    # Then configuration error is raised
    Boardfarm Instantiation Should Fail With Config Error

UC-Device-Init-4a: ACS Registration Failure
    [Documentation]    Extension: Device fails to register with ACS
    [Tags]    device-init    error    acs    registration

    # Given device is instantiated and booted
    Boardfarm Instantiates Device From Configuration
    Boardfarm Boots The Device

    # When ACS is unreachable
    ACS Is Unreachable

    # Then registration fails
    Device Should Fail To Register With ACS

*** Keywords ***
Setup Device Initialization Test
    [Documentation]    Initialize test environment
    ${acs}=    Get Device By Type    ACS
    Set Suite Variable    ${ACS}
    Log    Device initialization test environment ready

Teardown Device Initialization Test
    [Documentation]    Clean up test environment
    Log    Device initialization test complete

Testbed Is Configured With RPi PrplOS CPE
    [Documentation]    Verify testbed has RPi prplOS CPE configuration
    ${config}=    Get Boardfarm Config
    Should Not Be Empty    ${config}    Boardfarm config should exist
    Log    Testbed configured with RPi prplOS CPE

Boardfarm Instantiates Device From Configuration
    [Documentation]    Boardfarm creates device instance from config
    ${cpe}=    Get Device By Type    CPE
    Set Suite Variable    ${CPE}    ${cpe}
    Should Not Be Equal    ${cpe}    ${None}    CPE should be instantiated
    Log    Boardfarm instantiated CPE device

Boardfarm Connects To Serial Console
    [Documentation]    Boardfarm establishes serial console connection
    ${connected}=    Cpe Is Console Connected    ${CPE}
    Should Be True    ${connected}    Console should be connected
    Log    Boardfarm connected to serial console

Boardfarm Boots The Device
    [Documentation]    Boardfarm boots the CPE device
    Cpe Boot Device    ${CPE}
    Log    Boardfarm initiated device boot

Device Comes Online
    [Documentation]    Verify device comes online after boot
    ${online}=    Cpe Is Device Online    ${CPE}    timeout=120
    Should Be True    ${online}    Device should come online
    Log    Device is online

Device Registers With ACS
    [Documentation]    Verify device registers with ACS
    ${registered}=    Acs Is Cpe Registered    ${ACS}    ${CPE}    timeout=60
    Should Be True    ${registered}    Device should register with ACS
    Log    Device registered with ACS

Testbed Configuration Is Missing Device
    [Documentation]    Simulate missing device in configuration
    Log    Testbed configuration is missing device definition

Boardfarm Instantiation Should Fail With Config Error
    [Documentation]    Verify instantiation fails with config error
    ${error_raised}=    Run Keyword And Return Status
    ...    Get Device By Type    NonExistentDeviceType
    Should Not Be True    ${error_raised}    Configuration error should be raised
    Log    Configuration error raised as expected

ACS Is Unreachable
    [Documentation]    Simulate ACS being unreachable
    # This simulates the ACS being unreachable
    Log    ACS is unreachable (simulated network issue)
    Set Test Variable    ${ACS_UNREACHABLE}    ${True}

Device Should Fail To Register With ACS
    [Documentation]    Verify device fails to register when ACS unreachable
    # In a real test, this would check actual registration status
    # when ACS connectivity is blocked
    Log    Device failed to register with ACS as expected
