# ACS GUI Testing - Quick Start

## Overview

This directory contains BDD scenarios that test ACS GUI functionality using the self-healing UI testing framework.

## Test Structure

### Use Case: UC-ACS-GUI-01 - ACS GUI Device Management
- **Requirement:** `requirements/UC-ACS-GUI-01 ACS GUI Device Management.md`
- **Feature File:** `tests/features/ACS GUI Device Management.feature`
- **Step Definitions:** `tests/step_defs/acs_gui_steps.py`

## Scenarios Covered

### ✅ Main Success Scenarios

#### Authentication
- **UC-ACS-GUI-01-Auth**: Login and logout functionality
- Tests: Valid credentials, session management, logout flow

#### Device Discovery
- **UC-ACS-GUI-01-Search**: Search device by ID
- Tests: Device search, result validation

#### Device Status
- **UC-ACS-GUI-01-Status**: View device status and information
- Tests: Online status, device details, last inform time

#### Device Operations
- **UC-ACS-GUI-01-Reboot**: Reboot device via GUI
- Tests: Reboot initiation, confirmation, device reconnection

#### Parameter Operations
- **UC-ACS-GUI-01-GetParam**: Retrieve device parameters
- Tests: Get TR-069 parameters, value display

### ✅ Extensions (Error Handling & Edge Cases)

#### Invalid Credentials
- **UC-ACS-GUI-01-2a**: Invalid credentials handling
- Tests: Authentication failure, error message display

#### Device Not Found
- **UC-ACS-GUI-01-4a**: Search for non-existent device
- Tests: Empty results, appropriate error message

#### Device Offline
- **UC-ACS-GUI-01-7a**: View offline device status
- Tests: Offline status display, last known information

#### Operation Failure
- **UC-ACS-GUI-01-8a**: Firmware upgrade fails on containerized CPE
- Tests: Operation failure handling, error display, device remains operational
- Note: Containerized CPE does not support firmware upgrade - this tests expected failure behavior

## Running the Tests

### Prerequisites

1. **GUI artifacts must be configured** in `bf_config/boardfarm_config_example.json`:
```json
{
    "gui_selector_file": "bf_config/gui_artifacts/genieacs/selectors.yaml",
    "gui_navigation_file": "bf_config/gui_artifacts/genieacs/navigation.yaml",
    "gui_headless": true
}
```

2. **Activate virtual environment**:
```bash
cd ~/projects/req-tst/boardfarm-bdd
source .venv-3.12/bin/activate
```

### Run All GUI Tests

```bash
pytest --log-level=DEBUG --log-cli-level=DEBUG \
  --html=report.html --self-contained-html \
  --board-name prplos-docker-1 \
  --env-config ./bf_config/boardfarm_env_example.json \
  --inventory-config ./bf_config/boardfarm_config_example.json \
  --legacy \
  --save-console-logs ./logs/ \
  tests/features/ACS\ GUI\ Device\ Management.feature \
  -v -s
```

### Run Specific Scenarios (using -k option)

**Authentication test:**
```bash
pytest -k "UC-ACS-GUI-01-Auth" -v -s \
  --board-name prplos-docker-1 \
  --env-config ./bf_config/boardfarm_env_example.json \
  --inventory-config ./bf_config/boardfarm_config_example.json \
  --legacy
```

**Device search:**
```bash
pytest -k "Search" -v -s --board-name prplos-docker-1 ...
```

**Status and information:**
```bash
pytest -k "Status" -v -s --board-name prplos-docker-1 ...
```

**Device operations (reboot):**
```bash
pytest -k "Reboot" -v -s --board-name prplos-docker-1 ...
```

**Parameter operations:**
```bash
pytest -k "Param" -v -s --board-name prplos-docker-1 ...
```

**Multiple scenarios:**
```bash
pytest -k "Auth or Search or Status" -v -s --board-name prplos-docker-1 ...
```

### Run Without GUI

If GUI is not configured, tests will be skipped automatically:
```bash
pytest tests/features/ACS\ GUI\ Device\ Management.feature -v
# Output: SKIPPED [1] (ACS GUI not configured for this testbed)
```

## Scenario Selection with -k Option

Use the `-k` option to run specific scenarios by matching scenario names:

| Pattern | Matches | Example |
|---------|---------|---------|
| `Auth` | Authentication scenarios | `pytest -k "Auth" -v -s` |
| `Search` | Search scenarios | `pytest -k "Search" -v -s` |
| `Status` | Status scenarios | `pytest -k "Status" -v -s` |
| `Reboot` | Reboot scenarios | `pytest -k "Reboot" -v -s` |
| `GetParam` | Parameter scenarios | `pytest -k "GetParam" -v -s` |
| `2a` | Invalid credentials | `pytest -k "2a" -v -s` |
| `4a` | Non-existent device | `pytest -k "4a" -v -s` |
| `7a` | Offline device | `pytest -k "7a" -v -s` |
| `8a` | Firmware upgrade failure | `pytest -k "8a" -v -s` |
| `Auth or Search or Reboot` | Multiple scenarios | `pytest -k "Auth or Search or Reboot" -v -s` |

