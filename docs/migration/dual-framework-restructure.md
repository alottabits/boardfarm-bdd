# Dual Framework Restructure Plan

**Document**: `boardfarm-bdd/docs/dual_framework_restructure_plan.md`  
**Created**: January 29, 2026  
**Status**: Implementation Plan

---

## Executive Summary

This document outlines the implementation plan to restructure `boardfarm-bdd/` to support both **pytest-bdd** and **Robot Framework** test execution while sharing system use case definitions and maintaining a single Python virtual environment.

### Goals

1. Support pytest-bdd and Robot Framework in the same project
2. Share system use case definitions (`requirements/`) as single source of truth
3. Maintain consistent test behavior across frameworks (same `boardfarm3.use_cases`)
4. Enable independent CI/CD pipelines per framework
5. Minimize migration disruption for existing pytest-bdd tests

### Key Principles

1. **Libraries are the single source of truth** - All keywords defined in `robot/libraries/*.py`
2. **Tests contain no keyword definitions** - Test files call library keywords directly
3. **Libraries are thin wrappers** - Delegate to `boardfarm3.use_cases`
4. **Resource files for patterns only** - Setup/teardown and composite patterns, not duplicate keywords

---

## Current Structure

```
boardfarm-bdd/
├── .venv/                           # Virtual environment
├── conftest.py                      # pytest-bdd configuration
├── requirements/                    # System use case definitions
│   ├── UC-12347 remote cpe reboot.md
│   ├── UC-12348 User makes a one-way call.md
│   └── ...
├── tests/                           # All test artifacts (mixed)
│   ├── features/                    # Gherkin feature files
│   ├── step_defs/                   # Step definition implementations
│   ├── unit/                        # Unit tests
│   ├── ui_helpers/                  # UI testing helpers
│   └── test_*.py                    # Test runners
├── bf_config/                       # Testbed configuration
├── docs/                            # Documentation
├── raikou/                          # Docker testbed components
├── tools/                           # Development tools
└── pyproject.toml                   # Project configuration
```

---

## Target Structure

```
boardfarm-bdd/
├── .venv/                           # Single virtual environment (unchanged)
├── requirements/                    # SHARED - System use case definitions (unchanged)
│   ├── UC-12347 remote cpe reboot.md
│   ├── UC-12348 User makes a one-way call.md
│   ├── UC-ACS-GUI-01 ACS GUI Device Management.md
│   └── Device Class - RPi prplOS CPE.md
│
├── tests/                          # pytest-bdd implementation
│   ├── conftest.py                  # Moved from root
│   ├── pytest.ini                   # pytest configuration
│   ├── features/                    # Moved from tests/features/
│   │   ├── Remote CPE Reboot.feature
│   │   ├── UC-12348 User makes a one-way call.feature
│   │   ├── ACS GUI Device Management.feature
│   │   ├── Device Class Initialization.feature
│   │   └── hello.feature
│   ├── step_defs/                   # Moved from tests/step_defs/
│   │   ├── __init__.py
│   │   ├── acs_steps.py
│   │   ├── acs_gui_steps.py
│   │   ├── background_steps.py
│   │   ├── cpe_steps.py
│   │   ├── device_class_steps.py
│   │   ├── hello_steps.py
│   │   ├── operator_steps.py
│   │   └── sip_phone_steps.py
│   ├── unit/                        # Moved from tests/unit/
│   │   ├── mocks/
│   │   └── test_step_defs/
│   └── test_all_scenarios.py        # Moved from tests/
│
├── robot/                           # Robot Framework implementation (NEW)
│   ├── tests/                       # Robot test suites
│   │   ├── remote_cpe_reboot.robot
│   │   ├── user_makes_one_way_call.robot
│   │   ├── acs_gui_device_management.robot
│   │   ├── device_class_initialization.robot
│   │   └── hello.robot
│   ├── resources/                   # Shared Robot resources
│   │   ├── common.resource          # Common setup/teardown
│   │   ├── variables.resource       # Shared variables
│   │   └── cleanup.resource         # Cleanup keywords
│   └── robot.yaml                   # Robot configuration (pabot, etc.)
│
├── bf_config/                       # Testbed configuration (unchanged)
├── raikou/                          # Docker testbed (unchanged)
├── tools/                           # Development tools (unchanged)
│
├── docs/                            # Documentation (updated)
│   ├── use_case_architecture.md     # Existing
│   ├── dual_framework_restructure_plan.md  # This document
│   ├── tests/                      # pytest-bdd specific docs
│   │   ├── getting_started.md
│   │   └── step_definition_guide.md
│   ├── robot/                       # Robot Framework specific docs
│   │   ├── getting_started.md
│   │   └── keyword_reference.md
│   └── ...                          # Other existing docs
│
├── pyproject.toml                   # Updated with optional dependencies
└── README.md                        # Updated with dual-framework info
```

