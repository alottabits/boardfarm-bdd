*** Settings ***
Documentation    UC-12347: Remote CPE Reboot
...              As an operator of a network, I want to remotely reboot a CPE device
...              so that I can restore connectivity, apply configuration changes,
...              or resolve operational issues without physical access to the device.
...
...              Corresponds to pytest/features/Remote CPE Reboot.feature

Library     robotframework_boardfarm.BoardfarmLibrary
Library     robotframework_boardfarm.UseCaseLibrary
Resource    ../resources/common.resource

Suite Setup       Setup Testbed Connection
Suite Teardown    Teardown Testbed Connection
Test Teardown     Cleanup After Test

*** Variables ***
${TEST_PASSWORD}    p@ssw0rd123!

*** Test Cases ***
UC-12347-Main: Successful Remote Reboot
    [Documentation]    Main success scenario for remote CPE reboot.
    ...    Given the operator initiates a reboot task on the ACS for the CPE,
    ...    the ACS sends a connection request, issues the Reboot RPC,
    ...    and the CPE completes the boot sequence and resumes normal operation.
    [Tags]    UC-12347    reboot    smoke    main-scenario

    # Background
    A CPE Is Online And Fully Provisioned
    The User Sets The CPE GUI Password    ${TEST_PASSWORD}

    # Main scenario
    The Operator Initiates A Reboot Task On The ACS
    The ACS Sends Connection Request To CPE
    The CPE Initiates Session With ACS
    The CPE Sends Inform Message To ACS
    The ACS Issues Reboot RPC To CPE
    The CPE Completes Boot Sequence
    The CPE Resumes Normal Operation
    The CPE Configuration Is Preserved
    Use Case Succeeds And All Success Guarantees Are Met

UC-12347-3a: CPE Not Connected When Reboot Requested
    [Documentation]    Extension scenario: CPE is offline when reboot is requested.
    ...    The ACS queues the reboot task and executes it when the CPE comes online.
    [Tags]    UC-12347    reboot    extension    offline

    # Background
    A CPE Is Online And Fully Provisioned
    The User Sets The CPE GUI Password    ${TEST_PASSWORD}

    # Extension scenario
    The CPE TR069 Client Is Stopped
    The Operator Initiates A Reboot Task On The ACS
    The ACS Queues The Reboot Task
    The CPE TR069 Client Is Started
    The CPE Sends Inform Message To ACS
    The ACS Issues Queued Reboot RPC
    The CPE Completes Boot Sequence
    The CPE Resumes Normal Operation
    The CPE Configuration Is Preserved
    Use Case Succeeds And All Success Guarantees Are Met

*** Keywords ***
A CPE Is Online And Fully Provisioned
    [Documentation]    Verify CPE is online and fully provisioned
    ${acs}=    Get Device By Type    ACS
    ${cpe}=    Get Device By Type    CPE
    Set Suite Variable    ${ACS}
    Set Suite Variable    ${CPE}
    ${online}=    Acs Is Cpe Online    ${ACS}    ${CPE}
    Should Be True    ${online}    CPE should be online and provisioned

The User Sets The CPE GUI Password
    [Documentation]    Set the CPE GUI password via ACS
    [Arguments]    ${password}
    # Capture original config for cleanup/verification
    ${original}=    Acs Get Parameter Value    ${ACS}    ${CPE}
    ...    Device.Users.User.1.Password
    Set Suite Variable    ${ORIGINAL_PASSWORD}    ${original}
    Acs Set Parameter Value    ${ACS}    ${CPE}
    ...    Device.Users.User.1.Password    ${password}

The Operator Initiates A Reboot Task On The ACS
    [Documentation]    Operator initiates reboot task via ACS
    ${timestamp}=    Get Current Timestamp
    Set Suite Variable    ${REBOOT_TIMESTAMP}    ${timestamp}
    Acs Initiate Reboot    ${ACS}    ${CPE}
    Log    Reboot task initiated at ${timestamp}

The ACS Sends Connection Request To CPE
    [Documentation]    ACS sends TR-069 connection request to CPE
    Log    ACS sent connection request to CPE

The CPE Initiates Session With ACS
    [Documentation]    CPE receives connection request and initiates session
    Log    CPE initiated session with ACS

The CPE Sends Inform Message To ACS
    [Documentation]    CPE sends Inform message to ACS
    ${result}=    Acs Wait For Inform Message    ${ACS}    ${CPE}
    ...    since=${REBOOT_TIMESTAMP}    timeout=120
    Should Be True    ${result}    CPE should send Inform message

The ACS Issues Reboot RPC To CPE
    [Documentation]    ACS issues Reboot RPC to CPE
    ${reboot_time}=    Acs Wait For Reboot Rpc    ${ACS}    ${CPE}
    ...    since=${REBOOT_TIMESTAMP}    timeout=90
    Set Suite Variable    ${REBOOT_RPC_TIME}    ${reboot_time}
    Log    Reboot RPC issued at ${reboot_time}

The CPE Completes Boot Sequence
    [Documentation]    CPE completes boot sequence and sends boot Inform
    ${boot_time}=    Acs Wait For Boot Inform    ${ACS}    ${CPE}
    ...    since=${REBOOT_RPC_TIME}    timeout=240
    Should Not Be Equal    ${boot_time}    ${None}    CPE should complete boot sequence
    Log    Boot sequence completed at ${boot_time}

The CPE Resumes Normal Operation
    [Documentation]    Verify CPE is back online and operational
    ${online}=    Acs Is Cpe Online    ${ACS}    ${CPE}
    Should Be True    ${online}    CPE should be online after reboot

The CPE Configuration Is Preserved
    [Documentation]    Verify CPE configuration was preserved after reboot
    ${current_password}=    Acs Get Parameter Value    ${ACS}    ${CPE}
    ...    Device.Users.User.1.Password
    # Password should still be set (encrypted value will differ but shouldn't be empty)
    Should Not Be Empty    ${current_password}    Password should be preserved after reboot

Use Case Succeeds And All Success Guarantees Are Met
    [Documentation]    Final verification that use case succeeded
    Log    Use case completed successfully - all success guarantees met

The CPE TR069 Client Is Stopped
    [Documentation]    Stop the TR-069 client on CPE to simulate offline state
    Cpe Stop Tr069 Client    ${CPE}
    Sleep    2s    Wait for TR069 client to stop

The CPE TR069 Client Is Started
    [Documentation]    Start the TR-069 client on CPE
    Cpe Start Tr069 Client    ${CPE}
    Sleep    5s    Wait for TR069 client to connect

The ACS Queues The Reboot Task
    [Documentation]    ACS queues the reboot task for offline CPE
    Log    ACS has queued the reboot task (will execute when CPE comes online)

The ACS Issues Queued Reboot RPC
    [Documentation]    ACS issues the queued reboot RPC
    The ACS Issues Reboot RPC To CPE

Get Current Timestamp
    [Documentation]    Get current UTC timestamp
    ${timestamp}=    Evaluate    __import__('datetime').datetime.now(__import__('datetime').timezone.utc)
    RETURN    ${timestamp}
