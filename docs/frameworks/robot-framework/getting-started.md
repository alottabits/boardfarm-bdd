# Robot Framework Getting Started

This guide covers how to set up and run Robot Framework tests with boardfarm integration.

## Installation

Install the Robot Framework dependencies using the optional dependency group:

```bash
# From project root
pip install -e ".[robot]"
```

This installs:

- `robotframework` - Robot Framework test automation
- `robotframework-boardfarm` - Boardfarm integration library (includes `bfrobot` CLI)

## Project Structure

```
boardfarm-bdd/
├── robot/
│   ├── tests/                    # Robot test suites
│   │   ├── __init__.robot        # Suite initialization
│   │   ├── hello.robot           # Smoke tests
│   │   ├── remote_cpe_reboot.robot
│   │   ├── user_makes_one_way_call.robot
│   │   ├── acs_gui_device_management.robot
│   │   └── device_class_initialization.robot
│   ├── libraries/                # Python keyword libraries
│   │   ├── acs_keywords.py       # ACS operation keywords
│   │   ├── cpe_keywords.py       # CPE operation keywords
│   │   ├── voice_keywords.py     # Voice/SIP keywords
│   │   └── ...                   # Other keyword libraries
│   ├── resources/                # Shared resource files
│   │   ├── common.resource       # Common keywords
│   │   ├── variables.resource    # Shared variables
│   │   ├── cleanup.resource      # Cleanup keywords
│   │   └── voice.resource        # Voice test keywords
│   └── robot.yaml                # Configuration
└── requirements/                 # Use case specifications
```

## Running Tests

### Using the `bfrobot` Command (Recommended)

The `bfrobot` command provides a consistent CLI experience that matches `boardfarm` and `pytest`:

```bash
# Run all tests
bfrobot --board-name prplos-docker-1 \
        --env-config bf_config/boardfarm_env_example.json \
        --inventory-config bf_config/boardfarm_config_example.json \
        --outputdir results \
        robot/tests/

# Run a specific test file
bfrobot --board-name prplos-docker-1 \
        --env-config bf_config/boardfarm_env_example.json \
        --inventory-config bf_config/boardfarm_config_example.json \
        robot/tests/hello.robot

# Run with skip-boot for faster iteration
bfrobot --board-name prplos-docker-1 \
        --env-config bf_config/boardfarm_env_example.json \
        --inventory-config bf_config/boardfarm_config_example.json \
        --skip-boot \
        robot/tests/hello.robot
```

### Consistent CLI Across Tools

All three tools use the same command-line format:

```bash
# Boardfarm interactive shell
boardfarm --board-name prplos-docker-1 \
          --env-config bf_config/boardfarm_env_example.json \
          --inventory-config bf_config/boardfarm_config_example.json

# pytest with boardfarm
pytest --board-name prplos-docker-1 \
       --env-config bf_config/boardfarm_env_example.json \
       --inventory-config bf_config/boardfarm_config_example.json \
       tests/

# Robot Framework with boardfarm
bfrobot --board-name prplos-docker-1 \
        --env-config bf_config/boardfarm_env_example.json \
        --inventory-config bf_config/boardfarm_config_example.json \
        robot/tests/
```

### Running Specific Tests

```bash
# Run tests by tag
bfrobot --board-name prplos-docker-1 \
        --env-config bf_config/boardfarm_env_example.json \
        --inventory-config bf_config/boardfarm_config_example.json \
        --include smoke \
        robot/tests/

# Run tests by name pattern
bfrobot --board-name prplos-docker-1 \
        --env-config bf_config/boardfarm_env_example.json \
        --inventory-config bf_config/boardfarm_config_example.json \
        --test "*Reboot*" \
        robot/tests/

# Exclude certain tests
bfrobot --board-name prplos-docker-1 \
        --env-config bf_config/boardfarm_env_example.json \
        --inventory-config bf_config/boardfarm_config_example.json \
        --exclude slow \
        robot/tests/
```

### Command Line Options

| Option                      | Description                       | Required |
| --------------------------- | --------------------------------- | -------- |
| `--board-name`              | Board configuration name          | Yes      |
| `--env-config`              | Environment config JSON file      | Yes      |
| `--inventory-config`        | Inventory config JSON file        | Yes      |
| `--skip-boot`               | Skip device booting               | No       |
| `--skip-contingency-checks` | Skip contingency checks           | No       |
| `--save-console-logs`       | Path to save console logs         | No       |
| `--legacy`                  | Enable legacy device access       | No       |
| `--ignore-devices`          | Comma-separated devices to ignore | No       |

All standard Robot Framework options are also supported (`--outputdir`, `--include`, `--exclude`, `--test`, `--log`, `--report`, etc.).

### Alternative: Direct Listener Usage

For advanced use cases, you can use the listener directly with the `robot` command:

