# Step-by-Step Debugging Guide

This guide explains how to debug pytest-bdd scenarios step by step.

## Quick Start: Test One Step at a Time

### Method 1: Use the Debug Feature File

1. **Edit `tests/features/debug-step-by-step.feature`**
   - Uncomment the step you want to test
   - Comment out other steps
   - Run: `pytest -k "debug" -v`

2. **Example: Test only the background step**
   ```gherkin
   Feature: Debug Step by Step
     Scenario: Test Individual Steps
       Given a CPE is online and fully provisioned
   ```
   ```bash
   pytest -k "debug" -v
   ```

### Method 2: Use pytest Options

#### Stop at First Failure
```bash
# Stop at first failure and show detailed traceback
pytest -k "uc12345main" -x --tb=long -v

# Stop at first failure and drop into debugger
pytest -k "uc12345main" -x --pdb -v
```

#### Stepwise Mode (Continue from Last Failure)
```bash
# Run until first failure, then continue from there next time
pytest -k "uc12345main" --stepwise -v

# Skip the failing test and continue
pytest -k "uc12345main" --stepwise-skip -v
```

#### Verbose Output
```bash
# Show all test names and steps
pytest -k "uc12345main" -vv

# Show fixture setup/teardown
pytest -k "uc12345main" --setup-show -v
```

### Method 3: Create Minimal Test Files

Create a temporary test file for a single step:

**`tests/test_debug_single_step.py`:**
```python
from pathlib import Path
from pytest_bdd import scenarios

# Create a minimal feature file content
FEATURE_CONTENT = """
Feature: Debug Single Step
  Scenario: Test Background Step
    Given a CPE is online and fully provisioned
"""

# Write temporary feature file
debug_feature = Path(__file__).parent / "features" / "debug-single.feature"
debug_feature.write_text(FEATURE_CONTENT)

scenarios(str(debug_feature))
```

Run: `pytest tests/test_debug_single_step.py -v`

## Debugging Tips

### 1. Add Print Statements to Step Definitions

Edit step definitions to add debug output:

```python
@given("a CPE is online and fully provisioned")
def cpe_is_online_and_provisioned(acs, cpe, bf_context):
    print(f"DEBUG: Starting background step")
    print(f"DEBUG: acs={acs}, cpe={cpe}, bf_context={bf_context}")
    # ... rest of step
```

### 2. Use Python Debugger

Add breakpoints in step definitions:

```python
@given("a CPE is online and fully provisioned")
def cpe_is_online_and_provisioned(acs, cpe, bf_context):
    import pdb; pdb.set_trace()  # Breakpoint here
    # ... rest of step
```

Or use pytest's `--pdb` flag to drop into debugger on failures.

### 3. Check Fixture Availability

Verify fixtures are available:

```bash
# Show all available fixtures
pytest --fixtures | grep -E "(acs|cpe|bf_context|http_server)"

# Show fixture setup for a specific test
pytest -k "uc12345main" --setup-show -v
```

### 4. Test Fixtures Independently

Create a simple test to verify fixtures work:

```python
def test_fixtures(acs, cpe, bf_context, http_server):
    """Test that all required fixtures are available."""
    assert acs is not None
    assert cpe is not None
    assert bf_context is not None
    assert http_server is not None
    print("All fixtures available!")
```

### 5. Use Logging Instead of Print

Enable pytest logging:

```bash
# Show print statements
pytest -k "uc12345main" -s

# Show logging output
pytest -k "uc12345main" --log-cli-level=DEBUG
```

## Step-by-Step Workflow

### Recommended Approach:

1. **Start with Background Step**
   ```bash
   # Edit debug-step-by-step.feature to only have background step
   pytest -k "debug" -vv
   ```

2. **Add Steps One at a Time**
   - Uncomment next step in `debug-step-by-step.feature`
   - Run again: `pytest -k "debug" -vv`
   - Fix any issues before moving to next step

3. **Once All Steps Work Individually**
   - Test full scenario: `pytest -k "uc12345main" -vv`

### Example Session:

```bash
# Step 1: Test background only
pytest -k "debug" -vv
# ✓ Passes

# Step 2: Add firmware install step
# Edit debug-step-by-step.feature, uncomment firmware step
pytest -k "debug" -vv
# ✓ Passes

# Step 3: Add credentials step
# Edit debug-step-by-step.feature, uncomment credentials step
pytest -k "debug" -vv
# ✗ Fails - fix the step definition
# ... fix code ...
pytest -k "debug" -vv
# ✓ Passes

# Continue until all steps work...
```

## Common Issues

### Missing Fixtures

**Error:** `TypeError: cpe_is_online_and_provisioned() missing 3 required positional arguments`

**Solution:** Ensure fixtures are properly defined in `conftest.py` or pytest plugins.

### Step Not Found

**Error:** `StepDefinitionNotFoundError`

**Solution:** 
- Check step definition exists in `tests/step_defs/`
- Verify `conftest.py` auto-discovery is working
- Check step text matches exactly (case-sensitive)

### Fixture Scope Issues

**Error:** Fixture values not persisting between steps

**Solution:** Use `bf_context` fixture to store state between steps.

## Useful pytest Flags Summary

| Flag | Description |
|------|-------------|
| `-v` / `-vv` | Verbose output (more `v`s = more detail) |
| `-s` | Show print statements |
| `-x` | Stop at first failure |
| `--pdb` | Drop into debugger on failure |
| `--stepwise` | Continue from last failure |
| `--tb=short` | Shorter traceback format |
| `--tb=long` | Longer traceback format |
| `--setup-show` | Show fixture setup/teardown |
| `-k "keyword"` | Filter tests by keyword |
| `--collect-only` | Show what tests would run (dry run) |

## Next Steps

Once individual steps work, test the full scenario:

```bash
pytest -k "uc12345main" -vv
```

