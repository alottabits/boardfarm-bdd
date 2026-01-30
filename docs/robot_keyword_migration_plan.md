# Robot Framework Keyword Migration Plan

> **Status**: ✅ Migration Complete (January 29, 2026)
>
> This document is preserved as historical reference. The migration from `UseCaseLibrary` to
> Python Keyword Libraries has been completed. `UseCaseLibrary` has been removed from
> `robotframework-boardfarm`.

## Overview

This document outlines the migration from the **bottom-up** `UseCaseLibrary` approach to a **top-down** Python Keyword Libraries approach for Robot Framework tests.

### Current State (Bottom-Up)

```
boardfarm3.use_cases (160+ functions)
           ↓
UseCaseLibrary (auto-generates ALL keywords)
           ↓
Robot test files (use technical keyword names)
```

**Problems:**

- Keywords are auto-generated, not aligned with scenario language
- All use_cases exposed, regardless of whether they're needed
- No traceability from requirements → scenarios → keywords
- Doesn't mirror the pytest-bdd structure

### Target State (Top-Down)

```
Requirements (use case documents)
           ↓
BDD Scenarios (.robot test cases)
           ↓
Python Keyword Libraries (using @keyword decorator)
           ↓
boardfarm3.use_cases (implementation)
```

**Benefits:**

- Keywords match scenario step language via `@keyword` decorator
- Clean, reusable function names (not tied to step text)
- Multiple keyword aliases can map to the same function
- Only needed keywords are defined
- Clear traceability from requirements to implementation
- Mirrors pytest-bdd step_defs structure using decorators
- Consistent approach across both test frameworks

---

## Framework Comparison

The `@keyword` decorator in Robot Framework serves the same purpose as `@given`, `@when`, `@then` decorators in pytest-bdd:

| Aspect | pytest-bdd | Robot Framework |
|--------|------------|-----------------|
| Step mapping decorator | `@when("step text")` | `@keyword("step text")` |
| Function name | Clean, reusable | Clean, reusable |
| Multiple aliases | Via separate decorators | Multiple `@keyword` decorators |
| Documentation | Docstring | Docstring (shown in `libdoc`) |
| Implementation | Calls `use_cases` | Calls `use_cases` |

**pytest-bdd example:**

```python
@when("the ACS initiates a remote reboot of the CPE")
def initiate_reboot(acs: ACS, cpe: CPE) -> None:
    """Initiate CPE reboot via ACS."""
    acs_use_cases.initiate_reboot(acs, cpe)
```

**Robot Framework equivalent:**

```python
@keyword("The ACS initiates a remote reboot of the CPE")
def initiate_reboot(self, acs: ACS, cpe: CPE) -> None:
    """Initiate CPE reboot via ACS."""
    acs_use_cases.initiate_reboot(acs, cpe)
```

---

## Migration Phases

### Phase 1: Create Keyword Library Structure

**Location:** `boardfarm-bdd/robot/libraries/`

**Goal:** Create Python keyword library files that mirror `tests/step_defs/` structure.

#### Tasks

1.1. Create `robot/libraries/` directory structure:

```
robot/libraries/
├── __init__.py
├── boardfarm_keywords.py      # Base class and device access
├── acs_keywords.py            # Mirrors step_defs/acs_steps.py
├── cpe_keywords.py            # Mirrors step_defs/cpe_steps.py
├── voice_keywords.py          # Mirrors step_defs/voice_steps.py
├── background_keywords.py     # Mirrors step_defs/background_steps.py
└── operator_keywords.py       # Mirrors step_defs/operator_steps.py
```

1.2. Create base `boardfarm_keywords.py` with device access:

```python
"""Base Boardfarm Keywords for Robot Framework.

Provides device access and common utilities. This library works with
the BoardfarmListener to access deployed devices.
"""

from robot.api.deco import keyword

from robotframework_boardfarm.listener import get_listener


class BoardfarmKeywords:
    """Base keywords for Boardfarm device access."""

    ROBOT_LIBRARY_SCOPE = "SUITE"

    @keyword("Get device by type")
    @keyword("Get ${device_type} device")
    def get_device_by_type(self, device_type: str, index: int = 0):
        """Get a device by its type.

        Arguments:
            device_type: Type of device (e.g., "CPE", "ACS", "SIPPhone")
            index: Index if multiple devices of same type (default: 0)

        Returns:
            Device instance
        """
        listener = get_listener()
        return listener.device_manager.get_device_by_type(device_type, index)

    @keyword("Get Boardfarm config")
    def get_boardfarm_config(self):
        """Get the Boardfarm configuration."""
        listener = get_listener()
        return listener.boardfarm_config
```