```bash
robot --outputdir results \
    --listener "robotframework_boardfarm.BoardfarmListener:\
board_name=prplos-docker-1:\
env_config=bf_config/boardfarm_env_example.json:\
inventory_config=bf_config/boardfarm_config_example.json" \
    robot/tests/
```

## Writing Tests

### Basic Test Structure

```robot
*** Settings ***
Documentation    Description of this test suite
Library    robotframework_boardfarm.BoardfarmLibrary
Library    ../libraries/acs_keywords.py
Library    ../libraries/cpe_keywords.py
Resource   ../resources/common.resource

*** Test Cases ***
UC-12347: Remote CPE Reboot
    [Documentation]    Remote reboot of CPE via ACS
    [Tags]    smoke    reboot

    # Get devices dynamically
    ${acs}=    Get Device By Type    ACS
    ${cpe}=    Get Device By Type    CPE

    # Given - use scenario-aligned keywords
    A CPE Is Online And Fully Provisioned    ${acs}    ${cpe}

    # When
    The Operator Initiates A Reboot Task On The ACS For The CPE    ${acs}    ${cpe}

    # Then
    The CPE Should Have Rebooted    ${cpe}
```

### Device Availability Checking

Tests should verify required devices are available before proceeding:

```robot
*** Test Cases ***
UC-12348: Voice Call Test
    [Documentation]    Requires 2 SIP phones
    [Tags]    voice    requires-2-phones
    
    # Check device availability FIRST
    ${phones}=    Get Devices By Type    SIPPhone
    ${phone_count}=    Get Length    ${phones}
    Skip If    ${phone_count} < 2
    ...    Test requires 2 SIP phones, testbed has ${phone_count}
    
    # Get device properties FROM objects (not from variables)
    @{phone_list}=    Get Dictionary Values    ${phones}
    ${caller}=    Set Variable    ${phone_list}[0]
    ${callee}=    Set Variable    ${phone_list}[1]
    ${caller_number}=    Evaluate    $caller.number
    
    # Now proceed with test...
```

This pattern ensures:
- Tests are self-documenting about their requirements
- Robot Framework reports show exactly why tests were skipped
- Tests work on any testbed, gracefully skipping when needed

### Keyword Libraries

Robot Framework tests use Python keyword libraries that mirror the pytest-bdd step definitions:

| Library                  | Purpose              | Mirrors                               |
| ------------------------ | -------------------- | ------------------------------------- |
| `acs_keywords.py`        | ACS operations       | `tests/step_defs/acs_steps.py`        |
| `cpe_keywords.py`        | CPE operations       | `tests/step_defs/cpe_steps.py`        |
| `voice_keywords.py`      | Voice/SIP operations | `tests/step_defs/sip_phone_steps.py`  |
| `background_keywords.py` | Background setup     | `tests/step_defs/background_steps.py` |
| `operator_keywords.py`   | Operator actions     | `tests/step_defs/operator_steps.py`   |

**Example keyword library:**

```python
# robot/libraries/acs_keywords.py
import logging
from robot.api.deco import keyword
from boardfarm3.use_cases import acs as acs_use_cases

_LOGGER = logging.getLogger(__name__)


def _get_listener():
    from robotframework_boardfarm.listener import get_listener
    return get_listener()


class AcsKeywords:
    ROBOT_LIBRARY_SCOPE = "SUITE"

    @keyword("The CPE is online via ACS")
    def verify_cpe_online(self, acs, cpe):
        """Verify CPE connectivity via ACS (read-only, no cleanup needed)."""
        return acs_use_cases.is_cpe_online(acs, cpe)

    @keyword("Set ACS Parameter Value")
    def set_parameter(self, acs, cpe, parameter, value):
        """Set a TR-069 parameter and register automatic restore."""
        original = acs_use_cases.get_parameter_value(acs, cpe, parameter)
        acs_use_cases.set_parameter_value(acs, cpe, parameter, value)
        try:
            _get_listener().register_teardown(
                f"Restore {parameter}",
                self._restore_param, acs, cpe, parameter, original,
            )
        except Exception:
            _LOGGER.debug("Listener unavailable; skipping teardown registration")

    @staticmethod
    def _restore_param(acs, cpe, parameter, value):
        acs_use_cases.set_parameter_value(acs, cpe, parameter, value)
```

> **Note:** Read-only keywords (like `verify_cpe_online`) don't need `register_teardown`.
> Only state-changing keywords register cleanup.

### Using Resources

Import shared resources for common keywords and **true constants only**:

