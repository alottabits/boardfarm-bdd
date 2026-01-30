# BDD Test Suite Structure

This directory contains the Behavior-Driven Development (BDD) test suite using `pytest-bdd` and `boardfarm`. The structure is designed to be modular, maintainable, and scalable.

**Note: this is work in progress. The test step definitions are placeholders and may well need to be updated**

## Directory Structure

```
tests/
├── features/                   # Gherkin feature files (.feature)
│   ├── Remote CPE Reboot.feature
│   └── hello.feature
├── step_defs/                  # Step definition modules (actor-based organization)
│   ├── __init__.py
│   ├── background_steps.py    # Background/setup steps
│   ├── acs_steps.py           # ACS (Auto Configuration Server) actor steps
│   ├── cpe_steps.py           # CPE (Customer Premises Equipment) actor steps
│   ├── operator_steps.py      # Operator actor steps
│   └── hello_steps.py         # Simple example step (for illustration)
├── test_artifacts/            # Test data files (firmware images, configs, etc.)
├── test_all_scenarios.py      # Main script to run all scenarios
└── test_hello.py              # Example test file
```

## How It Works

### 1. Feature Files (`features/`)

Feature files contain BDD scenarios written in Gherkin syntax. Each `.feature` file corresponds to a use case and contains:

- **Feature**: High-level description of the feature being tested
- **Background**: Steps that run before each scenario
- **Scenarios**: Individual test cases with `Given`, `When`, `Then` steps
- **Scenario Names**: Include use case IDs in scenario names for organization (e.g., `UC-12345-Main: Successful Firmware Upgrade`)

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

Step definitions are organized into modules by **actor** - the entity performing the action. Each module contains Python functions decorated with `@given`, `@when`, or `@then` that implement the steps from feature files.

**Actor-Based Organization:**

- **`acs_steps.py`**: Steps where the ACS (Auto Configuration Server) is the actor performing actions
  - Examples: ACS sends connection request, ACS issues Reboot RPC, ACS queues tasks
- **`cpe_steps.py`**: Steps where the CPE (Customer Premises Equipment) is the actor performing actions
  - Examples: CPE sends Inform message, CPE executes reboot, CPE resumes normal operation
- **`operator_steps.py`**: Steps where the operator is the actor performing actions
  - Examples: Operator initiates reboot task, use case success verification
- **`background_steps.py`**: Background/setup steps that establish preconditions
  - Examples: CPE is online and provisioned, user sets GUI password
- **`hello_steps.py`**: Simple example step for illustration purposes

**Using Boardfarm Use Cases:**

Step definitions should be thin wrappers around `boardfarm3.use_cases` functions, which provide the single source of truth for test operations:

- `boardfarm3.use_cases.acs` - ACS/TR-069 operations
- `boardfarm3.use_cases.cpe` - CPE device operations
- `boardfarm3.use_cases.voice` - SIP/Voice operations
- `boardfarm3.use_cases.networking` - Network operations

Example step definition:

```python
from pytest_bdd import given, when, then
from boardfarm3.use_cases import acs as acs_use_cases
from boardfarm3.use_cases import cpe as cpe_use_cases
from boardfarm3.templates.acs import ACS
from boardfarm3.templates.cpe import CPE

@when("the ACS initiates a remote reboot of the CPE")
def acs_initiates_reboot(acs: ACS, cpe: CPE) -> None:
    """Initiate CPE reboot via ACS."""
    acs_use_cases.initiate_reboot(acs, cpe)

@then("the CPE uptime should be less than before the reboot")
def verify_uptime_reset(cpe: CPE, bf_context) -> None:
    """Verify CPE rebooted by checking uptime."""
    current_uptime = cpe_use_cases.get_seconds_uptime(cpe)
    assert current_uptime < bf_context.initial_uptime
```

### 3. Root `conftest.py` - Auto-Discovery System

Located at the project root (`boardfarm-bdd/conftest.py`), this file uses **AST-based auto-discovery** to automatically find and register all step definitions.

**Key Features:**

- **Automatic Module Import**: Auto-discovers and imports all `*_steps.py` files in `tests/step_defs/`
- **AST Parsing**: Uses Abstract Syntax Tree parsing to find `@given`, `@when`, and `@then` decorators
- **Dynamic Registration**: Automatically re-registers all step definitions so pytest-bdd can discover them
- **Zero Maintenance**: No manual imports needed - just add new `*_steps.py` files and they're automatically discovered!

**How It Works:**

1. Auto-imports all `*_steps.py` files in `tests/step_defs/`
2. Scans imported modules using AST to extract step decorator information
3. Gets function objects from the imported modules
4. Dynamically re-registers all step definitions at module level using `exec()`

**Important Notes:**