1.3. Create actor-based keyword libraries using the `@keyword` decorator pattern:

```python
"""ACS Keywords - mirrors tests/step_defs/acs_steps.py

Keywords for ACS operations, aligned with BDD scenario steps.
Uses @keyword decorator to map clean function names to scenario step text.
"""

from robot.api.deco import keyword

from boardfarm3.use_cases import acs as acs_use_cases
from boardfarm3.templates.acs import ACS
from boardfarm3.templates.cpe import CPE


class AcsKeywords:
    """Keywords for ACS operations matching BDD scenario steps."""

    ROBOT_LIBRARY_SCOPE = "SUITE"

    @keyword("The CPE is online via ACS")
    @keyword("CPE is reachable through ACS")  # Alias for flexibility
    def verify_cpe_online(self, acs: ACS, cpe: CPE) -> bool:
        """Verify CPE is online via ACS.

        Maps to scenario steps:
        - "Given the CPE is online via ACS"
        - "Given CPE is reachable through ACS"
        """
        return acs_use_cases.is_cpe_online(acs, cpe)

    @keyword("The ACS initiates a remote reboot of the CPE")
    @keyword("ACS reboots the CPE")  # Shorter alias
    def initiate_reboot(self, acs: ACS, cpe: CPE) -> None:
        """Initiate CPE reboot via ACS.

        Maps to scenario steps:
        - "When the ACS initiates a remote reboot of the CPE"
        - "When ACS reboots the CPE"
        """
        acs_use_cases.initiate_reboot(acs, cpe)

    @keyword("The CPE should have rebooted")
    def verify_reboot_completed(self, cpe: CPE, initial_uptime: float) -> None:
        """Verify CPE has rebooted by checking uptime decreased.

        Maps to scenario step:
        - "Then the CPE should have rebooted"
        """
        current_uptime = acs_use_cases.get_uptime(cpe)
        if current_uptime >= initial_uptime:
            raise AssertionError(
                f"CPE did not reboot: uptime {current_uptime} >= {initial_uptime}"
            )
```

#### Deliverables

- [ ] `robot/libraries/__init__.py`
- [ ] `robot/libraries/boardfarm_keywords.py`
- [ ] `robot/libraries/acs_keywords.py`
- [ ] `robot/libraries/cpe_keywords.py`
- [ ] `robot/libraries/voice_keywords.py`
- [ ] `robot/libraries/background_keywords.py`
- [ ] `robot/libraries/operator_keywords.py`

---

### Phase 2: Migrate Existing Keywords from step_defs

**Goal:** For each step definition in `tests/step_defs/`, create equivalent keywords in `robot/libraries/`.

#### Tasks

2.1. Audit existing step definitions:

```bash
# List all step definitions
grep -r "@given\|@when\|@then" tests/step_defs/*.py
```

2.2. For each step definition, create a corresponding keyword using the `@keyword` decorator:

**pytest-bdd step definition:**

```python
# tests/step_defs/acs_steps.py
@when("the ACS initiates a remote reboot of the CPE")
def initiate_reboot(acs: ACS, cpe: CPE) -> None:
    """Initiate CPE reboot via ACS."""
    acs_use_cases.initiate_reboot(acs, cpe)
```

**Equivalent Robot keyword:**

```python
# robot/libraries/acs_keywords.py
from robot.api.deco import keyword

@keyword("The ACS initiates a remote reboot of the CPE")
def initiate_reboot(self, acs: ACS, cpe: CPE) -> None:
    """Initiate CPE reboot via ACS.

    Maps to: "When the ACS initiates a remote reboot of the CPE"
    """
    acs_use_cases.initiate_reboot(acs, cpe)
```

2.3. Consider adding keyword aliases for flexibility:

```python
@keyword("The ACS initiates a remote reboot of the CPE")
@keyword("ACS reboots the CPE")
@keyword("Reboot CPE via ACS")
def initiate_reboot(self, acs: ACS, cpe: CPE) -> None:
    """Initiate CPE reboot via ACS."""
    acs_use_cases.initiate_reboot(acs, cpe)
```

#### Mapping Table

| step_defs file | Robot library file | Status |
|----------------|-------------------|--------|
| `acs_steps.py` | `acs_keywords.py` | Pending |
| `cpe_steps.py` | `cpe_keywords.py` | Pending |
| `voice_steps.py` | `voice_keywords.py` | Pending |
| `background_steps.py` | `background_keywords.py` | Pending |
| `operator_steps.py` | `operator_keywords.py` | Pending |
| `acs_gui_steps.py` | `acs_gui_keywords.py` | Pending |
| `sip_phone_steps.py` | `sip_phone_keywords.py` | Pending |