---

## Implementation Phases

### Phase 1: Create New Directory Structure (Day 1)

**Objective**: Create the target directory layout without moving files yet.

**Tasks**:

1.1. Create `tests/` directory structure:
```bash
mkdir -p tests/features
mkdir -p tests/step_defs
mkdir -p tests/unit/mocks
mkdir -p tests/unit/test_step_defs
```

1.2. Create `robot/` directory structure:
```bash
mkdir -p robot/tests
mkdir -p robot/resources
```

1.3. Create documentation directories:
```bash
mkdir -p docs/pytest
mkdir -p docs/robot
```

**Deliverables**:
- Empty directory structure ready for file migration

---

### Phase 2: Migrate pytest-bdd Files (Day 1-2)

**Objective**: Move existing pytest-bdd files to `tests/` directory.

**Tasks**:

2.1. Move feature files:
```bash
mv tests/features/*.feature tests/features/
mv tests/features/README_GUI_TESTS.md tests/features/
```

2.2. Move step definitions:
```bash
mv tests/step_defs/* tests/step_defs/
```

2.3. Move unit tests:
```bash
mv tests/unit/* tests/unit/
```

2.4. Move test runners:
```bash
mv tests/test_all_scenarios.py tests/
mv tests/test_hello.py tests/
```

2.5. Move conftest.py and update paths:
```bash
mv conftest.py tests/conftest.py
```

2.6. Update import paths in `tests/conftest.py`:
```python
# Before
step_defs_dir = Path(__file__).parent / "tests" / "step_defs"
module_path = f"tests.step_defs.{module_name}"

# After
step_defs_dir = Path(__file__).parent / "step_defs"
module_path = f"pytest.step_defs.{module_name}"
```

2.7. Create `tests/pytest.ini`:
```ini
[pytest]
testpaths = .
python_files = test_*.py
python_classes = Test*
python_functions = test_*
bdd_features_base_dir = features
addopts = -v --tb=short
```

2.8. Update step definition imports (if any absolute imports):
- Search for `from tests.` and update to `from pytest.`

**Deliverables**:
- All pytest-bdd files in `tests/` directory
- Updated import paths
- pytest.ini configuration

---

### Phase 3: Create Root conftest.py and pytest.ini (Day 2)

**Objective**: Enable running pytest from project root.

**Tasks**:

3.1. Create root `conftest.py` (minimal, delegates to tests/):
```python
"""Root conftest.py - delegates to tests/ directory."""

# Import pytest directory's conftest to make fixtures available
# when running from project root
import sys
from pathlib import Path

# Add pytest directory to path
pytest_dir = Path(__file__).parent / "pytest"
sys.path.insert(0, str(pytest_dir))

# Re-export fixtures from tests/conftest.py
from pytest.conftest import *  # noqa: F401, F403
```

