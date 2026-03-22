# Use Case: ACS GUI Device Management

| Field | Value |
| --- | --- |
| ID | UC-ACS-GUI-01 |
| Status | Approved |
| Author(s) | |
| Date | |
| Test specifications | see [Traceability](#traceability) |

## Goal

Manage CPE devices through the ACS GUI to perform monitoring and operational tasks without requiring direct API access.

## Scope

The E2E system, including the ACS GUI, ACS backend, CPE, and network infrastructure.

## Primary Actor

Network Operator

## Stakeholders

| Stakeholder | Interest |
| --- | --- |
| Network Operator | Manages devices through GUI |
| ACS Administrator | Maintains GUI availability |
| Subscriber | Benefits from reliable device management |
| CPE | Receives commands and reports status |

## Level

User-goal

## Preconditions

1. The ACS GUI is accessible and operational.
2. The operator has valid credentials for GUI access.
3. Target CPE devices are registered with the ACS.

## Minimal Guarantees

- All GUI operations are logged by the ACS.
- Failed operations do not corrupt device state.
- The GUI remains accessible even if backend operations fail.
- Device data integrity is maintained.

## Success Guarantees

1. The operator can successfully authenticate to the ACS GUI.
2. The operator can search and locate registered devices.
3. Device status information is accurately displayed.
4. Operational commands (reboot, etc.) are successfully executed.
5. Parameter values can be retrieved and modified.
6. All GUI operations complete within acceptable timeframes.

## Trigger

A network operator needs to manage CPE devices through the ACS web interface.

## Main Success Scenario

1. Operator accesses the ACS GUI login page.
2. Operator enters valid credentials.
3. System authenticates the operator and displays the dashboard.
4. Operator searches for a specific CPE by device ID.
5. System displays the device in search results.
6. Operator navigates to device details.
7. System displays device status and information.
8. Operator initiates a device operation (e.g., reboot).
9. System executes the operation via TR-069.
10. System displays operation confirmation.
11. Operator logs out from the GUI.
12. Use case succeeds and all success guarantees are met.

## Extensions

- **2.a Invalid Credentials**:
  
  1. Operator enters invalid credentials.
  2. System displays authentication error.
  3. Operator re-enters credentials or requests password reset.
  4. Return to step 2 of main scenario.

- **4.a Device Not Found**:
  
  1. Operator searches for non-existent device ID.
  2. System returns empty search results.
  3. Operator verifies device ID and retries.
  4. Return to step 4 of main scenario.

- **7.a Device Offline**:
  
  1. Device is offline when details are requested.
  2. System displays "offline" status.
  3. System shows last known information.
  4. Operator acknowledges offline status.
  5. Continue with other operations or exit.

- **8.a Operation Fails**:
  
  1. Device operation firmware upgrade fails.
  2. System displays error message.
  3. Operator reviews error and may retry.
  4. System logs failure for troubleshooting.

## Technology and Data Variations

- **Authentication methods**: 
  
  - Username/password (basic auth)
  - API tokens (for automation)

- **Device identification**:
  
  - Serial number
  - MAC address
  - OUI-ProductClass-Serial composite ID
  - Custom device name

- **GUI operations**:
  
  - View device status and information
  - Reboot device
  - Get TR-069 parameters
  - Firmware upgrade (action will fail as containerized CPE does not support it)

- **Browser compatibility**:
  
  - Selenium WebDriver supports major browsers
  - Headless mode for CI/CD environments
  - Desktop and mobile viewports

- **UI resilience**:
  
  - Semantic element search adapts to minor UI changes
  - Element names, IDs, or locators can change
  - Functional metadata (aria-label, data-action) remains stable

## Traceability

| Artifact | pytest-bdd | Robot Framework |
| --- | --- | --- |
| Test specification | `tests/features/ACS GUI Device Management.feature` | |
| Step / keyword impl | `tests/step_defs/acs_steps.py` | |
| Use case code | `boardfarm3/use_cases/acs.py` | `boardfarm3/use_cases/acs.py` |

## Related Information

- This use case leverages the self-healing UI testing framework
- Semantic element search uses 20+ metadata attributes for element identification.
- Task-oriented methods abstract UI navigation from test logic.
- GUI operations complement NBI (API) operations for comprehensive testing.

