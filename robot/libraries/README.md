# Robot Framework Keyword Libraries

This directory contains Python keyword libraries for Robot Framework tests.
These libraries are the **single source of truth** for all test keywords.

## Key Principles

1. **Libraries are the single source of truth** - All keywords are defined here
2. **Tests call library keywords directly** - No keyword definitions in `.robot` files
3. **Libraries are thin wrappers** - Delegate to `boardfarm3.use_cases`
4. **Mirrors pytest-bdd structure** - Same use_cases, same naming patterns

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ Robot Test Files (.robot)                                       │
│   - Call library keywords directly                              │
│   - NO keyword definitions                                      │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│ Keyword Libraries (this directory)                              │
│   - SINGLE SOURCE OF TRUTH                                      │
│   - @keyword decorator maps to scenario steps                   │
│   - Thin wrappers around boardfarm3.use_cases                   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│ boardfarm3.use_cases                                            │
│   - Business logic (shared with pytest-bdd)                     │
└─────────────────────────────────────────────────────────────────┘
```

## Libraries

| Library | Description | Mirrors |
|---------|-------------|---------|
| `boardfarm_keywords.py` | Device access keywords | Common functionality |
| `acs_keywords.py` | ACS operations | `tests/step_defs/acs_steps.py` |
| `cpe_keywords.py` | CPE operations | `tests/step_defs/cpe_steps.py` |
| `voice_keywords.py` | SIP phone/voice operations | `tests/step_defs/sip_phone_steps.py` |
| `background_keywords.py` | Background/setup operations | `tests/step_defs/background_steps.py` |
| `operator_keywords.py` | Operator-initiated operations | `tests/step_defs/operator_steps.py` |
| `acs_gui_keywords.py` | ACS GUI operations | `tests/step_defs/acs_gui_steps.py` |
| `device_class_keywords.py` | Device initialization | `tests/step_defs/device_class_steps.py` |
| `hello_keywords.py` | Simple smoke tests | `tests/step_defs/hello_steps.py` |

## Usage

### Import Libraries in Tests

```robot
*** Settings ***
Library    robotframework_boardfarm.BoardfarmLibrary
Library    ../libraries/boardfarm_keywords.py
Library    ../libraries/acs_keywords.py
Library    ../libraries/cpe_keywords.py
```

### Call Keywords Directly (Correct)

```robot
*** Test Cases ***
UC-12347: Remote CPE Reboot
    [Documentation]    Remote reboot of CPE via ACS

    # Get devices
    ${acs}=    Get Device By Type    ACS
    ${cpe}=    Get Device By Type    CPE

    # Call library keywords DIRECTLY
    A CPE Is Online And Fully Provisioned    ${acs}    ${cpe}
    The Operator Initiates A Reboot Task On The ACS For The CPE    ${acs}    ${cpe}
    Use Case Succeeds And All Success Guarantees Are Met    ${acs}    ${cpe}
```

### Anti-Pattern: DO NOT Define Keywords in Tests

```robot
*** Keywords ***
# ❌ WRONG - Keywords belong in libraries, not test files
My Custom Keyword
    ${acs}=    Get Device By Type    ACS
    The ACS Does Something    ${acs}
```

If you need a new keyword:
1. Add it to the appropriate library in this directory
2. Use the `@keyword` decorator
3. Delegate to `boardfarm3.use_cases`

## Creating New Keywords

### Template

```python
"""Module Keywords for Robot Framework.

Keywords for [description], aligned with BDD scenario steps.
Uses @keyword decorator to map clean function names to scenario step text.

Mirrors: tests/step_defs/module_steps.py
"""

from robot.api.deco import keyword, library

from boardfarm3.use_cases import module as module_use_cases


@library(scope="SUITE", doc_format="TEXT")
class ModuleKeywords:
    """Keywords for [description] matching BDD scenario steps."""

    @keyword("The action happens")
    @keyword("Action happens")  # Shorter alias
    def perform_action(self, device, parameter: str) -> None:
        """Perform the action.

        Maps to scenario steps:
        - "When the action happens"
        - "Action happens"

        Arguments:
            device: Device instance
            parameter: Parameter value
        """
        module_use_cases.perform_action(device, parameter)
        print("✓ Action completed")
```

### Key Guidelines

1. **Use `@keyword` decorator** - Maps clean Python function names to scenario step text
2. **Multiple aliases** - Add flexibility with multiple `@keyword` decorators
3. **Clean function names** - Use descriptive names, not verbatim step text
4. **Docstring** - Include "Maps to:" showing scenario steps
5. **Type hints** - Document parameter types
6. **Delegate to use_cases** - Business logic belongs in `boardfarm3.use_cases`
7. **Print status** - Use `print("✓ ...")` for progress feedback

## Comparison with pytest-bdd

| Aspect | pytest-bdd | Robot Framework |
|--------|------------|-----------------|
| Step mapping | `@when("step text")` | `@keyword("step text")` |
| Function name | Clean, reusable | Clean, reusable |
| Multiple aliases | Separate decorators | Multiple `@keyword` decorators |
| Implementation | Calls `use_cases` | Calls `use_cases` |
| Location | `tests/step_defs/` | `robot/libraries/` |

### pytest-bdd Example

```python
# tests/step_defs/acs_steps.py
from pytest_bdd import when

@when("the ACS initiates a remote reboot of the CPE")
def initiate_reboot(acs: ACS, cpe: CPE) -> None:
    """Initiate CPE reboot via ACS."""
    acs_use_cases.initiate_reboot(acs, cpe)
```

### Robot Framework Equivalent

```python
# robot/libraries/acs_keywords.py
from robot.api.deco import keyword

@keyword("The ACS initiates a remote reboot of the CPE")
def initiate_reboot(self, acs: ACS, cpe: CPE) -> None:
    """Initiate CPE reboot via ACS."""
    acs_use_cases.initiate_reboot(acs, cpe)
```

## Library Scope

All libraries use `@library(scope="SUITE")` which means:

- One library instance per test suite
- State is preserved across test cases in the same suite
- State is reset when moving to a new suite

## Best Practices

### DO

- ✅ Define all keywords in libraries
- ✅ Use `@keyword` decorator for scenario-aligned names
- ✅ Delegate to `boardfarm3.use_cases`
- ✅ Provide multiple aliases for flexibility
- ✅ Include clear docstrings with "Maps to:" sections

### DON'T

- ❌ Define keywords in `.robot` test files
- ❌ Duplicate keywords between libraries and resource files
- ❌ Put business logic in keyword libraries (use `use_cases`)
- ❌ Create keywords that don't map to scenario steps