3.2. Create root `pytest.ini`:
```ini
[pytest]
testpaths = pytest
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

**Deliverables**:
- Root conftest.py that delegates to tests/
- Root pytest.ini pointing to tests/ directory

---

### Phase 4: Update pyproject.toml (Day 2)

**Objective**: Configure optional dependencies for each framework.

**Tasks**:

4.1. Update `pyproject.toml`:
```toml
[project]
name = "boardfarm-bdd"
version = "0.1.0"
description = "BDD test suite for Boardfarm testbed"
requires-python = ">=3.11"

dependencies = [
    "boardfarm3>=1.0.0",
]

[project.optional-dependencies]
pytest = [
    "pytest>=7.0",
    "pytest-bdd>=6.0",
    "pytest-boardfarm3",
    "pytest-html",
]
robot = [
    "robotframework>=6.0",
    "robotframework-boardfarm>=0.1.0",
]
all = [
    "boardfarm-bdd[pytest,robot]",
]
dev = [
    "boardfarm-bdd[all]",
    "ruff>=0.4.0",
    "mypy",
    "pre-commit",
]

[tool.pytest.ini_options]
testpaths = ["pytest"]
python_files = ["test_*.py"]
bdd_features_base_dir = "tests/features"

[tool.ruff]
line-length = 88
target-version = "py311"
```

**Deliverables**:
- Updated pyproject.toml with framework-specific optional dependencies

---

### Phase 5: Create Robot Framework Test Suites (Day 3-4)

**Objective**: Implement Robot Framework test suites corresponding to existing feature files.

**Tasks**:

5.1. Create `robot/tests/remote_cpe_reboot.robot`:

**Important**: Tests call library keywords directly - NO local keyword definitions.

```robot
*** Settings ***
Documentation    UC-12347: Remote CPE Reboot
...              Remotely reboot the CPE device to restore connectivity,
...              apply configuration changes, or resolve operational issues.

Library     robotframework_boardfarm.BoardfarmLibrary
Library     ../libraries/boardfarm_keywords.py
Library     ../libraries/acs_keywords.py
Library     ../libraries/cpe_keywords.py
Library     ../libraries/background_keywords.py
Library     ../libraries/operator_keywords.py
Resource    ../resources/common.resource

Suite Setup       Setup Reboot Test Suite
Suite Teardown    Teardown Testbed Connection
Test Teardown     Cleanup After Reboot Test    ${ACS}    ${CPE}    ${ADMIN_USER_INDEX}

*** Variables ***
${TEST_PASSWORD}        p@ssw0rd123!
${ADMIN_USER_INDEX}     ${None}

*** Test Cases ***
UC-12347-Main: Successful Remote Reboot
    [Documentation]    Main success scenario for remote CPE reboot
    [Tags]    UC-12347    reboot    smoke

    # Background: Set CPE GUI password (call library keyword directly)
    ${password_result}=    Set CPE GUI Password    ${ACS}    ${CPE}    ${TEST_PASSWORD}
    Set Suite Variable    ${ADMIN_USER_INDEX}    ${password_result}[admin_user_index]

    # Main scenario: Call library keywords directly - no wrappers
    ${reboot_result}=    The Operator Initiates A Reboot Task On The ACS For The CPE    ${ACS}    ${CPE}
    ${reboot_timestamp}=    Set Variable    ${reboot_result}[test_start_timestamp]
    
    The ACS Sends A Connection Request To The CPE    ${ACS}    ${CPE}    since=${reboot_timestamp}
    The CPE Sends An Inform Message To The ACS    ${ACS}    ${CPE}    since=${reboot_timestamp}
    ${reboot_rpc_time}=    The ACS Responds To The Inform Message By Issuing The Reboot RPC    ${ACS}    ${CPE}    since=${reboot_timestamp}
    The CPE Sends An Inform Message After Boot Completion    ${ACS}    ${CPE}    since=${reboot_rpc_time}
    The CPE Resumes Normal Operation    ${ACS}    ${CPE}
    Use Case Succeeds And All Success Guarantees Are Met    ${ACS}    ${CPE}

