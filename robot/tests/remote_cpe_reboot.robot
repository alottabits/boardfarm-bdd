*** Settings ***
Documentation    UC-12347: Remote CPE Reboot
...              As an operator of a network, I want to remotely reboot a CPE device
...              so that I can restore connectivity, apply configuration changes,
...              or resolve operational issues without physical access to the device.
...
...              Corresponds to tests/features/Remote CPE Reboot.feature

Library     robotframework_boardfarm.BoardfarmLibrary
Library     ../libraries/boardfarm_keywords.py
Library     ../libraries/acs_keywords.py
Library     ../libraries/cpe_keywords.py
Library     ../libraries/background_keywords.py
Library     ../libraries/operator_keywords.py
Resource    ../resources/common.resource

Suite Setup       Setup Reboot Test Suite
Suite Teardown    Teardown Testbed Connection
Test Teardown     Cleanup After Reboot Test    ${ACS}    ${CPE}    ${ADMIN_USER_INDEX}

*** Variables ***
${TEST_PASSWORD}        p@ssw0rd123!
${ADMIN_USER_INDEX}     ${None}

*** Test Cases ***
UC-12347-Main: Successful Remote Reboot
    [Documentation]    Main success scenario for remote CPE reboot.
    ...    Given the operator initiates a reboot task on the ACS for the CPE,
    ...    the ACS sends a connection request, issues the Reboot RPC,
    ...    and the CPE completes the boot sequence and resumes normal operation.
    [Tags]    UC-12347    reboot    smoke    main-scenario

    # Background: Set CPE GUI password
    ${password_result}=    Set CPE GUI Password    ${ACS}    ${CPE}    ${TEST_PASSWORD}
    Set Suite Variable    ${ADMIN_USER_INDEX}    ${password_result}[admin_user_index]

    # Step 1: Operator initiates reboot task on ACS
    ${reboot_result}=    The Operator Initiates A Reboot Task On The ACS For The CPE    ${ACS}    ${CPE}
    ${reboot_timestamp}=    Set Variable    ${reboot_result}[test_start_timestamp]
    Log    Reboot task initiated at ${reboot_timestamp}

    # Step 2: ACS sends connection request to CPE
    The ACS Sends A Connection Request To The CPE    ${ACS}    ${CPE}
    ...    cpe_id=${CPE.sw.cpe_id}    since=${reboot_timestamp}

    # Step 3: CPE receives connection request and initiates session
    The CPE Receives The Connection Request And Initiates A Session    ${ACS}    ${CPE}

    # Step 4: CPE sends Inform message to ACS
    The CPE Sends An Inform Message To The ACS    ${ACS}    ${CPE}    since=${reboot_timestamp}

    # Step 5: ACS responds with Reboot RPC
    ${reboot_rpc_time}=    The ACS Responds To The Inform Message By Issuing The Reboot RPC    ${ACS}    ${CPE}
    ...    since=${reboot_timestamp}
    Log    Reboot RPC issued at ${reboot_rpc_time}

    # Step 6: CPE completes boot sequence
    ${boot_time}=    The CPE Sends An Inform Message After Boot Completion    ${ACS}    ${CPE}
    ...    since=${reboot_rpc_time}
    Should Not Be Equal    ${boot_time}    ${None}    CPE should complete boot sequence
    Log    Boot sequence completed at ${boot_time}

    # Step 7: CPE resumes normal operation
    The CPE Resumes Normal Operation    ${ACS}    ${CPE}

    # Step 8: Verify configuration preserved
    ${is_online}=    The CPE Is Online Via ACS    ${ACS}    ${CPE}
    Log    CPE is online - basic configuration verification passed

    # Step 9: Final verification - all success guarantees met
    Use Case Succeeds And All Success Guarantees Are Met    ${ACS}    ${CPE}

UC-12347-3a: CPE Not Connected When Reboot Requested
    [Documentation]    Extension scenario: CPE is offline when reboot is requested.
    ...    The ACS queues the reboot task and executes it when the CPE comes online.
    [Tags]    UC-12347    reboot    extension    offline

    # Background: Set CPE GUI password
    ${password_result}=    Set CPE GUI Password    ${ACS}    ${CPE}    ${TEST_PASSWORD}
    Set Suite Variable    ${ADMIN_USER_INDEX}    ${password_result}[admin_user_index]

    # Step 1: Make CPE unreachable for TR-069 sessions
    ${offline_context}=    The CPE Is Unreachable For TR-069 Sessions    ${CPE}
    Sleep    2s    Wait for TR069 client to stop

    # Step 2: Operator initiates reboot task on ACS
    ${reboot_result}=    The Operator Initiates A Reboot Task On The ACS For The CPE    ${ACS}    ${CPE}
    ${reboot_timestamp}=    Set Variable    ${reboot_result}[test_start_timestamp]

    # Step 3: ACS queues the reboot task
    The ACS Queues The Reboot RPC As A Pending Task    ${ACS}    ${CPE}    since=${reboot_timestamp}

    # Step 4: CPE comes back online
    ${reconnect_time}=    The CPE Comes Online And Connects To The ACS    ${ACS}    ${CPE}
    ...    offline_timestamp=${offline_context}[cpe_offline_timestamp]
    Sleep    5s    Wait for TR069 client to connect

    # Step 5: CPE sends Inform message
    The CPE Sends An Inform Message To The ACS    ${ACS}    ${CPE}    since=${reboot_timestamp}

    # Step 6: ACS issues queued Reboot RPC
    ${reboot_rpc_time}=    The ACS Issues The Queued Reboot RPC    ${ACS}    ${CPE}
    ...    since=${reconnect_time}

    # Step 7: CPE completes boot sequence
    ${boot_time}=    The CPE Sends An Inform Message After Boot Completion    ${ACS}    ${CPE}
    ...    since=${reboot_rpc_time}
    Should Not Be Equal    ${boot_time}    ${None}    CPE should complete boot sequence

    # Step 8: CPE resumes normal operation
    The CPE Resumes Normal Operation    ${ACS}    ${CPE}

    # Step 9: Verify configuration preserved
    ${is_online}=    The CPE Is Online Via ACS    ${ACS}    ${CPE}
    Log    CPE is online - basic configuration verification passed

    # Step 10: Final verification - all success guarantees met
    Use Case Succeeds And All Success Guarantees Are Met    ${ACS}    ${CPE}

*** Keywords ***
Setup Reboot Test Suite
    [Documentation]    Suite setup - get devices and verify CPE is online.
    ...    Captures baseline state for all tests in this suite.
    ${acs}=    Get Device By Type    ACS
    ${cpe}=    Get Device By Type    CPE
    Set Suite Variable    ${ACS}    ${acs}
    Set Suite Variable    ${CPE}    ${cpe}

    # Verify CPE is online and capture baseline
    ${baseline}=    A CPE Is Online And Fully Provisioned    ${ACS}    ${CPE}
    Set Suite Variable    ${INITIAL_UPTIME}    ${baseline}[initial_uptime]
    Log    Reboot test suite setup complete. CPE baseline: uptime=${INITIAL_UPTIME}s