- **pytest-bdd 8.1.0 Limitation**: Due to how pytest-bdd 8.1.0 works, step definitions imported from modules are not automatically discoverable at runtime. The auto-discovery system works around this by re-registering steps directly in `conftest.py`.
- **No Manual Imports Required**: Test files do NOT need to import step definitions - `conftest.py` handles everything automatically.
- **Scalable**: Adding new step definition files automatically registers them - no code changes needed!

### 4. Test Execution Files

**`test_all_scenarios.py`**:

- Discovers all `.feature` files in the `features/` directory
- Loads scenarios using pytest-bdd's `scenarios()` function
- Creates individual pytest test functions for each scenario
- **No step definition imports needed** - handled by `conftest.py`
- Uses underscore naming (`test_*.py`) to match pytest's auto-discovery pattern

**`test_hello.py`**:

- Example test file showing how to run a single feature file
- Demonstrates the minimal setup needed

## Running Tests

### Run All Scenarios

```bash
# From project root - discovers all test files automatically
pytest

# Or specify the test file explicitly
pytest tests/test_all_scenarios.py
```

### Run with Verbose Output

```bash
pytest -v
# or
pytest tests/test_all_scenarios.py -v
```

### Run Specific Scenarios by Name

```bash
# Run scenarios matching UC-12345 (all scenarios with this prefix)
# Note: pytest-bdd converts scenario names to lowercase and removes hyphens
# You can run from project root without specifying test files:
pytest -k "uc12345"

# Run the main scenario specifically
pytest -k "uc12345main"
# or match by descriptive name
pytest -k "successful_firmware"

# Run a specific scenario by use case ID (hyphens removed in test names)
pytest -k "uc123456a"  # UC-12345-6.a
pytest -k "uc123458a"  # UC-12345-8.a
```

### Run a Single Feature File

```bash
pytest tests/test_hello.py
# or use keyword matching
pytest -k "say_hello"
```

### Run with Shorter Traceback

```bash
pytest --tb=short
# or
pytest tests/test_all_scenarios.py --tb=short
```

## Adding New Step Definitions

### 1. Identify the Appropriate Module

Choose the module based on **which actor is performing the action**:

- ACS performs action → `acs_steps.py`
- CPE performs action → `cpe_steps.py`
- Operator performs action → `operator_steps.py`
- Background/setup step → `background_steps.py`

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

### 3. Use Boardfarm Use Cases

Import and use functions from `boardfarm3.use_cases`:

```python
from boardfarm3.use_cases import acs as acs_use_cases
from boardfarm3.use_cases import cpe as cpe_use_cases

# In your step definition
uptime = cpe_use_cases.get_seconds_uptime(cpe)
is_online = acs_use_cases.is_cpe_online(acs, cpe)
```

### 4. Create a New Actor Module (if needed)

If you need a new actor category:

1. Create a new file in `step_defs/` following the naming pattern `<actor>_steps.py` (e.g., `wan_steps.py`, `http_server_steps.py`)
2. **That's it!** The auto-discovery system in `conftest.py` will automatically import and register it.
3. No manual imports or configuration needed in `conftest.py` - it's completely automatic!

## Best Practices

### Step Definition Organization

1. **Organize by Actor**: Group steps by which actor performs the action (ACS, CPE, Operator, etc.)
2. **Use Descriptive Names**: Function names should clearly describe what the step does
3. **Add Docstrings**: Every step definition should have a docstring explaining its purpose
4. **Reuse Steps**: Check existing step definitions before creating new ones
5. **Type Hints**: Always use type hints for all function parameters
6. **Actor Clarity**: Step text should make it clear which actor is performing the action

### Feature File Guidelines

1. **One Feature File per Use Case**: Each `.feature` file should correspond to one use case
2. **Name Scenarios Consistently**: Include use case IDs in scenario names for easy filtering (e.g., `UC-12345-Main: Successful Firmware Upgrade`)
   - pytest-bdd converts scenario names to test function names by: removing hyphens/special chars, lowercasing, replacing spaces with underscores
   - Example: `UC-12345-Main: Successful Firmware Upgrade` → `test_uc12345main_successful_firmware_upgrade`
   - Filter using: `pytest -k "uc12345main"` or `pytest -k "successful_firmware"`
3. **Verify Guarantees**: Each scenario should verify Success Guarantees (success paths) or Minimal Guarantees (failure paths)
4. **Clear Step Names**: Use clear, business-readable step names
5. **No Tags Needed**: Use consistent naming patterns instead of `@` tags to avoid marker registration and warnings

### Using Boardfarm Use Cases

1. **Single Source of Truth**: Use `boardfarm3.use_cases` for all test operations
2. **Thin Wrappers**: Step definitions should have minimal logic - delegate to use_cases
3. **Portability**: Using use_cases ensures tests work with both pytest-bdd and Robot Framework