*** Keywords ***
Setup Reboot Test Suite
    [Documentation]    Suite setup - get devices and verify CPE is online.
    ${acs}=    Get Device By Type    ACS
    ${cpe}=    Get Device By Type    CPE
    Set Suite Variable    ${ACS}    ${acs}
    Set Suite Variable    ${CPE}    ${cpe}
    ${baseline}=    A CPE Is Online And Fully Provisioned    ${ACS}    ${CPE}
    Set Suite Variable    ${INITIAL_UPTIME}    ${baseline}[initial_uptime]
```

**Note**: The test file has only ONE local keyword (suite setup) which initializes devices.
All test logic uses library keywords directly.

5.2. Create `robot/tests/user_makes_one_way_call.robot`:

**Important**: Tests call library keywords directly - NO local keyword definitions.

```robot
*** Settings ***
Documentation    UC-12348: User Makes a One-Way Call
...              Test SIP phone call establishment and teardown.

Library     robotframework_boardfarm.BoardfarmLibrary
Library     ../libraries/boardfarm_keywords.py
Library     ../libraries/voice_keywords.py
Resource    ../resources/common.resource
Resource    ../resources/voice.resource

Suite Setup       Setup Voice Test Environment
Suite Teardown    Teardown Voice Test Environment
Test Teardown     Cleanup SIP Phones After Test    ${CALLER}    ${CALLEE}

*** Variables ***
${CALL_TIMEOUT}    30

*** Test Cases ***
UC-12348-Main: Successful One-Way Call
    [Documentation]    User successfully makes a one-way voice call
    [Tags]    UC-12348    voice    call

    # Setup: Call library keywords directly - no local wrappers
    Register Phone On LAN Side    ${LAN_PHONE}    1000
    Register Phone On WAN Side    ${WAN_PHONE}    2000
    Set Caller And Callee    ${LAN_PHONE}    ${WAN_PHONE}

    # Action: Call library keywords directly
    Caller Calls Callee

    # Verification: Call library keywords directly
    The Callee Phone Should Start Ringing
    Callee Answers Call
    Both Phones Should Be Connected
    A Bidirectional RTP Media Session Should Be Established

    # Cleanup
    Caller Hangs Up
    Verify SIP Call Terminated
    Both Phones Should Return To Idle State
```

**Note**: The test file has ZERO local keyword definitions.
All keywords come from `voice_keywords.py` library or `voice.resource` patterns.

5.3. Create `robot/tests/hello.robot` (smoke test):

**Important**: Tests call library keywords directly - NO local keyword definitions.

```robot
*** Settings ***
Documentation    Basic smoke test to verify testbed connectivity.

Library     robotframework_boardfarm.BoardfarmLibrary
Library     ../libraries/boardfarm_keywords.py
Library     ../libraries/acs_keywords.py

*** Test Cases ***
Verify Testbed Connectivity
    [Documentation]    Verify basic testbed connectivity
    [Tags]    smoke    connectivity

    # Call library keywords directly
    ${acs}=    Get Device By Type    ACS
    ${cpe}=    Get Device By Type    CPE
    Should Not Be Equal    ${acs}    ${None}
    Should Not Be Equal    ${cpe}    ${None}
    Log    ACS: ${acs}
    Log    CPE: ${cpe}

Verify CPE Is Online
    [Documentation]    Verify CPE is online via ACS
    [Tags]    smoke    cpe

    # Call library keywords directly
    ${acs}=    Get Device By Type    ACS
    ${cpe}=    Get Device By Type    CPE
    The CPE Is Online Via ACS    ${acs}    ${cpe}
