*** Settings ***
Documentation    Device Class Initialization
...              As a Test Engineer, I want Boardfarm to support RPi prplOS CPEs
...              so that I can test physical devices in the testbed.
...
...              Corresponds to tests/features/Device Class Initialization.feature

Library     robotframework_boardfarm.BoardfarmLibrary
Library     ../libraries/boardfarm_keywords.py
Library     ../libraries/device_class_keywords.py
Library     ../libraries/acs_keywords.py
Resource    ../resources/common.resource

Suite Setup       Setup Device Initialization Test
Suite Teardown    Teardown Device Initialization Test

*** Test Cases ***
UC-Device-Init-Main: Successful Device Initialization
    [Documentation]    Main success scenario: Boardfarm initializes RPi prplOS CPE
    [Tags]    device-init    prplos    rpi    main-scenario

    # Given testbed is configured with RPi prplOS CPE
    The Testbed Is Configured With RPi PrplOS CPE    ${DEVICE_MANAGER}

    # When Boardfarm instantiates and connects
    ${cpe}=    Boardfarm Instantiates Device From Configuration    ${DEVICE_MANAGER}
    Set Suite Variable    ${CPE}    ${cpe}
    Boardfarm Connects To Serial Console    ${DEVICE_MANAGER}
    Boardfarm Boots The Device    ${DEVICE_MANAGER}

    # Then device comes online
    Device Is Online    ${DEVICE_MANAGER}
    Device Registers With ACS    ${DEVICE_MANAGER}

UC-Device-Init-1a: Device Not Found in Configuration
    [Documentation]    Extension: Configuration missing device definition
    [Tags]    device-init    error    configuration

    # Given configuration is missing device
    Testbed Missing Device

    # When Boardfarm attempts to instantiate
    # Then configuration error is raised
    Boardfarm Instantiation Should Fail With Config Error

UC-Device-Init-4a: ACS Registration Failure
    [Documentation]    Extension: Device fails to register with ACS
    [Tags]    device-init    error    acs    registration

    # Given device is instantiated and booted
    ${cpe}=    Boardfarm Instantiates Device From Configuration    ${DEVICE_MANAGER}
    Set Suite Variable    ${CPE}    ${cpe}
    Boardfarm Boots The Device    ${DEVICE_MANAGER}

    # When ACS is unreachable
    ACS Is Unreachable

    # Then registration fails
    Device Fails ACS Registration

*** Keywords ***
Setup Device Initialization Test
    [Documentation]    Initialize test environment
    ${device_manager}=    Get Device Manager
    Set Suite Variable    ${DEVICE_MANAGER}    ${device_manager}
    ${acs}=    Get Device By Type    ACS
    Set Suite Variable    ${ACS}
    Log    Device initialization test environment ready

Teardown Device Initialization Test
    [Documentation]    Clean up test environment
    Log    Device initialization test complete

Boardfarm Instantiation Should Fail With Config Error
    [Documentation]    Verify instantiation fails with config error
    ${error_raised}=    Run Keyword And Return Status
    ...    Get Device By Type    NonExistentDeviceType
    Should Not Be True    ${error_raised}    Configuration error should be raised
    Configuration Error Raised
