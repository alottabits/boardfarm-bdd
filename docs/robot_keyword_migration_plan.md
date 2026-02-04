# Robot Framework Keyword Migration Plan

> **Status**: ✅ Migration Complete (February 4, 2026)
>
> This document describes the completed migration to the keyword library architecture.
> All Robot Framework tests now follow this structure.

## Final Architecture

### Key Principles (Implemented)

1. **Libraries are the single source of truth** - All keywords defined in `robot/libraries/*.py`
2. **Tests contain no keyword definitions** - Test files call library keywords directly
3. **Libraries are thin wrappers** - Delegate to `boardfarm3.use_cases`
4. **Resource files for patterns only** - Setup/teardown and composite patterns, not duplicate keywords

### Four-Layer Abstraction (Implemented)

```
┌─────────────────────────────────────────────────────────────────┐
│ Layer 1: Robot Test Files (.robot)                              │
│   - Test cases call library keywords DIRECTLY                   │
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

---

## Completed Migration

### Phase 1: Keyword Library Structure ✅

**Location:** `boardfarm-bdd/robot/libraries/`

Created Python keyword library files that mirror `tests/step_defs/` structure:

```
robot/libraries/
├── __init__.py
├── boardfarm_keywords.py      # Device access
├── acs_keywords.py            # Mirrors step_defs/acs_steps.py
├── cpe_keywords.py            # Mirrors step_defs/cpe_steps.py
├── voice_keywords.py          # Mirrors step_defs/sip_phone_steps.py
├── background_keywords.py     # Mirrors step_defs/background_steps.py
├── operator_keywords.py       # Mirrors step_defs/operator_steps.py
├── acs_gui_keywords.py        # Mirrors step_defs/acs_gui_steps.py
├── device_class_keywords.py   # Mirrors step_defs/device_class_steps.py
├── hello_keywords.py          # Smoke test keywords
└── README.md
```

### Phase 2: Migrate Keywords from step_defs ✅

All pytest-bdd step definitions have equivalent Robot Framework keywords:

| step_defs file | Robot library file | Status |
|----------------|-------------------|--------|
| `acs_steps.py` | `acs_keywords.py` | ✅ Complete |
| `cpe_steps.py` | `cpe_keywords.py` | ✅ Complete |
| `sip_phone_steps.py` | `voice_keywords.py` | ✅ Complete |
| `background_steps.py` | `background_keywords.py` | ✅ Complete |
| `operator_steps.py` | `operator_keywords.py` | ✅ Complete |
| `acs_gui_steps.py` | `acs_gui_keywords.py` | ✅ Complete |

### Phase 3: Refactor Robot Test Files ✅

All `.robot` test files updated to:
- Import keyword libraries directly
- Call library keywords directly (no wrappers)
- Remove all local keyword definitions

**Refactored Files:**

| File | Before | After | Status |
|------|--------|-------|--------|
| `remote_cpe_reboot.robot` | 177 lines, 16 local keywords | 100 lines, 1 setup keyword | ✅ Complete |
| `user_makes_one_way_call.robot` | 252 lines, 20 local keywords | 135 lines, 0 local keywords | ✅ Complete |

### Phase 4: Remove UseCaseLibrary ✅

- `UseCaseLibrary` removed from `robotframework-boardfarm`
- All tests use keyword libraries instead
- Version bumped

### Phase 5: Update Documentation ✅

- `boardfarm-bdd/robot/README.md` - Updated with new architecture
- `boardfarm-bdd/robot/libraries/README.md` - Updated with guidelines
- `robotframework-boardfarm/README.md` - Updated
- This migration plan - Marked complete

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
| Location | `tests/step_defs/` | `robot/libraries/` |

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

## Correct Test Structure

### ✅ Correct Pattern: Tests Call Library Keywords Directly

```robot
*** Settings ***
Library    robotframework_boardfarm.BoardfarmLibrary
Library    ../libraries/acs_keywords.py
Library    ../libraries/cpe_keywords.py
Resource   ../resources/common.resource

Suite Setup       Setup Testbed Connection
Suite Teardown    Teardown Testbed Connection

*** Test Cases ***
UC-12347-Main: Successful Remote Reboot
    [Documentation]    Main success scenario

    # Call library keywords DIRECTLY - no wrappers
    ${baseline}=    A CPE Is Online And Fully Provisioned    ${ACS}    ${CPE}
    ${result}=    The Operator Initiates A Reboot Task On The ACS For The CPE    ${ACS}    ${CPE}
    The ACS Sends A Connection Request To The CPE    ${ACS}    ${CPE}
    The CPE Sends An Inform Message To The ACS    ${ACS}    ${CPE}
    Use Case Succeeds And All Success Guarantees Are Met    ${ACS}    ${CPE}
```

### ❌ Anti-Pattern: DO NOT Define Keywords in Tests

```robot
*** Keywords ***
# ❌ WRONG - This defeats the purpose of having libraries
A CPE Is Online And Fully Provisioned
    ${acs}=    Get Device By Type    ACS
    ${cpe}=    Get Device By Type    CPE
    ${baseline}=    background_keywords.A CPE Is Online And Fully Provisioned    ${acs}    ${cpe}
    RETURN    ${baseline}
```

**Problems with this anti-pattern:**
- Creates naming conflicts (hence the `fully qualified name` workarounds)
- Duplicates what's already in libraries
- Makes maintenance harder (changes needed in multiple places)
- Obscures the actual test logic

---

## Resource File Guidelines

Resource files should **only** be used for:

### ✅ Appropriate Uses

1. **Suite Setup/Teardown** - Initialize test environments
   ```robot
   Setup Testbed Connection
       ${acs}=    Get Device By Type    ACS
       ${cpe}=    Get Device By Type    CPE
       Set Suite Variable    ${ACS}
       Set Suite Variable    ${CPE}
   ```

2. **Composite Keywords** - Combine multiple library calls into workflows
   ```robot
   Cleanup After Reboot Test
       [Arguments]    ${acs}    ${cpe}    ${admin_user_index}
       Run Keyword And Ignore Error    Cleanup After Test
       IF    $admin_user_index is not None
           Run Keyword And Ignore Error    Restore CPE GUI Password To Default    ${acs}    ${cpe}    ${admin_user_index}
       END
   ```

### ❌ Inappropriate Uses

- **Wrapping library keywords** with the same name (causes recursion)
- **Duplicating library functionality** (defeats single source of truth)
- **Adding business logic** (belongs in libraries/use_cases)

---

## Success Criteria (All Met)

| Criteria | Status |
|----------|--------|
| Libraries are single source of truth | ✅ |
| Tests contain no keyword definitions | ✅ |
| Keywords mirror pytest-bdd step_defs | ✅ |
| Clear traceability: requirements → scenarios → keywords → use_cases | ✅ |
| All existing tests pass | ✅ |
| Documentation updated | ✅ |
| No recursion issues from naming conflicts | ✅ |

---

## Migration Timeline

| Date | Milestone |
|------|-----------|
| January 2026 | Initial keyword libraries created |
| January 29, 2026 | UseCaseLibrary removed |
| February 4, 2026 | Test files refactored to remove local keywords |
| February 4, 2026 | Documentation updated, migration complete |
