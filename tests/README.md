# BDD Test Suite Structure

This directory contains the Behavior-Driven Development (BDD) test suite using `pytest-bdd` and `boardfarm`. The structure is designed to be modular, maintainable, and scalable.

**Note: this is still very much work in progress. The test step definitions are placeholders and need to be updated**

## Directory Structure

```
tests/
├── features/                   # Gherkin feature files (.feature)
│   ├── CPE Firmware Upgrade.feature
│   └── hello.feature
├── step_defs/                  # Step definition modules (modular organization)
│   ├── __init__.py
│   ├── helpers.py             # Shared helper functions
│   ├── background_steps.py    # Background/initialization steps
│   ├── firmware_steps.py      # Firmware-related steps
│   ├── acs_steps.py           # ACS interaction steps
│   ├── cpe_config_steps.py    # CPE configuration steps
│   ├── provisioning_steps.py  # Provisioning and connectivity steps
│   ├── verification_steps.py  # Verification and assertion steps
│   └── hello_steps.py         # Example hello world steps
├── test_artifacts/            # Test data files (firmware images, configs, etc.)
├── test-all-scenarios.py      # Main script to run all scenarios
├── test-main-upgrade-scenario.py  # Run main upgrade scenario only
└── test_hello.py              # Example test file
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
- **`hello_steps.py`**: Example hello world steps for testing

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

### 3. Root `conftest.py` - Auto-Discovery System

Located at the project root (`boardfarm-bdd/conftest.py`), this file uses **AST-based auto-discovery** to automatically find and register all step definitions.

**Key Features:**
- **Automatic Discovery**: Scans `tests/step_defs/` for all Python modules
- **AST Parsing**: Uses Abstract Syntax Tree parsing to find `@given`, `@when`, and `@then` decorators
- **Dynamic Registration**: Automatically re-registers all step definitions so pytest-bdd can discover them
- **Zero Maintenance**: No manual imports needed - just add new step definition files!

**How It Works:**
1. Scans `tests/step_defs/` directory for all `.py` files (excluding `__init__.py` and `helpers.py`)
2. Parses each file using AST to extract step decorator information
3. Imports the modules to get function objects
4. Dynamically re-registers all step definitions at module level using `exec()`

**Important Notes:**
- **pytest-bdd 8.1.0 Limitation**: Due to how pytest-bdd 8.1.0 works, step definitions imported from modules are not automatically discoverable at runtime. The auto-discovery system works around this by re-registering steps directly in `conftest.py`.
- **No Manual Imports Required**: Test files do NOT need to import step definitions - `conftest.py` handles everything automatically.
- **Scalable**: Adding new step definition files automatically registers them - no code changes needed!

### 4. Test Execution Files

**`test-all-scenarios.py`**:
- Discovers all `.feature` files in the `features/` directory
- Loads scenarios using pytest-bdd's `scenarios()` function
- Creates individual pytest test functions for each scenario
- **No step definition imports needed** - handled by `conftest.py`

**`test-main-upgrade-scenario.py`**:
- Runs only the main firmware upgrade scenario
- Useful for focused testing during development

**`test_hello.py`**:
- Example test file showing how to run a single feature file
- Demonstrates the minimal setup needed

## Running Tests

### Run All Scenarios
```bash
pytest tests/test-all-scenarios.py
```

### Run with Verbose Output
```bash
pytest tests/test-all-scenarios.py -v
```

### Run Specific Scenarios by Tag
```bash
# Run scenarios tagged with UC-12345
pytest tests/test-all-scenarios.py -k "UC-12345"

# Run a specific scenario
pytest tests/test-all-scenarios.py -k "@UC-12345-Main"
```

### Run a Single Feature File
```bash
pytest tests/test_hello.py
```

### Run with Shorter Traceback
```bash
pytest tests/test-all-scenarios.py --tb=short
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
2. **That's it!** The auto-discovery system in `conftest.py` will automatically find and register it.
3. No manual imports or configuration needed.

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
5. **Run Tests**: Execute tests using `pytest tests/test-all-scenarios.py`

**Note**: No need to update `conftest.py` or test files - the auto-discovery system handles everything!

## Troubleshooting

### Step Definition Not Found

- **Check Step Text Match**: Ensure the step text in the feature file exactly matches the decorator pattern (including quotes, case, and whitespace)
- **Verify File Location**: Ensure the step definition file is in the `step_defs/` directory
- **Check File Naming**: Step definition files should be `.py` files (not `__init__.py` or `helpers.py`)
- **Run Discovery**: Check the pytest output - `conftest.py` prints which steps it discovers and registers

### Import Errors

- Use absolute imports: `from tests.step_defs.helpers import ...`
- Ensure `__init__.py` exists in `step_defs/` directory
- Check that helper functions are imported correctly

### Feature File Not Discovered

- Verify the feature file has a `.feature` extension
- Check that the file is in the `features/` directory
- Ensure test files are finding the correct path

### Auto-Discovery Issues

- Check that `conftest.py` is at the project root (not in `tests/`)
- Verify step definition files follow the naming convention (`*_steps.py`)
- Check pytest output for discovery messages - it should show registered steps
- Ensure step decorators use the correct syntax: `@given("step name")` or `@given(parsers.parse("..."))`

## Lessons Learned

### pytest-bdd 8.1.0 Step Discovery Limitation

**Issue**: pytest-bdd 8.1.0 does not automatically discover step definitions that are imported from modules. Even if modules are imported in `conftest.py`, pytest-bdd cannot find them at runtime.

**Solution**: The auto-discovery system in `conftest.py` uses AST parsing to find all step definitions and dynamically re-registers them at module level. This ensures pytest-bdd can discover them properly.

**Key Points**:
- Step definitions must be registered in `conftest.py` for pytest-bdd to find them
- Simply importing modules is not sufficient
- The auto-discovery system handles this automatically - no manual work needed

### Benefits of Auto-Discovery

1. **Zero Maintenance**: Add new step definition files without touching `conftest.py` or test files
2. **Single Source of Truth**: Step definitions live only in `step_defs/` modules
3. **Scalable**: Works with any number of step definition files
4. **Self-Documenting**: Discovery output shows what steps are registered

## Related Documentation

- [Project README](../README.md) - Overall project documentation
- [Use Case Template](../docs/Use%20Case%20Template%20(reflect%20the%20goal).md) - Use case structure
- [pytest-bdd Documentation](https://pytest-bdd.readthedocs.io/) - pytest-bdd framework docs