---

### Phase 3: Update Robot Test Files

**Goal:** Update existing `.robot` files to use new keyword libraries instead of UseCaseLibrary.

#### Tasks

3.1. Update library imports in all `.robot` files:

**Before:**

```robot
*** Settings ***
Library    robotframework_boardfarm.BoardfarmLibrary
Library    robotframework_boardfarm.UseCaseLibrary
```

**After:**

```robot
*** Settings ***
Library    robotframework_boardfarm.BoardfarmLibrary
Library    ../libraries/boardfarm_keywords.py
Library    ../libraries/acs_keywords.py
Library    ../libraries/cpe_keywords.py
# Add other libraries as needed
```

3.2. Update keyword calls to use the decorator-defined names:

**Before (auto-generated technical names):**

```robot
*** Test Cases ***
Test CPE Reboot
    ${acs}=    Get Device By Type    ACS
    ${cpe}=    Get Device By Type    CPE
    Acs Initiate Reboot    ${acs}    ${cpe}
```

**After (scenario-aligned names from @keyword decorator):**

```robot
*** Test Cases ***
UC-12347-Main: Successful Remote Reboot
    [Documentation]    Main success scenario from UC-12347

    # Given
    ${acs}=    Get Device By Type    ACS
    ${cpe}=    Get Device By Type    CPE
    The CPE Is Online Via ACS    ${acs}    ${cpe}

    # When
    The ACS Initiates A Remote Reboot Of The CPE    ${acs}    ${cpe}

    # Then
    The CPE Should Have Rebooted    ${cpe}    ${initial_uptime}
```

3.3. Files to update:

- [ ] `robot/tests/hello.robot`
- [ ] `robot/tests/remote_cpe_reboot.robot`
- [ ] `robot/tests/user_makes_one_way_call.robot`
- [ ] `robot/tests/acs_gui_device_management.robot`
- [ ] `robot/tests/device_class_initialization.robot`
- [ ] `robot/tests/__init__.robot`

3.4. Update resource files:

- [ ] `robot/resources/common.resource`
- [ ] `robot/resources/voice.resource`
- [ ] `robot/resources/cleanup.resource`

---

### Phase 4: Remove UseCaseLibrary

**Location:** `robotframework-boardfarm/`

**Goal:** Remove UseCaseLibrary from robotframework-boardfarm.

#### Tasks

4.1. Remove `use_case_library.py` from robotframework-boardfarm

4.2. Remove UseCaseLibrary from `__init__.py` exports

4.3. Remove any tests related to UseCaseLibrary

4.4. Update version number (semantic versioning)

---

### Phase 5: Update Documentation

**Goal:** Update all documentation to reflect the new approach.

#### Tasks

5.1. Update `boardfarm-bdd/robot/README.md`:

- Document keyword library structure
- Explain the `@keyword` decorator pattern
- Provide examples showing decorator usage

5.2. Update `boardfarm-bdd/docs/robot/getting_started.md`:

- Update library import examples
- Add section on creating new keywords with `@keyword` decorator
- Link keyword libraries to step_defs equivalents

5.3. Update `robotframework-boardfarm/README.md`:

- Remove all references to UseCaseLibrary
- Document BoardfarmLibrary as the primary library
- Explain that keywords should be in test project using `@keyword` decorator

5.4. Create `boardfarm-bdd/robot/libraries/README.md`:

- Document the keyword library structure
- Explain `@keyword` decorator usage
- Provide template for new keywords

---

## Implementation Order

```
Phase 1: Create Keyword Library Structure
    ↓
Phase 2: Migrate Existing Keywords from step_defs
    ↓
Phase 3: Update Robot Test Files
    ↓
Phase 4: Remove UseCaseLibrary
    ↓
Phase 5: Update Documentation
```

---

## Keyword Design Guidelines

### Using the `@keyword` Decorator

The `@keyword` decorator from `robot.api.deco` maps clean Python function names to scenario step text:

```python
from robot.api.deco import keyword

class AcsKeywords:
    ROBOT_LIBRARY_SCOPE = "SUITE"

    @keyword("The CPE is online via ACS")
    def verify_cpe_online(self, acs, cpe):
        """Verify CPE connectivity via ACS."""
        return acs_use_cases.is_cpe_online(acs, cpe)
```

### Multiple Keyword Aliases

Use multiple `@keyword` decorators to support different step phrasings:

