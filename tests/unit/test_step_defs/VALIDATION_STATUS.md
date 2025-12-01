# Step Definition Validation Status

> **Purpose**: Track unit test coverage and validation status for step definition modules to ensure test code quality.

## Overview

This document tracks the validation of **step definitions** (the test code itself), not the system under test. Each step definition should have comprehensive unit tests to ensure its validation logic works correctly across different scenarios and testbeds.

---

## Coverage Summary

| Module | Total Statements | Unit Tests | Coverage % | Status |
|--------|-----------------|------------|------------|--------|
| `sip_phone_steps.py` | 548 | 57 | 68% | ✅ In Progress |
| `acs_steps.py` | 125 | 0 | 16% | ⏳ To Do |
| `cpe_steps.py` | 306 | 0 | 9% | ⏳ To Do |
| `background_steps.py` | 99 | 0 | 11% | ⏳ To Do |
| `operator_steps.py` | 27 | 0 | 37% | ⏳ To Do |
| `helpers.py` | 127 | 0 | 14% | ⏳ To Do |
| `hello_steps.py` | 5 | 0 | 60% | ⏳ To Do |

**Overall Progress**: 57 unit tests / 1237 total statements (37% overall coverage)

**Last Updated**: 2025-12-01

---

## Module: sip_phone_steps.py

**Status**: ✅ 68% Coverage (548 statements, 174 missed) | 57 Unit Tests

### Helper Functions

| Function | Unit Tests | Test Cases | Status | Notes |
|----------|-----------|------------|--------|-------|
| `get_phone_by_name` | ✅ | 2 | **Done** | Success + failure cases |
| `get_phone_by_role` | ✅ | 5 | **Done** | Caller, callee, not set, invalid |
| `ensure_phone_registered` | ✅ | 2 | **Done** | Success + failure cases |
| `verify_phone_state` | ✅ | 3 | **Done** | Success, failure, invalid state |
| `wait_for_phone_state` | ✅ | 2 | **Done** | Success + timeout cases |
| `verify_rtp_session` | ✅ | 4 | **Done** | UDP detection, port range, exceptions |
| `discover_available_sip_phones_from_devices` | ✅ | 1 | **Done** | Phone discovery from devices |
| `map_phones_to_requirements` | ✅ | 2 | **Done** | Success + insufficient phones |
| `check_kamailio_active_calls` | ⏳ | - | To Do | Check active calls on server |
| `verify_sip_message_in_logs` | ⏳ | - | To Do | Verify SIP message in logs |
| `check_rtpengine_engagement` | ⏳ | - | To Do | Check RTPEngine status |

### Step Definitions

| Step Pattern | Function | Unit Tests | Test Cases | Priority | Status |
|--------------|----------|-----------|------------|----------|--------|
| "SIP server is running and operational" | `sip_server_is_running` | ✅ | 2 | Low | **Done** |
| "following phones are required" | `validate_use_case_phone_requirements` | ✅ | 2 | Medium | **Done** |
| "{caller} is caller and {callee} is callee" | `assign_caller_callee_roles` | ✅ | 2 | Medium | **Done** |
| "the {role} phone is idle" | `phone_is_idle` | ✅ | 2 | **High** | **Done** |
| "the {role} phone is in active call" | `phone_in_active_call` | ✅ | 3 | **High** | **Done** |
| "{caller} dials {callee}'s number" | `phone_dials_number` | ✅ | 2 | **High** | **Done** |
| "{role} dials invalid number" | `phone_dials_invalid_number` | ✅ | 1 | Medium | **Done** |
| "{role} answers the call" | `phone_answers_call` | ✅ | 2 | **High** | **Done** |
| "{role} hangs up" | `phone_hangs_up` | ✅ | 1 | Medium | **Done** |
| "{role} phone starts ringing" | `phone_starts_ringing` | ✅ | 2 | High | **Done** |
| "caller calls callee" | `caller_calls_callee` | ✅ | 1 | Medium | **Done** |
| "{role} plays dial tone" | `phone_plays_dial_tone` | ✅ | 3 | Medium | **Done** |
| "{role} plays busy tone" | `phone_plays_busy_tone` | ✅ | 3 | **High** | **Done** |
| "caller plays busy tone" | `caller_plays_busy_tone` | ✅ | 2 | **High** | **Done** |
| "both phones connected" | `both_phones_connected` | ✅ | 2 | **High** | **Done** |
| "both phones return to idle" | `both_phones_return_to_idle` | ✅ | 2 | High | **Done** |
| "SIP server sends {response}" | `sip_server_sends_response` | ✅ | 3 | High | **Done** |

---

## Module: acs_steps.py

**Status**: ⏳ 16% Coverage (125 statements, 105 missed) | 0 Unit Tests

| Step Pattern | Function | Unit Tests | Test Cases | Priority | Status |
|--------------|----------|-----------|------------|----------|--------|
| TBD | TBD | ⏳ | - | Medium | To Do |

---

## Module: cpe_steps.py

**Status**: ⏳ 9% Coverage (306 statements, 279 missed) | 0 Unit Tests

| Step Pattern | Function | Unit Tests | Test Cases | Priority | Status |
|--------------|----------|-----------|------------|----------|--------|
| TBD | TBD | ⏳ | - | Medium | To Do |

---

## Module: background_steps.py

**Status**: ⏳ 11% Coverage (99 statements, 88 missed) | 0 Unit Tests

| Step Pattern | Function | Unit Tests | Test Cases | Priority | Status |
|--------------|----------|-----------|------------|----------|--------|
| TBD | TBD | ⏳ | - | Low | To Do |

---

## Module: operator_steps.py

**Status**: ⏳ 37% Coverage (27 statements, 17 missed) | 0 Unit Tests

| Step Pattern | Function | Unit Tests | Test Cases | Priority | Status |
|--------------|----------|-----------|------------|----------|--------|
| TBD | TBD | ⏳ | - | Low | To Do |

---

## Test Coverage Details

### Completed Modules

*None yet - aiming for 80%+ coverage*

### In Progress

**sip_phone_steps.py** - 68% coverage (57 tests)
- ✅ Core helper functions tested
- ✅ Most critical step definitions tested
- ⏳ Remaining: 3 helper functions, additional edge cases
- 🎯 Target: 80% coverage

### To Do (Priority Order)

1. **sip_phone_steps.py** - Continue to 80%+ coverage
   - Add tests for: `check_kamailio_active_calls`, `verify_sip_message_in_logs`, `check_rtpengine_engagement`
   - Add more edge cases for existing functions

2. **acs_steps.py** - Medium priority (125 statements, 16% coverage)
3. **cpe_steps.py** - Medium priority (306 statements, 9% coverage)
4. **background_steps.py** - Low priority (99 statements, 11% coverage)
5. **operator_steps.py** - Low priority (27 statements, 37% coverage)

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
