# Robot Framework Test Suite

This directory contains Robot Framework tests for the boardfarm BDD test suite.

## Key Principles

1. **Libraries are the single source of truth** - All keywords are defined in Python libraries (`libraries/*.py`)
2. **Tests contain no keyword definitions** - Test files (`.robot`) call library keywords directly
3. **Libraries are thin wrappers** - Keyword libraries delegate to `boardfarm3.use_cases`
4. **Resource files for patterns only** - Resources provide setup/teardown and composite patterns, not duplicate keywords

## Directory Structure

```
robot/
├── tests/                      # Robot test suites (.robot files)
│   ├── __init__.robot          # Suite initialization
│   ├── hello.robot             # Smoke tests
│   ├── remote_cpe_reboot.robot # CPE reboot scenarios
│   ├── user_makes_one_way_call.robot # Voice call scenarios
│   ├── acs_gui_device_management.robot
│   └── device_class_initialization.robot
├── resources/                  # Shared resource files
│   ├── common.resource         # Setup/teardown, composite keywords
│   ├── variables.resource      # Shared variables
│   ├── cleanup.resource        # Cleanup patterns
│   └── voice.resource          # Voice test setup/teardown
├── libraries/                  # Python keyword libraries (SINGLE SOURCE OF TRUTH)
│   ├── __init__.py
│   ├── boardfarm_keywords.py   # Device access keywords
│   ├── acs_keywords.py         # ACS operation keywords
│   ├── cpe_keywords.py         # CPE operation keywords
│   ├── voice_keywords.py       # Voice/SIP keywords
│   ├── background_keywords.py  # Background/setup keywords
│   ├── operator_keywords.py    # Operator action keywords
│   ├── acs_gui_keywords.py     # ACS GUI keywords
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
        robot/tests/remote_cpe_reboot.robot

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

### Correct Pattern: Tests Call Library Keywords Directly

Test files should **NOT** define keywords. They should call library keywords directly:

```robot
*** Settings ***
Documentation    Description of this test suite
Library    robotframework_boardfarm.BoardfarmLibrary
Library    ../libraries/boardfarm_keywords.py
Library    ../libraries/acs_keywords.py
Library    ../libraries/cpe_keywords.py
Resource   ../resources/common.resource

Suite Setup       Setup Testbed Connection
Suite Teardown    Teardown Testbed Connection

*** Test Cases ***
UC-12347-Main: Successful Remote Reboot
    [Documentation]    Main success scenario for remote CPE reboot
    [Tags]    UC-12347    reboot    smoke

    # Background: Verify CPE online (library keyword)
    ${baseline}=    A CPE Is Online And Fully Provisioned    ${ACS}    ${CPE}

    # Main scenario: Use library keywords directly
    ${result}=    The Operator Initiates A Reboot Task On The ACS For The CPE    ${ACS}    ${CPE}
    The ACS Sends A Connection Request To The CPE    ${ACS}    ${CPE}
    The CPE Sends An Inform Message To The ACS    ${ACS}    ${CPE}
    The ACS Responds To The Inform Message By Issuing The Reboot RPC    ${ACS}    ${CPE}
    The CPE Sends An Inform Message After Boot Completion    ${ACS}    ${CPE}
    The CPE Resumes Normal Operation    ${ACS}    ${CPE}
    Use Case Succeeds And All Success Guarantees Are Met    ${ACS}    ${CPE}
```

### Anti-Pattern: DO NOT Define Keywords in Tests

```robot
*** Keywords ***
# ❌ WRONG - Do not define keywords in test files
My Custom Keyword
    ${result}=    Some Library Keyword
    RETURN    ${result}
```

If you need a new keyword, add it to the appropriate library in `libraries/`.

### When to Use Resource Files

Resource files should only be used for:

1. **Suite Setup/Teardown** - Patterns that initialize test environments
2. **Composite Keywords** - High-level workflows combining multiple library calls
3. **Test Cleanup** - Patterns for cleaning up after tests

Resource files should **NOT**:
- Duplicate or wrap library keywords with the same name
- Contain business logic (that belongs in libraries)

## Architecture

### Four-Layer Abstraction

```
┌─────────────────────────────────────────────────────────────────┐
│ Layer 1: Robot Test Files (.robot)                              │
│   - Test cases that call library keywords directly              │
│   - NO keyword definitions (except minimal suite setup)         │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│ Layer 2: Python Keyword Libraries (robot/libraries/)            │
│   - SINGLE SOURCE OF TRUTH for keywords                         │
│   - @keyword decorator maps to scenario steps                   │
│   - Thin wrappers around boardfarm3.use_cases                   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│ Layer 3: boardfarm3.use_cases                                   │
│   - Business logic for test operations                          │
│   - Shared with pytest-bdd step definitions                     │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│ Layer 4: Device Templates                                       │
│   - Low-level device operations                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Keyword Library Pattern

Libraries use the `@keyword` decorator to map Python functions to scenario step text:

```python
from robot.api.deco import keyword
from boardfarm3.use_cases import acs as acs_use_cases

class AcsKeywords:
    ROBOT_LIBRARY_SCOPE = "SUITE"

    @keyword("The CPE is online via ACS")
    @keyword("CPE is reachable through ACS")  # Alias
    def verify_cpe_online(self, acs, cpe):
        """Verify CPE connectivity via ACS."""
        return acs_use_cases.is_cpe_online(acs, cpe)
```

### Comparison with pytest-bdd

| pytest-bdd | Robot Framework |
|------------|-----------------|
| `@when("step text")` | `@keyword("step text")` |
| `tests/step_defs/acs_steps.py` | `robot/libraries/acs_keywords.py` |
| `boardfarm3.use_cases.acs` | `boardfarm3.use_cases.acs` (same) |

Both frameworks delegate to the same `boardfarm3.use_cases` functions.

## Creating New Keywords

When adding new test scenarios:

1. **Check if a use_case exists** in `boardfarm3/use_cases/`
2. **Add keyword to library** in `robot/libraries/` using `@keyword` decorator
3. **Use keyword directly** in test files - no wrapper needed

See [libraries/README.md](libraries/README.md) for detailed guidelines.

## Keyword Libraries

| Library | Purpose | Mirrors |
|---------|---------|---------|
| `boardfarm_keywords.py` | Device access (Get Device By Type) | Common functionality |
| `acs_keywords.py` | ACS operations | `tests/step_defs/acs_steps.py` |
| `cpe_keywords.py` | CPE operations | `tests/step_defs/cpe_steps.py` |
| `voice_keywords.py` | Voice/SIP operations | `tests/step_defs/sip_phone_steps.py` |
| `background_keywords.py` | Background setup | `tests/step_defs/background_steps.py` |
| `operator_keywords.py` | Operator actions | `tests/step_defs/operator_steps.py` |
| `acs_gui_keywords.py` | ACS GUI operations | `tests/step_defs/acs_gui_steps.py` |

## Further Reading

- [Keyword Libraries Documentation](libraries/README.md)
- [Migration Plan](../docs/robot_keyword_migration_plan.md)
- [Project README](../README.md)
