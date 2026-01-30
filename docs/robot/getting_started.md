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

| Option | Description | Required |
|--------|-------------|----------|
| `--board-name` | Board configuration name | Yes |
| `--env-config` | Environment config JSON file | Yes |
| `--inventory-config` | Inventory config JSON file | Yes |
| `--skip-boot` | Skip device booting | No |
| `--skip-contingency-checks` | Skip contingency checks | No |
| `--save-console-logs` | Path to save console logs | No |
| `--legacy` | Enable legacy device access | No |
| `--ignore-devices` | Comma-separated devices to ignore | No |

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

    # Get devices
    ${acs}=    Get Device By Type    ACS
    ${cpe}=    Get Device By Type    CPE

    # Given - use scenario-aligned keywords
    A CPE Is Online And Fully Provisioned    ${acs}    ${cpe}
    
    # When
    The Operator Initiates A Reboot Task On The ACS For The CPE    ${acs}    ${cpe}
    
    # Then
    The CPE Should Have Rebooted    ${cpe}
```

### Keyword Libraries

Robot Framework tests use Python keyword libraries that mirror the pytest-bdd step definitions:

| Library | Purpose | Mirrors |
|---------|---------|---------|
| `acs_keywords.py` | ACS operations | `tests/step_defs/acs_steps.py` |
| `cpe_keywords.py` | CPE operations | `tests/step_defs/cpe_steps.py` |
| `voice_keywords.py` | Voice/SIP operations | `tests/step_defs/sip_phone_steps.py` |
| `background_keywords.py` | Background setup | `tests/step_defs/background_steps.py` |
| `operator_keywords.py` | Operator actions | `tests/step_defs/operator_steps.py` |

**Example keyword library:**

```python
# robot/libraries/acs_keywords.py
from robot.api.deco import keyword
from boardfarm3.use_cases import acs as acs_use_cases

class AcsKeywords:
    ROBOT_LIBRARY_SCOPE = "SUITE"

    @keyword("The CPE is online via ACS")
    def verify_cpe_online(self, acs, cpe):
        """Verify CPE connectivity via ACS."""
        return acs_use_cases.is_cpe_online(acs, cpe)

    @keyword("The ACS initiates a remote reboot of the CPE")
    def initiate_reboot(self, acs, cpe):
        """Initiate CPE reboot via ACS."""
        acs_use_cases.initiate_reboot(acs, cpe)
```

### Using Resources

Import shared resources for common keywords:

```robot
*** Settings ***
Resource    ../resources/common.resource
Resource    ../resources/variables.resource

*** Test Cases ***
Test With Resources
    # Uses keyword from common.resource
    Setup Testbed Connection
    
    # Uses variable from variables.resource
    Log    Timeout: ${DEFAULT_TIMEOUT}
```

## Architecture

Tests follow the 4-layer architecture:

```
┌─────────────────────────────────────────────────────────┐
│  Robot Test Files (.robot)                              │
│  - Test cases with scenario-aligned keywords            │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  Python Keyword Libraries (robot/libraries/)            │
│  - @keyword decorator maps to scenario steps            │
│  - Mirrors tests/step_defs/ structure                   │
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

## Keyword Naming Convention

Keywords use the `@keyword` decorator to map clean Python function names to scenario step text:

| pytest-bdd | Robot Framework |
|------------|-----------------|
| `@when("step text")` | `@keyword("step text")` |
| `tests/step_defs/acs_steps.py` | `robot/libraries/acs_keywords.py` |
| `boardfarm3.use_cases.acs` | `boardfarm3.use_cases.acs` (same) |

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

## Parallel Execution

Use `pabot` for parallel test execution:

```bash
# Install pabot
pip install robotframework-pabot

# Run tests in parallel (note: requires separate board per process)
pabot --processes 2 \
    --listener "robotframework_boardfarm.BoardfarmListener:..." \
    robot/tests/
```

## Further Reading

- [Keyword Libraries Documentation](../../robot/libraries/README.md)
- [Use Case Architecture](../use_case_architecture.md) - Architecture overview
- [robotframework-boardfarm Documentation](../../../robotframework-boardfarm/README.md)
