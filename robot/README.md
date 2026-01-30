# Robot Framework Test Suite

This directory contains Robot Framework tests for the boardfarm BDD test suite.

## Directory Structure

```
robot/
├── tests/                      # Robot test suites (.robot files)
│   ├── __init__.robot          # Suite initialization
│   ├── hello.robot             # Smoke tests
│   ├── remote_cpe_reboot.robot
│   ├── user_makes_one_way_call.robot
│   ├── acs_gui_device_management.robot
│   └── device_class_initialization.robot
├── resources/                  # Shared resource files
│   ├── common.resource         # Common keywords
│   ├── variables.resource      # Shared variables
│   ├── cleanup.resource        # Cleanup keywords
│   └── voice.resource          # Voice test keywords
├── libraries/                  # Python keyword libraries
│   ├── __init__.py
│   ├── boardfarm_keywords.py   # Base device access keywords
│   ├── acs_keywords.py         # ACS operation keywords
│   ├── cpe_keywords.py         # CPE operation keywords
│   ├── voice_keywords.py       # Voice/SIP keywords
│   ├── background_keywords.py  # Background/setup keywords
│   ├── operator_keywords.py    # Operator action keywords
│   ├── acs_gui_keywords.py     # ACS GUI keywords
│   ├── device_class_keywords.py # Device initialization keywords
│   ├── hello_keywords.py       # Smoke test keywords
│   └── README.md               # Keyword library documentation
└── robot.yaml                  # Robot Framework configuration
```

## Quick Start

### Installation

```bash
# From project root
pip install -e ".[robot]"
```

This installs:

- `robotframework` - Robot Framework test automation
- `robotframework-boardfarm` - Boardfarm integration (includes `bfrobot` CLI)

### Running Tests

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

### Filtering Tests

```bash
# Run by tag
bfrobot ... --include smoke robot/tests/

# Run by test name pattern
bfrobot ... --test "*Reboot*" robot/tests/

# Exclude tests
bfrobot ... --exclude slow robot/tests/
```

## Writing Tests

### Basic Test Structure

```robot
*** Settings ***
Documentation    Description of this test suite
Library    robotframework_boardfarm.BoardfarmLibrary
Library    ../libraries/boardfarm_keywords.py
Library    ../libraries/acs_keywords.py
Library    ../libraries/cpe_keywords.py
Resource   ../resources/common.resource

*** Test Cases ***
My Test Case
    [Documentation]    What this test verifies
    [Tags]    smoke    my-feature

    # Get devices
    ${cpe}=    Get Device By Type    CPE
    ${acs}=    Get Device By Type    ACS

    # Use scenario-aligned keywords
    The CPE Is Online Via ACS    ${acs}    ${cpe}
    
    # Get parameters
    ${version}=    Get ACS Parameter Value    ${acs}    ${cpe}
    ...    Device.DeviceInfo.SoftwareVersion

    # Verify results
    Should Not Be Empty    ${version}
    Log    Software Version: ${version}
```

### Keyword Libraries

| Library | Purpose | Mirrors |
|---------|---------|---------|
| `boardfarm_keywords.py` | Device access (Get Device By Type) | Common functionality |
| `acs_keywords.py` | ACS operations | `tests/step_defs/acs_steps.py` |
| `cpe_keywords.py` | CPE operations | `tests/step_defs/cpe_steps.py` |
| `voice_keywords.py` | Voice/SIP operations | `tests/step_defs/sip_phone_steps.py` |
| `background_keywords.py` | Background setup | `tests/step_defs/background_steps.py` |
| `operator_keywords.py` | Operator actions | `tests/step_defs/operator_steps.py` |
| `acs_gui_keywords.py` | ACS GUI operations | `tests/step_defs/acs_gui_steps.py` |

### Keyword Naming Convention

Keywords use the `@keyword` decorator to map clean Python function names to
scenario step text. This mirrors the pytest-bdd approach:

**Python Keyword Library:**

```python
from robot.api.deco import keyword

@keyword("The CPE is online via ACS")
@keyword("CPE is reachable through ACS")  # Alias
def verify_cpe_online(self, acs, cpe):
    """Verify CPE connectivity via ACS."""
    return acs_use_cases.is_cpe_online(acs, cpe)
```

**Robot Test Usage:**

```robot
*** Test Cases ***
Verify CPE Online
    ${acs}=    Get Device By Type    ACS
    ${cpe}=    Get Device By Type    CPE
    The CPE Is Online Via ACS    ${acs}    ${cpe}
```

### Comparison with pytest-bdd

| pytest-bdd | Robot Framework |
|------------|-----------------|
| `@when("step text")` | `@keyword("step text")` |
| `tests/step_defs/acs_steps.py` | `robot/libraries/acs_keywords.py` |
| `boardfarm3.use_cases.acs` | `boardfarm3.use_cases.acs` (same) |

Both frameworks delegate to the same `boardfarm3.use_cases` functions.

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
└─────────────────────────────────────────────────────────┘
```

## Creating New Keywords

When adding new test scenarios:

1. Check if a pytest-bdd step definition exists in `tests/step_defs/`
2. Create the equivalent keyword in `robot/libraries/` using `@keyword` decorator
3. Keywords should delegate to `boardfarm3.use_cases` functions

See [libraries/README.md](libraries/README.md) for detailed guidelines.

## Further Reading

- [Keyword Libraries Documentation](libraries/README.md)
- [Detailed Getting Started Guide](../docs/robot/getting_started.md)
- [Keyword Reference](../docs/robot/keyword_reference.md)
- [Use Case Architecture](../docs/use_case_architecture.md)
- [Migration Plan](../docs/robot_keyword_migration_plan.md)
- [Project README](../README.md)