## What Gets Tested

### Self-Healing Capabilities
- **Semantic element search**: Finds elements by function, not just ID/name
- **Resilience to UI changes**: 80%+ of element renames handled automatically
- **Rich metadata**: Uses 20+ attributes (aria-label, data-action, text, etc.)
- **Weighted scoring**: Smart matching algorithm for best element selection

### Task-Oriented Methods Tested
These scenarios test the following `GenieAcsGUI` methods:

**Authentication (3 methods):**
- `login(username, password)` - Login to GUI (✅ tested: success & failure)
- `logout()` - Logout from GUI (✅ tested)
- `is_logged_in()` - Check login status (✅ tested)

**Discovery (1 method tested):**
- `search_device(cpe_id)` - Search for device (✅ tested: found & not found)

**Status (3 methods):**
- `get_device_status(cpe_id)` - Get device status (✅ tested: online & offline)
- `verify_device_online(cpe_id, timeout)` - Wait for online (✅ tested)
- `get_last_inform_time(cpe_id)` - Get last inform timestamp (✅ tested)

**Operations (1 method tested):**
- `reboot_device_via_gui(cpe_id)` - Reboot device (✅ tested)

**Parameters (1 method tested):**
- `get_device_parameter_via_gui(cpe_id, param)` - Get parameter (✅ tested)

**Firmware (1 method tested):**
- `trigger_firmware_upgrade_via_gui(cpe_id, url)` - Start upgrade (✅ tested: expected failure on containerized CPE)

**Note:** Not all 18 methods are tested in these scenarios. Focus is on core functionality and error handling per requirements.

## Expected Results

### Successful Test Run

```
tests/features/ACS GUI Device Management.feature
✓ UC-ACS-GUI-01-Auth: Successful GUI Login and Logout          PASSED
✓ UC-ACS-GUI-01-Search: Search for Device by ID                PASSED
✓ UC-ACS-GUI-01-Status: View Device Status and Information     PASSED
✓ UC-ACS-GUI-01-Reboot: Reboot Device via GUI                  PASSED
✓ UC-ACS-GUI-01-GetParam: Retrieve Device Parameter via GUI    PASSED
✓ UC-ACS-GUI-01-2a: Invalid Credentials                        PASSED
✓ UC-ACS-GUI-01-4a: Search for Non-Existent Device             PASSED
✓ UC-ACS-GUI-01-7a: View Offline Device Status                 PASSED (or SKIPPED if no offline device)
✓ UC-ACS-GUI-01-8a: Firmware Upgrade Fails on Containerized    PASSED

9 scenarios (8-9 passed, 0-1 skipped)
```

**Note:** UC-ACS-GUI-01-7a may be skipped if no offline device is available. UC-ACS-GUI-01-8a requires a containerized CPE.

### Headless Mode

Tests run in headless Chrome by default:
- ✅ Faster execution
- ✅ No UI window displayed
- ✅ CI/CD compatible
- ✅ Screenshot capability available

## Troubleshooting

### GUI Not Configured
```
SKIPPED: ACS GUI not configured for this testbed
```
**Solution:** Add GUI config fields to device config (see Prerequisites)

### Selenium Driver Error
```
ERROR: ChromeDriver not found
```
**Solution:** Selenium Manager auto-downloads drivers. Ensure internet access or pre-install ChromeDriver

### Element Not Found
```
ERROR: Element not found after 20 seconds
```
**Solution:** Check if UI structure changed significantly. May need to regenerate artifacts:
```bash
cd tests/ui_helpers
python discover_ui.py --url http://localhost:7557 --output ui_map.json
python -m boardfarm3.lib.gui.selector_generator --input ui_map.json --output selectors.yaml
python -m boardfarm3.lib.gui.navigation_generator --input ui_map.json --output navigation.yaml
```

### Timeout Waiting for Device
```
ERROR: Device did not reconnect within 60 seconds
```
**Solution:** Device may be slow to reboot. Increase timeout or check device health

## Benefits of This Approach

✅ **Maintainable**: Task-oriented methods hide UI complexity  
✅ **Resilient**: Self-healing tests adapt to UI changes  
✅ **Readable**: BDD scenarios document expected behavior  
✅ **Reusable**: Step definitions work across scenarios  
✅ **Traceable**: Requirements → Features → Steps → Code  
✅ **Vendor-Neutral**: Same pattern works for any ACS  

## Next Steps

1. **Run tests** with your testbed configuration
2. **Review results** in HTML report
3. **Add more scenarios** for additional use cases
4. **Extend to other ACS vendors** (Axiros, etc.)
5. **Integrate into CI/CD** with headless mode

## Related Documentation

- **Framework:** `boardfarm/boardfarm3/lib/gui/README.md`
- **Template:** `boardfarm/boardfarm3/templates/acs/acs_gui.py`
- **Implementation:** `boardfarm/boardfarm3/devices/genie_acs.py`
- **Configuration:** `boardfarm-bdd/tests/ui_helpers/README.md`

---

**Last Updated:** December 7, 2024  
**Status:** ✅ Ready for testing