```

**Note**: The test file has ZERO local keyword definitions.
All keywords come from libraries.

5.4. Create additional test files for other features (similar pattern).

**Deliverables**:
- Robot test suites corresponding to existing feature files
- Keyword implementations using UseCaseLibrary

---

### Phase 6: Create Robot Framework Resources (Day 4)

**Objective**: Create shared Robot Framework resource files.

**Important**: Resource files should only contain:
- Suite setup/teardown patterns
- Composite keywords that combine multiple library calls
- Test cleanup patterns

Resource files should **NOT**:
- Duplicate or wrap library keywords with the same name (causes recursion)
- Contain business logic (that belongs in libraries/use_cases)

**Tasks**:

6.1. Create `robot/resources/common.resource`:
```robot
*** Settings ***
Documentation    Common keywords and setup for all Robot tests.

Library     BoardfarmLibrary
Library     UseCaseLibrary

*** Keywords ***
Setup Testbed Connection
    [Documentation]    Common suite setup - verify testbed connectivity
    Log    Setting up testbed connection...
    ${acs}=    Get Device By Type    ACS
    ${cpe}=    Get Device By Type    CPE
    Set Suite Variable    ${ACS}
    Set Suite Variable    ${CPE}
    Log    Testbed connection established

Teardown Testbed Connection
    [Documentation]    Common suite teardown
    Log    Tearing down testbed connection...

Cleanup After Test
    [Documentation]    Common test teardown - cleanup any test artifacts
    Log    Cleaning up after test...
    Run Keyword And Ignore Error    Refresh CPE Console Connection
```

6.2. Create `robot/resources/variables.resource`:
```robot
*** Variables ***
# Default test values
${DEFAULT_CPE_PASSWORD}     admin
${TEST_PASSWORD}            p@ssw0rd123!
${DEFAULT_TIMEOUT}          30
${REBOOT_TIMEOUT}           240

# TR-069 parameters
${PARAM_SOFTWARE_VERSION}   Device.DeviceInfo.SoftwareVersion
${PARAM_MANUFACTURER}       Device.DeviceInfo.Manufacturer
${PARAM_USER_PASSWORD}      Device.Users.User.1.Password
```

6.3. Create `robot/resources/cleanup.resource`:
```robot
*** Settings ***
Documentation    Cleanup keywords for test teardown.

Library     BoardfarmLibrary
Library     UseCaseLibrary

*** Keywords ***
Cleanup CPE Configuration
    [Documentation]    Restore CPE configuration to original state
    [Arguments]    ${original_config}
    Log    Restoring CPE configuration...
    # Implementation depends on what was captured

Cleanup SIP Phones
    [Documentation]    Clean up all SIP phones in testbed
    Log    Cleaning up SIP phones...
    # Iterate through phones and cleanup

Refresh CPE Console Connection
    [Documentation]    Refresh CPE console connection after reboot
    ${cpe}=    Get Device By Type    CPE
    Cpe Refresh Console Connection    ${cpe}
```

6.4. Create `robot/robot.yaml` (optional, for pabot/robot configuration):
```yaml
# Robot Framework configuration
# Used by pabot for parallel execution

# Parallel execution settings
processes: 2

# Output settings  
outputdir: results
log: log.html
report: report.html

# Default listener
listener: robotframework_boardfarm.BoardfarmListener
```

**Deliverables**:
- Shared resource files for Robot Framework tests
- Common keywords for setup/teardown

---

### Phase 7: ~~Create Shared Test Data~~ (CANCELLED)

**Status**: CANCELLED

**Rationale**: After review, this phase was determined to violate the 4-layer 
architecture principle. Hardcoding device-specific data (TR-069 parameters, 
SIP configurations, etc.) contradicts boardfarm's core concept of abstracting 
device-specific details.

**Key Insights**:
- TR-069 parameter paths vary by CPE vendor/model (prplOS vs RDK vs vendor X)
- ACS configurations differ between implementations (GenieACS vs Axiros)
- SIP/voice configurations depend on testbed setup
- Tests should get device-specific data from device classes at runtime

**Correct Approach**:
- Tests call `boardfarm3.use_cases` functions
- Use cases work with device interfaces
- Device classes know their own data models and configurations
- No shared test data files needed - each integration layer provides what's needed

**The `shared/` directory is NOT implemented.**

---

### Phase 8: Update Documentation (Day 5)

**Objective**: Create framework-specific documentation and update existing docs.

**Tasks**:

8.1. Create `docs/tests/getting_started.md`:
```markdown
# pytest-bdd Getting Started