```python
@keyword("The CPE is online via ACS")
@keyword("CPE is reachable through ACS")
@keyword("Verify CPE connectivity")
def verify_cpe_online(self, acs, cpe):
    """Verify CPE connectivity via ACS.

    Supports multiple step phrasings for flexibility.
    """
    return acs_use_cases.is_cpe_online(acs, cpe)
```

### Function Naming Convention

Keep function names clean and descriptive (not tied to step text):

| Good (clean) | Bad (verbatim step text) |
|--------------|--------------------------|
| `verify_cpe_online` | `the_cpe_is_online_via_acs` |
| `initiate_reboot` | `the_acs_initiates_a_remote_reboot_of_the_cpe` |
| `verify_reboot_completed` | `the_cpe_should_have_rebooted` |
| `make_call` | `user_a_makes_a_call_to_user_b` |

### Documentation

Each keyword should include:

- Docstring explaining what it does
- "Maps to:" comment listing the scenario step(s)
- Type hints for parameters

```python
@keyword("The ACS initiates a remote reboot of the CPE")
@keyword("ACS reboots the CPE")
def initiate_reboot(self, acs: ACS, cpe: CPE) -> None:
    """Initiate CPE reboot via ACS.

    Maps to scenario steps:
    - "When the ACS initiates a remote reboot of the CPE"
    - "When ACS reboots the CPE"

    Arguments:
        acs: ACS device instance
        cpe: CPE device instance
    """
    acs_use_cases.initiate_reboot(acs, cpe)
```

### Side-by-Side Comparison: pytest-bdd vs Robot Framework

**pytest-bdd (tests/step_defs/acs_steps.py):**

```python
from pytest_bdd import when, then

@when("the ACS initiates a remote reboot of the CPE")
def initiate_reboot(acs: ACS, cpe: CPE) -> None:
    """Initiate CPE reboot via ACS."""
    acs_use_cases.initiate_reboot(acs, cpe)

@then("the CPE should have rebooted")
def verify_reboot(cpe: CPE, initial_uptime: float) -> None:
    """Verify CPE has rebooted."""
    assert acs_use_cases.get_uptime(cpe) < initial_uptime
```

**Robot Framework (robot/libraries/acs_keywords.py):**

```python
from robot.api.deco import keyword

@keyword("The ACS initiates a remote reboot of the CPE")
def initiate_reboot(self, acs: ACS, cpe: CPE) -> None:
    """Initiate CPE reboot via ACS."""
    acs_use_cases.initiate_reboot(acs, cpe)

@keyword("The CPE should have rebooted")
def verify_reboot(self, cpe: CPE, initial_uptime: float) -> None:
    """Verify CPE has rebooted."""
    if acs_use_cases.get_uptime(cpe) >= initial_uptime:
        raise AssertionError("CPE did not reboot")
```

---

## Validation Checklist

### Phase 1 Complete

- [ ] All keyword library files created
- [ ] `@keyword` decorators properly imported
- [ ] Base BoardfarmKeywords class working
- [ ] Libraries can be imported without errors

### Phase 2 Complete

- [ ] All step definitions have equivalent keywords
- [ ] Keywords use `@keyword` decorator (not verbatim function names)
- [ ] Type hints in place
- [ ] Appropriate aliases added for flexibility

### Phase 3 Complete

- [ ] All .robot files updated
- [ ] All tests pass with new keywords
- [ ] No UseCaseLibrary imports remain

### Phase 4 Complete

- [ ] `use_case_library.py` removed
- [ ] UseCaseLibrary removed from `__init__.py`
- [ ] Related tests removed
- [ ] Version bumped

### Phase 5 Complete

- [ ] All documentation updated
- [ ] Examples show `@keyword` decorator usage
- [ ] Keyword library README created
- [ ] All UseCaseLibrary references removed from docs

---

## Rollback Plan

If issues arise during migration:

1. **Version control** - Tag releases before major changes
2. **Test isolation** - Migrate one test file at a time
3. **Git history** - UseCaseLibrary can be restored from git if needed

---

## Success Criteria

1. **Consistency**: Robot Framework keyword structure mirrors pytest-bdd step_defs (decorator-based mapping)
2. **Reusability**: Clean function names that can be reused or aliased
3. **Flexibility**: Multiple keyword aliases support different step phrasings
4. **Traceability**: Clear path from requirements → scenarios → keywords → use_cases
5. **Maintainability**: Adding new keywords follows same pattern as adding step definitions
6. **Tests pass**: All existing tests continue to work
7. **Documentation**: Clear guidance for test authors