## Workflow: Adding a New Test

1. **Write Use Case**: Create use case document in `requirements/`
2. **Create Feature File**: Add `.feature` file in `features/` with scenarios
3. **Implement Steps**: Add step definitions to appropriate modules in `step_defs/`
4. **Add Test Artifacts**: Place required files in `test_artifacts/` if needed
5. **Run Tests**: Execute tests using `pytest` or `pytest tests/test_all_scenarios.py`

**Note**: No need to update `conftest.py` or test files - the auto-discovery system handles everything!

## Troubleshooting

### Step Definition Not Found

- **Check Step Text Match**: Ensure the step text in the feature file exactly matches the decorator pattern (including quotes, case, and whitespace)
- **Verify File Location**: Ensure the step definition file is in the `step_defs/` directory
- **Check File Naming**: Step definition files should follow the pattern `*_steps.py`
- **Run Discovery**: Check the pytest output - `conftest.py` prints which steps it discovers and registers

### CPE Initialization Issues

#### eth1 Connectivity Failures After Reinitialization

**Symptom**: After changing GUI credentials in a test, eth1 fails to connect when Boardfarm tries to reinitialize the environment.

**Root Cause**: When GUI credentials are changed via TR-069 (`Device.Users.User.1.Username` and `Device.Users.User.1.Password`), PrplOS creates a config backup (`/tmp/sysupgrade.tgz`). If an upgrade was attempted, this backup is preserved to `/boot/sysupgrade.tgz`. On reinitialization without an upgrade, if this backup exists, PrplOS will restore it during boot, which can interfere with Boardfarm's initialization process.

**Solution**: The init wrapper script (`container-init.sh`) automatically removes leftover `/boot/sysupgrade.tgz` during normal boot (when no upgrade flag exists). This ensures a clean state for Boardfarm initialization.

**Note**: GUI credentials are **not** used for Boardfarm initialization - the CPE connects via `docker exec` (local_cmd), not SSH. The issue is caused by config restoration interfering with network initialization, not by credential authentication.

**Verification**: Check if `/boot/sysupgrade.tgz` exists in the container:

```bash
docker exec cpe ls -la /boot/sysupgrade.tgz
```

If it exists during normal boot (no upgrade), it should be automatically removed by the init wrapper script. If eth1 connectivity issues persist, check container logs for config restoration messages.

### Import Errors

- Use absolute imports for use_cases: `from boardfarm3.use_cases import acs as acs_use_cases`
- Ensure `__init__.py` exists in `step_defs/` directory
- Check that boardfarm3 is properly installed in your environment

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

### Using Naming Patterns Instead of Tags

**Issue**: Using `@` tags in feature files requires registering markers in `pytest.ini` to avoid warnings. With many use cases, this becomes tedious to maintain.

**Solution**: Use consistent naming patterns in scenario names (e.g., `UC-12345-Main: Successful Firmware Upgrade`) instead of tags. Filter scenarios using pytest's `-k` option with keyword matching.

**Key Points**:

- Scenario names are converted to test function names: hyphens/special chars removed, lowercased, spaces become underscores
- Example: `UC-12345-Main: Successful Firmware Upgrade` → `test_uc12345main_successful_firmware_upgrade`
- Filter using: `pytest -k "uc12345main"` or `pytest -k "successful_firmware"`
- No marker registration needed - eliminates warnings and maintenance overhead
- Still provides organization and filtering capabilities through consistent naming

## Running Tests with Boardfarm Testbed

For detailed test execution instructions including filtering, logging, and reporting options, see the [Getting Started Guide](../docs/tests/getting_started.md).

### Quick Start

```bash
# Run all tests
pytest --board-name prplos-docker-1 \
    --env-config bf_config/boardfarm_env_example.json \
    --inventory-config bf_config/boardfarm_config_example.json \
    --legacy \
    --save-console-logs ./logs/

# Run specific scenario by name
pytest -k "UC12347Main" \
    --board-name prplos-docker-1 \
    --env-config bf_config/boardfarm_env_example.json \
    --inventory-config bf_config/boardfarm_config_example.json \
    --legacy -v -s
```

## Related Documentation

- [Project README](../README.md) - Overall project documentation
- [Getting Started Guide](../docs/tests/getting_started.md) - Detailed guide with examples
- [Use Case Template](../docs/Use%20Case%20Template%20(reflect%20the%20goal).md) - Use case structure
- [Use Case Architecture](../docs/use_case_architecture.md) - Architecture overview
- [pytest-bdd Documentation](https://pytest-bdd.readthedocs.io/) - pytest-bdd framework docs