## Installation

```bash
pip install -e ".[pytest]"
```

## Running Tests

```bash
# From project root
pytest tests/features/ \
    --board-name=prplos-docker-1 \
    --env-config=bf_config/boardfarm_env_example.json \
    --inventory-config=bf_config/boardfarm_config_example.json

# Run specific feature
pytest tests/features/Remote\ CPE\ Reboot.feature
```

## Writing Tests

See `step_migration_guide.md` for step definition patterns.
```

8.2. Create `docs/robot/getting_started.md`:
```markdown
# Robot Framework Getting Started

## Installation

```bash
pip install -e ".[robot]"
```

## Running Tests

```bash
# From project root
robot --listener "robotframework_boardfarm.BoardfarmListener:\
board_name=prplos-docker-1:\
env_config=bf_config/boardfarm_env_example.json:\
inventory_config=bf_config/boardfarm_config_example.json" \
    robot/tests/

# Run specific test
robot --listener ... robot/tests/remote_cpe_reboot.robot
```

## Writing Tests

1. Create test file in `robot/tests/`
2. Import `BoardfarmLibrary` and `UseCaseLibrary`
3. Use keywords like `Acs Get Parameter Value`, `Cpe Get Cpu Usage`
```

8.3. Create `docs/robot/keyword_reference.md`:
```markdown
# Robot Framework Keyword Reference

## BoardfarmLibrary Keywords

| Keyword | Description |
|---------|-------------|
| `Get Device By Type` | Get device instance by type string |
| `Get Boardfarm Config` | Get testbed configuration |
| `Log Step` | Log a test step |

## UseCaseLibrary Keywords (from boardfarm3.use_cases)

### ACS Keywords
| Keyword | Source | Description |
|---------|--------|-------------|
| `Acs Get Parameter Value` | `acs.get_parameter_value()` | Get TR-069 parameter |
| `Acs Set Parameter Value` | `acs.set_parameter_value()` | Set TR-069 parameter |
| `Acs Initiate Reboot` | `acs.initiate_reboot()` | Initiate CPE reboot |
| `Acs Is Cpe Online` | `acs.is_cpe_online()` | Check CPE online status |

### CPE Keywords
| Keyword | Source | Description |
|---------|--------|-------------|
| `Cpe Get Cpu Usage` | `cpe.get_cpu_usage()` | Get CPU usage |
| `Cpe Get Seconds Uptime` | `cpe.get_seconds_uptime()` | Get uptime |
| `Cpe Factory Reset` | `cpe.factory_reset()` | Factory reset CPE |

### Voice Keywords
| Keyword | Source | Description |
|---------|--------|-------------|
| `Voice Call A Phone` | `voice.call_a_phone()` | Initiate call |
| `Voice Answer A Call` | `voice.answer_a_call()` | Answer incoming call |
| `Voice Disconnect The Call` | `voice.disconnect_the_call()` | Hang up |
```

8.4. Update `README.md` with dual-framework information.

8.5. Update `docs/use_case_architecture.md` to reference both frameworks.

**Deliverables**:
- Framework-specific getting started guides
- Keyword reference for Robot Framework
- Updated project README

---

### Phase 9: Update CI/CD Configuration (Day 5-6)

**Objective**: Configure CI/CD for both frameworks.

**Tasks**:

9.1. Create/update `.github/workflows/pytest.yml`:
```yaml
name: pytest-bdd Tests

on:
  push:
    paths:
      - 'tests/**'
      - 'requirements/**'
  pull_request:
    paths:
      - 'tests/**'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -e ".[pytest]"
      - name: Run pytest-bdd tests
        run: pytest tests/features/ --tb=short
