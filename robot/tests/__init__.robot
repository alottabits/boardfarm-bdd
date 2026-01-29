*** Settings ***
Documentation    Boardfarm BDD Robot Framework Test Suites
...              
...              This test suite contains Robot Framework implementations of BDD scenarios
...              that correspond to the system use cases defined in requirements/.
...              
...              All tests use the UseCaseLibrary for high-level test operations,
...              which maps to boardfarm3.use_cases for consistent behavior with pytest-bdd.
...
...              Test Suites:
...              - hello.robot: Basic smoke tests
...              - remote_cpe_reboot.robot: UC-12347 Remote CPE Reboot
...              - user_makes_one_way_call.robot: UC-12348 Voice Call Tests
...              - acs_gui_device_management.robot: UC-ACS-GUI-01 GUI Management
...              - device_class_initialization.robot: Device Class Tests

Library     robotframework_boardfarm.BoardfarmLibrary
Library     robotframework_boardfarm.UseCaseLibrary

Force Tags    boardfarm-bdd

*** Keywords ***
Suite Level Setup
    [Documentation]    Common setup for all test suites
    Log    Boardfarm BDD Robot Test Suite initialized
