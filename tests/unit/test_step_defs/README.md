# Unit Testing for Step Definitions

## Purpose

This directory contains **unit tests for step definitions** to ensure the test code itself is correct and reliable.

## What We Test

**System under test**: The step definitions (validation logic in `tests/step_defs/`)

**Goal**: Ensure step definitions properly validate conditions and fail correctly when expected

**Not tested here**: The actual CPE/SIP/ACS system behavior (that's tested via scenarios with full testbed)

## Structure

```
tests/unit/test_step_defs/
├── README.md                    # This file
├── VALIDATION_STATUS.md         # Coverage tracking
├── test_sip_phone_steps.py      # Unit tests for sip_phone_steps.py
├── test_reboot_steps.py         # Unit tests for reboot_steps.py
└── ...
```

## Quick Start

### Run All Unit Tests
```bash
pytest tests/unit/test_step_defs/ -v
```

### Run Specific Module Tests
```bash
pytest tests/unit/test_step_defs/test_sip_phone_steps.py -v
```

### Check Coverage
```bash
pytest tests/unit/ --cov=tests/step_defs --cov-report=term
```

## Writing Unit Tests

### 1. Use Mocks from tests/unit/mocks/

```python
from tests.unit.mocks.mock_context import MockContext
from tests.unit.mocks.mock_devices import MockSIPPhone, MockSIPServer

def test_phone_is_idle_success():
    # Arrange
    context = MockContext()
    phone = MockSIPPhone(name="test_phone")
    phone._state = "idle"
    context.caller = phone
    
    # Act & Assert
    phone_is_idle("caller", context)  # Should not raise
```

### 2. Test Success, Failure, and Edge Cases

```python
class TestPhoneIsIdle:
    def test_success_when_idle(self):
        """Step passes when phone is idle."""
        # ...
    
    def test_failure_when_not_idle(self):
        """Step fails with AssertionError when phone is not idle."""
        # ...
    
    def test_failure_missing_context(self):
        """Step fails when phone not in context."""
        # ...
```

### 3. Update VALIDATION_STATUS.md

After creating tests, update the validation status:
- Mark function as ✓ Unit Tested
- Record test case count
- Update coverage percentage

## Test Standards

Each step definition function should have:
- ✅ At least 3 test cases (success, failure, edge)
- ✅ Tests pass consistently
- ✅ Target: 80% code coverage

## Tracking

See [`VALIDATION_STATUS.md`](./VALIDATION_STATUS.md) for:
- Current coverage by module
- Which functions have unit tests
- Priority order for implementation

## Why Unit Test Step Definitions?

1. **Reusability**: Step definitions are shared across scenarios - one bug affects many tests
2. **Fast feedback**: Unit tests run in milliseconds vs minutes for full testbed
3. **Reliable tests**: Ensures validation logic works before using in scenarios
4. **Easy debugging**: Pinpoints exactly which step has faulty logic
5. **Testbed independence**: Tests work without containers or hardware

## Integration with Workflow

When using `/automate_scenario`:
1. Check if step definitions exist
2. **Check if step definitions have unit tests** (in VALIDATION_STATUS.md)
3. If no unit tests exist, create them
4. Run unit tests to validate step logic
5. Then run scenario with full testbed