```

9.2. Create `.github/workflows/robot.yml`:
```yaml
name: Robot Framework Tests

on:
  push:
    paths:
      - 'robot/**'
      - 'requirements/**'
  pull_request:
    paths:
      - 'robot/**'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -e ".[robot]"
      - name: Run Robot Framework tests
        run: |
          robot --listener robotframework_boardfarm.BoardfarmListener:... \
            robot/tests/
```

**Deliverables**:
- Separate CI workflows for each framework
- Path-based triggering for efficient CI runs

---

### Phase 10: Validation and Cleanup (Day 6-7)

**Objective**: Validate the restructure and clean up old artifacts.

**Tasks**:

10.1. Validate pytest-bdd tests run from new location:
```bash
pytest tests/features/ -v
```

10.2. Validate Robot Framework tests run:
```bash
robot robot/tests/hello.robot
```

10.3. Validate imports and paths work correctly.

10.4. Remove old `tests/` directory (after confirming everything works):
```bash
rm -rf tests/
```

10.5. Update any remaining references to old paths.

10.6. Run full test suite for both frameworks.

**Deliverables**:
- Validated test execution for both frameworks
- Clean project structure without legacy artifacts

---

## Migration Summary

| Source | Destination |
|--------|-------------|
| `conftest.py` | `tests/conftest.py` |
| `tests/features/` | `tests/features/` |
| `tests/step_defs/` | `tests/step_defs/` |
| `tests/unit/` | `tests/unit/` |
| `tests/test_*.py` | `tests/test_*.py` |
| `tests/ui_helpers/` | `tests/ui_helpers/` |
| (new) | `robot/tests/` |
| (new) | `robot/resources/` |

---

## Timeline

| Phase | Description | Duration | Dependencies |
|-------|-------------|----------|--------------|
| 1 | Create directory structure | 0.5 day | None |
| 2 | Migrate pytest-bdd files | 1 day | Phase 1 |
| 3 | Create root conftest.py | 0.5 day | Phase 2 |
| 4 | Update pyproject.toml | 0.5 day | Phase 1 |
| 5 | Create Robot test suites | 2 days | Phase 1 |
| 6 | Create Robot resources | 0.5 day | Phase 5 |
| 7 | ~~Create shared test data~~ | CANCELLED | - |
| 8 | Update documentation | 1 day | Phases 2, 5 |
| 9 | Update CI/CD | 0.5 day | Phases 2, 5 |
| 10 | Validation and cleanup | 1 day | All phases |

**Total Estimated Duration**: 7-8 days

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Broken imports after move | Update paths incrementally, validate at each step |
| CI/CD disruption | Keep old paths working until new structure validated |
| Missing test coverage | Run both old and new tests during transition |
| Documentation gaps | Update docs as part of each phase |

---

## Success Criteria

1. ✅ All existing pytest-bdd tests pass from new location
2. ✅ Robot Framework tests execute successfully
3. ✅ Both frameworks use same `boardfarm3.use_cases`
4. ✅ Shared test data accessible from both frameworks
5. ✅ CI/CD pipelines work for both frameworks
6. ✅ Documentation covers both frameworks
7. ✅ Single venv supports both frameworks

---

## Appendix: File Mapping

### Feature → Robot Test Mapping

| Requirement | pytest-bdd Feature | Robot Test |
|-------------|-------------------|------------|
| UC-12347 remote cpe reboot.md | Remote CPE Reboot.feature | remote_cpe_reboot.robot |
| UC-12348 User makes a one-way call.md | UC-12348 User makes a one-way call.feature | user_makes_one_way_call.robot |
| UC-ACS-GUI-01 ACS GUI Device Management.md | ACS GUI Device Management.feature | acs_gui_device_management.robot |
| Device Class - RPi prplOS CPE.md | Device Class Initialization.feature | device_class_initialization.robot |

---

**Document Version**: 1.0  
**Last Updated**: January 29, 2026