```robot
*** Settings ***
Resource    ../resources/common.resource
Resource    ../resources/variables.resource

*** Test Cases ***
Test With Resources
    # Uses keyword from common.resource
    Setup Testbed Connection

    # Uses CONSTANT from variables.resource (timeout, not device data)
    Log    Timeout: ${DEFAULT_TIMEOUT}
    
    # Device data comes FROM device objects, not from variables
    ${cpe}=    Get Device By Type    CPE
    ${cpe_id}=    Evaluate    $cpe.sw.cpe_id
```

**Important**: Resource files should only contain:
- Timeouts (e.g., `${DEFAULT_TIMEOUT}=30`)
- TR-069 parameter paths (standard paths)
- Test tags

Resource files should **NOT** contain:
- Phone numbers (use `phone.number`)
- IP addresses (use `device.ipv4_addr`)
- Credentials (use `device.username`, `device.password`)
- Any testbed-specific configuration

## Architecture

Tests follow the 4-layer architecture:

```
┌─────────────────────────────────────────────────────────┐
│  Robot Test Files (.robot)                              │
│  - Test cases with scenario-aligned keywords            │
│  - Check device availability, skip if not met           │
│  - Extract device data FROM objects                     │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  Python Keyword Libraries (robot/libraries/)            │
│  - @keyword decorator maps to scenario steps            │
│  - Mirrors tests/step_defs/ structure                   │
│  - Thin wrappers around boardfarm3.use_cases            │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  boardfarm3.use_cases                                   │
│  - Single source of truth for test logic                │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  Device Templates                                       │
│  - Low-level device operations                          │
│  - Provided by boardfarm                                │
└─────────────────────────────────────────────────────────┘
```

### Role of BoardfarmListener

The `BoardfarmListener` manages the full test lifecycle:

| Phase | Action |
|-------|--------|
| **Suite Start** | Deploys devices via Boardfarm hooks |
| **Test Start** | Creates empty teardown stack, sets library context |
| **Test End** | Drains teardown stack (LIFO), refreshes CPE console, clears context |
| **Suite End** | Releases devices |

The listener provides **automatic per-test cleanup** through a LIFO teardown stack. Keyword libraries call `register_teardown()` when they change state, and the listener reverses those changes when the test finishes (pass or fail). This mirrors the `yield`-based cleanup in pytest-bdd.

The listener does **NOT** filter or select tests. Tests are responsible for checking their own preconditions and skipping themselves if requirements aren't met.

See [Test Cleanup Architecture](../../architecture/test-cleanup-architecture.md) for full details.

## Keyword Naming Convention

Keywords use the `@keyword` decorator to map clean Python function names to scenario step text:

| Aspect | pytest-bdd | Robot Framework |
|--------|-----------|-----------------|
| Step binding | `@when("step text")` | `@keyword("step text")` |
| Step location | `tests/step_defs/acs_steps.py` | `robot/libraries/acs_keywords.py` |
| Use case layer | `boardfarm3.use_cases.acs` | `boardfarm3.use_cases.acs` (same) |
| Per-test cleanup | `yield` in step function | `register_teardown()` in keyword library |
| Cleanup execution | pytest fixture teardown (LIFO) | `BoardfarmListener.end_test()` (LIFO) |

**Example comparison:**

```python
# pytest-bdd step definition
@when("the ACS initiates a remote reboot of the CPE")
def initiate_reboot(acs: ACS, cpe: CPE) -> None:
    acs_use_cases.initiate_reboot(acs, cpe)
```

```python
# Robot Framework keyword library
@keyword("The ACS initiates a remote reboot of the CPE")
def initiate_reboot(self, acs, cpe):
    acs_use_cases.initiate_reboot(acs, cpe)
```

Both call the same `boardfarm3.use_cases.acs.initiate_reboot()` function.

## Low-Level Device Access

Since keyword libraries are Python code, you have full access to device objects when needed:

```python
@keyword("Get CPE load average")
def get_load_avg(self, cpe):
    """Direct device access when no use_case exists."""
    return cpe.sw.get_load_avg()
```

Use this for edge cases where no `boardfarm3.use_cases` function exists.

## Reporting

Robot Framework generates HTML reports automatically:

```bash
# Default output (log.html, report.html, output.xml)
bfrobot ... --outputdir results robot/tests/

# Custom report names
bfrobot ... --log mylog.html --report myreport.html robot/tests/
```

### Reprocessing Results

```bash
# Combine multiple outputs
rebot --output combined.xml results1/output.xml results2/output.xml

# Generate new report from output
rebot --log newlog.html output.xml
```

## Further Reading

- [Best Practices Guide](best-practices.md) - **Important lessons learned and pitfalls to avoid**
- [Keyword Reference](keyword-reference.md) - Complete keyword documentation
- [Keyword Libraries Documentation](../../robot/libraries/README.md)
- [Use Case Architecture](../../architecture/boardfarm-five-layer-model.md) - Architecture overview
- [robotframework-boardfarm Documentation](../../../robotframework-boardfarm/README.md)
