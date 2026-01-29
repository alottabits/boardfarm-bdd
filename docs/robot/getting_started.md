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
Library     BoardfarmLibrary
Library     UseCaseLibrary
Resource    ../resources/common.resource

Suite Setup       Setup Testbed Connection
Suite Teardown    Teardown Testbed Connection
Test Teardown     Cleanup After Test

*** Test Cases ***
My Test Case
    [Documentation]    What this test verifies
    [Tags]    smoke    my-feature

    # Given
    ${cpe}=    Get Device By Type    CPE
    ${acs}=    Get Device By Type    ACS
    
    # When
    ${result}=    Acs Get Parameter Value    ${acs}    ${cpe}
    ...    Device.DeviceInfo.SoftwareVersion
    
    # Then
    Should Not Be Empty    ${result}
    Log    Software Version: ${result}
```

### Using Libraries

Robot Framework tests use two main libraries:

1. **BoardfarmLibrary** - Device access and configuration
2. **UseCaseLibrary** - High-level test operations (recommended)

```robot
*** Settings ***
Library    BoardfarmLibrary
Library    UseCaseLibrary

*** Test Cases ***
Example Using UseCaseLibrary
    # Get devices
    ${acs}=    Get Device By Type    ACS
    ${cpe}=    Get Device By Type    CPE
    
    # Use high-level keywords from use_cases
    ${online}=    Acs Is Cpe Online    ${acs}    ${cpe}
    Should Be True    ${online}
    
    # Get parameter value
    ${version}=    Acs Get Parameter Value    ${acs}    ${cpe}
    ...    Device.DeviceInfo.SoftwareVersion
    Log    Version: ${version}
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
│  - Test cases and keywords                              │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  UseCaseLibrary                                         │
│  - Exposes boardfarm3.use_cases as keywords             │
│  - E.g., "Acs Get Parameter Value" → acs.get_param...   │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  boardfarm3.use_cases                                   │
│  - Reusable test operations                             │
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

UseCaseLibrary converts `boardfarm3.use_cases` functions to Robot keywords:

| Use Case Function | Robot Keyword |
|-------------------|---------------|
| `acs.get_parameter_value()` | `Acs Get Parameter Value` |
| `acs.is_cpe_online()` | `Acs Is Cpe Online` |
| `cpe.get_cpu_usage()` | `Cpe Get Cpu Usage` |
| `voice.call_a_phone()` | `Voice Call A Phone` |

Pattern: `module_name.function_name()` → `Module Name Function Name`

## Reporting

Robot Framework generates HTML reports automatically:

```bash
# Default output (log.html, report.html, output.xml)
robot --outputdir results robot/tests/

# Custom report names
robot --log mylog.html --report myreport.html robot/tests/
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

# Run tests in parallel
pabot --processes 2 \
    --listener "robotframework_boardfarm.BoardfarmListener:..." \
    robot/tests/
```

## Further Reading

- [Keyword Reference](keyword_reference.md) - Complete keyword documentation
- [Use Case Architecture](../use_case_architecture.md) - Architecture overview
- [robotframework-boardfarm Documentation](../../robotframework-boardfarm/README.md)
