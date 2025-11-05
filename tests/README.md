# BDD Test Suite Structure

This directory contains the Behavior-Driven Development (BDD) test suite using `pytest-bdd` and `boardfarm`. The structure is designed to be modular, maintainable, and scalable.

**Note: this is still very much work in progress. The test step definitions are placehoders and need to be updated**

## Directory Structure

```
tests/
├── execution/                  # Test execution scripts
│   └── test-all-scenarios.py  # Main script to run all scenarios
├── features/                   # Gherkin feature files (.feature)
│   └── CPE Firmware Upgrade.feature
├── step_defs/                  # Step definition modules (modular organization)
│   ├── __init__.py
│   ├── helpers.py             # Shared helper functions
│   ├── background_steps.py    # Background/initialization steps
│   ├── firmware_steps.py      # Firmware-related steps
│   ├── acs_steps.py           # ACS interaction steps
│   ├── cpe_config_steps.py    # CPE configuration steps
│   ├── provisioning_steps.py  # Provisioning and connectivity steps
│   └── verification_steps.py  # Verification and assertion steps
└── test_artifacts/            # Test data files (firmware images, configs, etc.)
```

## How It Works

### 1. Feature Files (`features/`)

Feature files contain BDD scenarios written in Gherkin syntax. Each `.feature` file corresponds to a use case and contains:
- **Feature**: High-level description of the feature being tested
- **Background**: Steps that run before each scenario
- **Scenarios**: Individual test cases with `Given`, `When`, `Then` steps
- **Tags**: Links scenarios to use case sections (e.g., `@UC-12345-Main`)

Example:
```gherkin
Feature: CPE Firmware Upgrade
  Background:
    Given a CPE is online and fully provisioned

  @UC-12345-Main
  Scenario: Successful Firmware Upgrade
    Given the operator installs a new signed firmware file "prplos_upgrade.img" on the image server
    When the CPE performs its periodic TR-069 check-in
    Then the CPE installs the firmware and reboots
```

### 2. Step Definitions (`step_defs/`)

Step definitions are organized into modules by domain/functionality. Each module contains Python functions decorated with `@given`, `@when`, or `@then` that implement the steps from feature files.

**Modular Organization:**
- **`background_steps.py`**: Steps that run in the Background section
- **`firmware_steps.py`**: Steps related to firmware installation and management
- **`acs_steps.py`**: Steps for ACS (Auto Configuration Server) interactions
- **`cpe_config_steps.py`**: Steps for configuring CPE settings (credentials, SSID, etc.)
- **`provisioning_steps.py`**: Steps for provisioning and network connectivity
- **`verification_steps.py`**: Steps that verify outcomes and assert results

**Shared Helpers (`helpers.py`):**
- Contains utility functions used across multiple step definitions
- Functions like `gpv_value()`, `get_console_uptime_seconds()`, `install_file_on_tftp()`
- Import from `tests.step_defs.helpers` in step definition modules

Example step definition:
```python
from pytest_bdd import given, parsers
from tests.step_defs.helpers import install_file_on_tftp

@given(parsers.parse('the operator installs a new signed firmware file "{filename}" on the image server'))
def operator_installs_firmware(tftp_server: WanTemplate, filename: str) -> None:
    """Copy a signed firmware file from the local test suite to the TFTP server."""
    install_file_on_tftp(tftp_server, filename)
```

### 3. Root `conftest.py`

Located at the project root (`boardfarm-bdd/conftest.py`), this file:
- Defines pytest fixtures (`CPE`, `ACS`, `WAN`) for device access
- Imports all step definition modules so pytest-bdd can discover them
- Re-exports helper functions for backward compatibility

**Important**: All step definition modules must be imported in `conftest.py` for pytest-bdd to discover them:
```python
from tests.step_defs import (  # noqa: F401
    acs_steps,
    background_steps,
    cpe_config_steps,
    firmware_steps,
    provisioning_steps,
    verification_steps,
)
```

### 4. Test Execution (`execution/`)

The `test-all-scenarios.py` script:
- Discovers all `.feature` files in the `features/` directory
- Loads scenarios using pytest-bdd's `scenarios()` function
- Creates individual pytest test functions for each scenario

## Running Tests

