# Step Definition Validation Status

> **Purpose**: Track unit test coverage and validation status for step definition modules to ensure test code quality.

## Overview

This document tracks the validation of **step definitions** (the test code itself), not the system under test. Each step definition should have comprehensive unit tests to ensure its validation logic works correctly across different scenarios and testbeds.

---

## Coverage Summary

| Module | Total Functions | Unit Tested | Coverage % | Status |
|--------|----------------|-------------|------------|--------|
| `sip_phone_steps.py` | 45 | 0 | 0% | ⏳ To Do |
| `reboot_steps.py` | 12 | 0 | 0% | ⏳ To Do |
| `background_steps.py` | 8 | 0 | 0% | ⏳ To Do |

**Overall Progress**: 0 / 65 functions tested (0%)

**Last Updated**: TBD

---

## Module: sip_phone_steps.py

### Helper Functions

| Function | Unit Tests | Test Cases | Status | Notes |
|----------|-----------|------------|--------|-------|
| `get_phone_by_name` | ⏳ | - | To Do | Get phone from context by name |
| `get_phone_by_role` | ⏳ | - | To Do | Get phone by role (caller/callee) |
| `ensure_phone_registered` | ⏳ | - | To Do | Verify phone registration |
| `verify_phone_state` | ⏳ | - | To Do | Verify phone in expected state |
| `wait_for_phone_state` | ⏳ | - | To Do | Wait for state transition |
| `check_kamailio_active_calls` | ⏳ | - | To Do | Check active calls on server |
| `verify_sip_message_in_logs` | ⏳ | - | To Do | Verify SIP message in logs |
| `verify_rtp_session` | ⏳ | - | To Do | Verify RTP session active |
| `check_rtpengine_engagement` | ⏳ | - | To Do | Check RTPEngine status |

### Step Definitions

| Step Pattern | Function | Unit Tests | Test Cases | Priority | Status |
|--------------|----------|-----------|------------|----------|--------|
| "SIP server is running and operational" | `sip_server_is_running` | ⏳ | - | Low | To Do |
| "following phones are required" | `validate_use_case_phone_requirements` | ⏳ | - | Medium | To Do |
| "{phone_name} with number {number} on {location}" | `phone_registered_on_location` | ⏳ | - | Medium | To Do |
| "{caller} is caller and {callee} is callee" | `assign_caller_callee_roles` | ⏳ | - | Medium | To Do |
| "the {role} phone is idle" | `phone_is_idle` | ⏳ | - | **High** | To Do |
| "the {role} phone is in active call" | `phone_in_active_call` | ⏳ | - | **High** | To Do |
| "{role} takes phone off-hook" | `phone_off_hook` | ⏳ | - | Medium | To Do |
| "{caller} dials {callee}'s number" | `phone_dials_number` | ⏳ | - | **High** | To Do |
| "{role} answers the call" | `phone_answers_call` | ⏳ | - | **High** | To Do |
| "caller plays busy tone" | `caller_plays_busy_tone` | ⏳ | - | **High** | To Do |
| ... | ... | ... | ... | ... | ... |

---

## Module: reboot_steps.py

| Step Pattern | Function | Unit Tests | Test Cases | Priority | Status |
|--------------|----------|-----------|------------|----------|--------|
| TBD | TBD | ⏳ | - | - | To Do |

---

## Module: background_steps.py

| Step Pattern | Function | Unit Tests | Test Cases | Priority | Status |
|--------------|----------|-----------|------------|----------|--------|
| TBD | TBD | ⏳ | - | - | To Do |

---

## Test Coverage Details

### Completed Modules

*None yet*

### In Progress

*None yet*

### To Do (Priority Order)

1. **sip_phone_steps.py** - High priority (most complex validation logic)
   - Start with: `phone_is_idle`, `phone_dials_number`, `phone_answers_call`
   - Then: `phone_in_active_call`, `caller_plays_busy_tone`
   - Finally: Helper functions and remaining steps

2. **reboot_steps.py** - Medium priority
3. **background_steps.py** - Low priority

---

## Unit Test Standards

For each step definition, create tests covering:

### 1. Success Cases
- Step passes when validation conditions are met
- Expected behavior with valid inputs

### 2. Failure Cases
- Step fails with proper error message when validation fails
- Clear assertion errors

### 3. Edge Cases
- Invalid inputs (wrong types, None values)
- Missing context attributes
- Device failures/exceptions
- Timeout scenarios
- Boundary conditions

### Target Metrics
- **Minimum**: 3 test cases per function (success, failure, edge)
- **Goal**: 80% code coverage per module
- **All tests must pass** before marking function as validated

---

## Validation Workflow

When implementing/modifying a step definition:

1. **Identify the function** in the appropriate module
2. **Create unit tests** in `tests/unit/test_step_defs/test_<module>.py`
3. **Run tests**: `pytest tests/unit/test_step_defs/test_<module>.py -v`
4. **Measure coverage**: `pytest tests/unit/ --cov=tests/step_defs/<module> --cov-report=term`
5. **Update this document** with:
   - Function marked as unit tested ✓
   - Test case count
   - Coverage percentage
   - Date completed
6. **Commit** unit tests alongside step definitions

---

## Commands

### Run All Unit Tests
```bash
pytest tests/unit/test_step_defs/ -v
```

### Run Tests for Specific Module
```bash
pytest tests/unit/test_step_defs/test_sip_phone_steps.py -v
```

### Check Coverage
```bash
pytest tests/unit/ --cov=tests/step_defs --cov-report=term --cov-report=html
```

### Generate Coverage Report
```bash
pytest tests/unit/ --cov=tests/step_defs --cov-report=html
# Open htmlcov/index.html in browser
```

---

## Notes

### Why Track at Step Definition Level?

Step definitions are **reusable** across:
- Multiple scenarios
- Different feature files
- Various testbed configurations
- Different use cases

Therefore, unit tests for step definitions are **shared assets** that benefit all scenarios using those steps.

### Relationship to Scenarios

When implementing a scenario:
1. Scenario uses existing step definitions → Check if they have unit tests
2. Scenario needs new step definition → Create step + unit tests
3. Scenario needs modified step → Update step + update unit tests

### Out of Scope

This document does NOT track:
- System test results (scenario execution on real testbed)
- Testbed configurations
- Component versions
- Test results for actual system validation

Those belong in a separate test results tracking system (Level 2, to be designed later).
