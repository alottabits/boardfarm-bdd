# Robot Framework Keyword Libraries

This directory contains Python keyword libraries for Robot Framework tests.
These libraries mirror the pytest-bdd step definitions in `tests/step_defs/`.

## Architecture

The keyword libraries use the `@keyword` decorator to map clean Python function names
to scenario step text, providing:

- **Reusability**: Same function can have multiple keyword aliases
- **Consistency**: Mirrors pytest-bdd's decorator pattern
- **Flexibility**: Step text can vary without changing function names
- **Maintainability**: Clean code that's easy to understand

## Libraries

| Library | Description | Mirrors |
|---------|-------------|---------|
| `boardfarm_keywords.py` | Base keywords for device access | Common functionality |
| `acs_keywords.py` | ACS operations | `tests/step_defs/acs_steps.py` |
| `cpe_keywords.py` | CPE operations | `tests/step_defs/cpe_steps.py` |
| `voice_keywords.py` | SIP phone/voice operations | `tests/step_defs/sip_phone_steps.py` |
| `background_keywords.py` | Background/setup operations | `tests/step_defs/background_steps.py` |
| `operator_keywords.py` | Operator-initiated operations | `tests/step_defs/operator_steps.py` |
| `acs_gui_keywords.py` | ACS GUI operations | `tests/step_defs/acs_gui_steps.py` |
| `device_class_keywords.py` | Device initialization | `tests/step_defs/device_class_steps.py` |
| `hello_keywords.py` | Simple smoke tests | `tests/step_defs/hello_steps.py` |

## Usage

### Import Libraries

```robot
*** Settings ***
Library    robotframework_boardfarm.BoardfarmLibrary
Library    ../libraries/boardfarm_keywords.py
Library    ../libraries/acs_keywords.py
Library    ../libraries/cpe_keywords.py
```

### Use Keywords

```robot
*** Test Cases ***
UC-12347: Remote CPE Reboot
    [Documentation]    Remote reboot of CPE via ACS

    # Setup
    ${acs}=    Get Device By Type    ACS
    ${cpe}=    Get Device By Type    CPE

    # Given
    A CPE Is Online And Fully Provisioned    ${acs}    ${cpe}

    # When
    The Operator Initiates A Reboot Task On The ACS For The CPE    ${acs}    ${cpe}

    # Then
    Use Case Succeeds And All Success Guarantees Are Met    ${acs}    ${cpe}
```

## Creating New Keywords

### Template

```python
"""Module Keywords for Robot Framework.

Keywords for [description], aligned with BDD scenario steps.
Uses @keyword decorator to map clean function names to scenario step text.

Mirrors: tests/step_defs/module_steps.py
"""

from robot.api.deco import keyword

from boardfarm3.use_cases import module as module_use_cases


class ModuleKeywords:
    """Keywords for [description] matching BDD scenario steps."""

    ROBOT_LIBRARY_SCOPE = "SUITE"
    ROBOT_LIBRARY_DOC_FORMAT = "TEXT"

    @keyword("The action happens")
    @keyword("Action happens")  # Shorter alias
    def perform_action(self, device: Any, parameter: str) -> None:
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

1. **Use `@keyword` decorator** for all public methods
2. **Multiple aliases** for flexibility in step phrasing
3. **Clean function names** (not verbatim step text)
4. **Docstring** with "Maps to:" showing scenario steps
5. **Type hints** for parameters
6. **Delegate to use_cases** for business logic

## Comparison with pytest-bdd

| Aspect | pytest-bdd | Robot Framework |
|--------|------------|-----------------|
| Step mapping | `@when("step text")` | `@keyword("step text")` |
| Function name | Clean, reusable | Clean, reusable |
| Multiple aliases | Separate decorators | Multiple `@keyword` decorators |
| Implementation | Calls `use_cases` | Calls `use_cases` |

### pytest-bdd Example

```python
from pytest_bdd import when

@when("the ACS initiates a remote reboot of the CPE")
def initiate_reboot(acs: ACS, cpe: CPE) -> None:
    """Initiate CPE reboot via ACS."""
    acs_use_cases.initiate_reboot(acs, cpe)
```

### Robot Framework Equivalent

```python
from robot.api.deco import keyword

@keyword("The ACS initiates a remote reboot of the CPE")
def initiate_reboot(self, acs: ACS, cpe: CPE) -> None:
    """Initiate CPE reboot via ACS."""
    acs_use_cases.initiate_reboot(acs, cpe)
```

## Library Scope

All libraries use `ROBOT_LIBRARY_SCOPE = "SUITE"` which means:

- One library instance per test suite
- State is preserved across test cases in the same suite
- State is reset when moving to a new suite

## Related Documentation

- [Robot Framework Getting Started](../../docs/robot/getting_started.md)
- [Robot Framework Keyword Reference](../../docs/robot/keyword_reference.md)
- [Migration Plan](../../docs/robot_keyword_migration_plan.md)