### Run All Scenarios
```bash
pytest tests/execution/test-all-scenarios.py
```

### Run with Verbose Output
```bash
pytest tests/execution/test-all-scenarios.py -v
```

### Run Specific Scenarios by Tag
```bash
# Run scenarios tagged with UC-12345
pytest tests/execution/test-all-scenarios.py -k "UC-12345"

# Run a specific scenario
pytest tests/execution/test-all-scenarios.py -k "@UC-12345-Main"
```

### Run with Shorter Traceback
```bash
pytest tests/execution/test-all-scenarios.py --tb=short
```

## Adding New Step Definitions

### 1. Identify the Appropriate Module

Choose the module that best fits the step's domain:
- Configuration → `cpe_config_steps.py`
- Firmware operations → `firmware_steps.py`
- ACS interactions → `acs_steps.py`
- Verification → `verification_steps.py`
- Provisioning → `provisioning_steps.py`

### 2. Add the Step Definition

Create a function decorated with `@given`, `@when`, or `@then`:

```python
from pytest_bdd import given, parsers
from boardfarm3.templates.cpe.cpe import CPE as CpeTemplate

@given(parsers.parse('the CPE has firmware version "{version}"'))
def cpe_has_firmware_version(cpe: CpeTemplate, version: str) -> None:
    """Verify the CPE is running the specified firmware version."""
    # Implementation here
    pass
```

### 3. Use Shared Helpers

Import helper functions from `helpers.py` when needed:
```python
from tests.step_defs.helpers import gpv_value, get_console_uptime_seconds
```

### 4. Create a New Module (if needed)

If you need a new domain category:
1. Create a new file in `step_defs/` (e.g., `network_steps.py`)
2. Add the import to `conftest.py`:
   ```python
   from tests.step_defs import network_steps  # noqa: F401
   ```

## Best Practices

### Step Definition Organization

1. **Group Related Steps**: Keep steps that work together in the same module
2. **Use Descriptive Names**: Function names should clearly describe what the step does
3. **Add Docstrings**: Every step definition should have a docstring explaining its purpose
4. **Reuse Steps**: Check existing step definitions before creating new ones
5. **Type Hints**: Always use type hints for all function parameters

### Feature File Guidelines

1. **One Feature File per Use Case**: Each `.feature` file should correspond to one use case
2. **Tag Scenarios**: Use tags to link scenarios to use case sections (e.g., `@UC-12345-Main`)
3. **Verify Guarantees**: Each scenario should verify Success Guarantees (success paths) or Minimal Guarantees (failure paths)
4. **Clear Step Names**: Use clear, business-readable step names

### Shared Helpers

1. **Common Utilities**: Place functions used by multiple step definitions in `helpers.py`
2. **No Side Effects**: Helper functions should be pure functions when possible
3. **Clear Names**: Use descriptive function names without underscores (e.g., `gpv_value` not `_gpv_value`)

## Workflow: Adding a New Test

1. **Write Use Case**: Create use case document in `requirements/`
2. **Create Feature File**: Add `.feature` file in `features/` with scenarios
3. **Implement Steps**: Add step definitions to appropriate modules in `step_defs/`
4. **Add Test Artifacts**: Place required files in `test_artifacts/` if needed
5. **Run Tests**: Execute tests using `pytest tests/execution/test-all-scenarios.py`

## Troubleshooting

### Step Definition Not Found

- Ensure the step definition module is imported in `conftest.py`
- Check that the step text in the feature file exactly matches the decorator pattern
- Verify the step definition file is in the `step_defs/` directory

### Import Errors

- Use absolute imports: `from tests.step_defs.helpers import ...`
- Ensure `__init__.py` exists in `step_defs/` directory
- Check that helper functions are imported correctly

### Feature File Not Discovered

- Verify the feature file has a `.feature` extension
- Check that the file is in the `features/` directory
- Ensure `test-all-scenarios.py` is finding the correct path

## Related Documentation

- [Project README](../README.md) - Overall project documentation
- [Use Case Template](../docs/Use%20Case%20Template%20(reflect%20the%20goal).md) - Use case structure
- [pytest-bdd Documentation](https://pytest-bdd.readthedocs.io/) - pytest-bdd framework docs

