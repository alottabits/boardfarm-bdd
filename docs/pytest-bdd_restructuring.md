# pytest-bdd Step Definition Restructuring Plan

**Project**: boardfarm-bdd  
**Goal**: Align pytest-bdd step definitions with Boardfarm use_cases for framework portability  
**Related**: robotframework-boardfarm/DEVELOPMENT_PLAN.md  
**Created**: January 26, 2026  
**Status**: Draft - Pending Review

---

## Executive Summary

This plan outlines the restructuring of pytest-bdd step definitions in `boardfarm-bdd` to leverage the `boardfarm3.use_cases` module as the primary abstraction layer. This alignment ensures:

1. **Portability**: Same test operations work across pytest-bdd and Robot Framework
2. **Single Source of Truth**: Test logic lives in Boardfarm use_cases, not integration layers
3. **Maintainability**: Fix once in use_cases, benefit everywhere
4. **Consistency**: Standardized deprecation handling via `debtcollector`

---

## Current State Analysis

### Step Definition Files

| File | Lines | Direct Device Calls | Helper Functions | Use Case Calls |
|------|-------|---------------------|------------------|----------------|
| `cpe_steps.py` | 830 | High | Yes (`helpers.py`) | None |
| `acs_steps.py` | 408 | High | Yes (`helpers.py`) | None |
| `sip_phone_steps.py` | 1316 | High | Yes (embedded) | None |
| `operator_steps.py` | 80 | Medium | Minimal | None |
| `helpers.py` | 317 | N/A (utility) | N/A | N/A |
| `background_steps.py` | TBD | TBD | TBD | None |
| `acs_gui_steps.py` | TBD | TBD | TBD | None |

### Current Patterns (Anti-Patterns)

**1. Direct Device Method Calls in Steps**

```python
# Current: cpe_steps.py
def get_console_uptime_seconds(cpe: CpeTemplate) -> int:
    try:
        return int(cpe.sw.get_seconds_uptime())  # Direct device call
    except Exception:
        out = cpe.hw.get_console("console").execute_command("cut -d' ' -f1 /proc/uptime")
        return int(float(out.strip() or "0"))
```

**2. Helper Functions with Device Logic**

```python
# Current: helpers.py
def gpv_value(acs: AcsTemplate, cpe: CpeTemplate, param: str, retries: int = 6) -> str:
    def _fn() -> str | None:
        res = acs.GPV(param, cpe_id=cpe.sw.cpe_id)  # Direct device call
        # ... business logic
    out = retry(_fn, retries)
    # ...
```

**3. Complex Business Logic in Steps**

```python
# Current: cpe_steps.py - 200+ lines of log parsing logic
def cpe_sends_inform_after_boot_completion(...):
    # Polls GenieACS logs
    # Parses timestamps
    # Filters by CPE ID
    # Compares chronologically
    # All embedded in step definition
```

**4. Voice Steps Bypass use_cases**

```python
# Current: sip_phone_steps.py
def phone_dials_number(caller_role: str, callee_role: str, bf_context: Any) -> None:
    caller.dial(callee_number)  # Direct device call
    # Should use: voice.call_a_phone(caller, callee)
```

### Available use_cases (boardfarm3/use_cases/)

| Module | Functions | Coverage |
|--------|-----------|----------|
| `cpe.py` | 18 functions | CPE performance, factory reset, tcpdump, uptime, NTP |
| `networking.py` | 35 functions | ping, HTTP, DNS, TCP/UDP sessions, firewall |
| `voice.py` | 50+ functions | Call setup, answer, disconnect, hold, forward |
| `device_getters.py` | Device access utilities | Limited |
| `device_utilities.py` | Utility functions | Limited |
| `dhcp.py` | DHCP operations | DHCP release/renew |
| `iperf.py` | Performance testing | iperf client/server |
| `wifi.py` | WiFi operations | WiFi configuration |

### Gap Analysis

**Operations in Step Definitions NOT in use_cases:**

| Operation | Current Location | Proposed use_case Module |
|-----------|------------------|--------------------------|
| GPV/SPV via ACS | `helpers.py`, `acs_steps.py` | `acs.py` (NEW) |
| ACS log polling | `cpe_steps.py`, `acs_steps.py` | `acs.py` (NEW) |
| CPE online check | `background_steps.py` | `cpe.py` (EXTEND) |
| Reboot via ACS | `operator_steps.py` | `acs.py` (NEW) |
| Console reconnection | `cpe_steps.py` | `cpe.py` (EXTEND) |
| Config preservation check | `cpe_steps.py` | `cpe.py` (EXTEND) |
| TR-069 client control | `cpe_steps.py` | `cpe.py` (EXTEND) |

---

## Target Architecture

### Abstraction Layers (Aligned with robotframework-boardfarm)

```
┌─────────────────────────────────────────────────────────────────────┐
│ Layer 1: Test Definition                                            │
│   pytest-bdd: @given/@when/@then steps                              │
│   Robot Framework: Keywords                                         │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────┐
│ Layer 2: Integration Layer (THIN WRAPPER)                           │
│   pytest-bdd: Step functions call use_cases                         │
│   Robot Framework: UseCaseLibrary wraps use_cases                   │
│   NO business logic - parameter passing only                        │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────┐
│ Layer 3: Boardfarm use_cases (boardfarm3/use_cases/*.py)            │
│   SINGLE SOURCE OF TRUTH                                            │
│   High-level test operations with business logic                    │
│   Documented with test statement hints                              │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────┐
│ Layer 4: Device Templates (boardfarm3/templates/*.py)               │
│   Low-level device operations                                       │
│   Protocol-specific implementations                                 │
└─────────────────────────────────────────────────────────────────────┘
```

### Target Step Definition Pattern

**BEFORE (Current - Anti-Pattern):**

```python
@then("the CPE executes the reboot command and restarts")
def cpe_executes_reboot_and_restarts(acs, cpe, bf_context):
    cpe_id = bf_context.reboot_cpe_id
    
    # Direct device calls and embedded business logic
    max_attempts = 30
    for _attempt in range(max_attempts):
        try:
            console = cpe.hw.get_console("console")
            console.execute_command("echo test", timeout=2)
            time.sleep(1)
        except Exception:
            # ... 50+ more lines of logic
```

**AFTER (Target - Use Case Pattern):**

```python
from boardfarm3.use_cases import cpe as cpe_use_cases

@then("the CPE executes the reboot command and restarts")
def cpe_executes_reboot_and_restarts(acs, cpe, bf_context):
    """CPE executes reboot and restarts - delegates to use_case."""
    cpe_id = bf_context.reboot_cpe_id
    
    # Single use_case call - all logic encapsulated
    cpe_use_cases.wait_for_reboot_completion(cpe, timeout=60)
    
    print(f"✓ CPE {cpe_id} reboot completed")
```

---

## Interface Handling in use_cases

### Background: Device Interface Architecture

Boardfarm device classes expose multiple interfaces for interacting with devices:

**ACS Device:**
- `acs.nbi` - Northbound Interface (REST API for TR-069)
- `acs.gui` - GUI interface (web browser operations)
- `acs.console` - Console access (SSH to ACS server)

**CPE Device:**
- `cpe.sw` - Software layer (OS services, applications)
- `cpe.hw` - Hardware layer (console/serial access)
- (future) `cpe.gui` - GUI interface (LuCI web interface)

### Design Decision: Parameter-Based Interface Selection

For use_cases where multiple interfaces can perform the same operation, we use a **`via` parameter with a sensible default**:

```python
from typing import Literal

InterfaceType = Literal["nbi", "gui"]

def reboot_device(
    acs: ACS, 
    cpe: CPE, 
    via: InterfaceType = "nbi"
) -> bool:
    """Reboot device via ACS.
    
    :param via: Interface to use ("nbi" for API, "gui" for web interface)
    """
    if via == "gui":
        return acs.gui.reboot_device_via_gui(cpe.sw.cpe_id)
    return acs.nbi.Reboot(cpe_id=cpe.sw.cpe_id)
```

### Why This Approach?

1. **Single function per operation** - Less API surface, easier to maintain
2. **Consistent pattern** - Same approach everywhere, predictable
3. **Default covers 90% of cases** - Most tests don't care about the interface
4. **Override when needed** - Tests that DO care about interface just pass `via="gui"`
5. **No code duplication** - Implementation logic is in one place

### When NOT to Use `via` Parameter

Operations that only work on one interface don't need a `via` parameter:

```python
def wait_for_inform_in_logs(acs: ACS, cpe_id: str, timeout: int = 120) -> bool:
    """Wait for Inform message in ACS CWMP logs.
    
    This operation uses console access (no alternative interface).
    """
    # Always uses acs.console - no via parameter needed
    ...
```

### Framework Integration

This approach integrates cleanly with both pytest-bdd and Robot Framework:

**pytest-bdd:**
```python
@when("the operator reboots the CPE via ACS")
def operator_reboots_cpe(acs, cpe):
    acs_use_cases.reboot_device(acs, cpe)  # uses default via="nbi"

@when("the operator reboots the CPE via ACS GUI")
def operator_reboots_cpe_via_gui(acs, cpe):
    acs_use_cases.reboot_device(acs, cpe, via="gui")
```

**Robot Framework:**
```robotframework
*** Test Cases ***
Reboot Via NBI
    Acs Reboot Device    ${acs}    ${cpe}
    # via defaults to "nbi"

Reboot Via GUI
    Acs Reboot Device    ${acs}    ${cpe}    via=gui
```

Robot Framework handles optional keyword arguments natively, so this works without any special handling in the `UseCaseLibrary`.

### Interface Selection Guidelines

| Scenario | Recommendation |
|----------|----------------|
| Testing a specific interface (e.g., GUI works) | Explicitly pass `via="gui"` |
| Testing business logic (e.g., reboot works) | Use default (typically NBI) |
| Operation only on one interface | No `via` parameter |
| Performance-critical paths | Use NBI (faster than GUI) |

---

## Implementation Plan

### Phase 1: Create New use_cases (Priority: HIGH)

**Objective**: Create missing use_case functions to cover current step definition operations.

#### 1.1 Create `boardfarm3/use_cases/acs.py` (NEW)

```python
"""ACS (Auto Configuration Server) use cases.

Provides high-level operations for ACS interactions including:
- Parameter get/set via TR-069
- Reboot task management
- Log monitoring and polling
- Connection request handling

Interface Selection:
    Many functions support a `via` parameter to select the interface:
    - "nbi" (default): Use NBI/REST API (faster, programmatic)
    - "gui": Use web GUI (tests GUI functionality)
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Literal
from datetime import datetime

if TYPE_CHECKING:
    from boardfarm3.templates.acs import ACS
    from boardfarm3.templates.cpe import CPE

# Type alias for interface selection
InterfaceType = Literal["nbi", "gui"]


def get_parameter_value(
    acs: ACS,
    cpe: CPE,
    parameter: str,
    timeout: int = 30,
    retries: int = 6,
    via: InterfaceType = "nbi",
) -> str:
    """Get TR-069 parameter value via ACS.
    
    .. hint:: This Use Case implements statements from the test suite such as:
    
        - Get the value of a TR-069 parameter via ACS
        - Verify CPE parameter value
    
    :param acs: ACS device instance
    :param cpe: CPE device instance  
    :param parameter: TR-069 parameter path
    :param timeout: Operation timeout in seconds
    :param retries: Number of retry attempts
    :param via: Interface to use ("nbi" for API, "gui" for web interface)
    :return: Parameter value as string
    :raises AssertionError: If parameter cannot be retrieved
    """
    if via == "gui":
        return acs.gui.get_device_parameter_via_gui(cpe.sw.cpe_id, parameter)
    # Default: NBI with retry logic
    ...


def set_parameter_value(
    acs: ACS,
    cpe: CPE,
    parameter: str,
    value: str,
    timeout: int = 30,
    via: InterfaceType = "nbi",
) -> bool:
    """Set TR-069 parameter value via ACS.
    
    .. hint:: This Use Case implements statements from the test suite such as:
    
        - Set the value of a TR-069 parameter via ACS
        - Configure CPE parameter
    
    :param acs: ACS device instance
    :param cpe: CPE device instance
    :param parameter: TR-069 parameter path
    :param value: Value to set
    :param timeout: Operation timeout in seconds
    :param via: Interface to use ("nbi" for API, "gui" for web interface)
    :return: True if successful
    """
    if via == "gui":
        return acs.gui.set_device_parameter_via_gui(cpe.sw.cpe_id, parameter, value)
    # Default: NBI
    return acs.nbi.SPV({parameter: value}, timeout, cpe.sw.cpe_id)


def initiate_reboot(
    acs: ACS,
    cpe: CPE,
    command_key: str = "reboot",
    conn_request: bool = True,
    via: InterfaceType = "nbi",
) -> None:
    """Initiate CPE reboot via ACS.
    
    .. hint:: This Use Case implements statements from the test suite such as:
    
        - The operator initiates a reboot task on the ACS for the CPE
        - Reboot the CPE via TR-069
    
    :param acs: ACS device instance
    :param cpe: CPE device instance
    :param command_key: Command key for the reboot task
    :param conn_request: Whether to trigger connection request
    :param via: Interface to use ("nbi" for API, "gui" for web interface)
    """
    if via == "gui":
        acs.gui.reboot_device_via_gui(cpe.sw.cpe_id)
        return
    # Default: NBI
    acs.nbi.Reboot(CommandKey=command_key, cpe_id=cpe.sw.cpe_id)


def wait_for_inform_message(
    acs: ACS,
    cpe_id: str,
    event_codes: list[str] | None = None,
    since: datetime | None = None,
    timeout: int = 120,
) -> bool:
    """Wait for Inform message from CPE in ACS logs.
    
    .. hint:: This Use Case implements statements from the test suite such as:
    
        - The CPE sends an Inform message to the ACS
        - Wait for post-reboot Inform with "1 BOOT,M Reboot" events
    
    :param acs: ACS device instance
    :param cpe_id: CPE identifier
    :param event_codes: Expected event codes (e.g., ["1 BOOT", "M Reboot"])
    :param since: Only consider logs after this timestamp
    :param timeout: Maximum wait time in seconds
    :return: True if Inform found
    """
    ...


def wait_for_reboot_rpc(
    acs: ACS,
    cpe_id: str,
    since: datetime | None = None,
    timeout: int = 90,
) -> datetime | None:
    """Wait for Reboot RPC in ACS CWMP logs.
    
    .. hint:: This Use Case implements statements from the test suite such as:
    
        - The ACS responds to the Inform message by issuing the Reboot RPC
        - Verify ACS sent Reboot RPC to CPE
    
    :param acs: ACS device instance
    :param cpe_id: CPE identifier
    :param since: Only consider logs after this timestamp
    :param timeout: Maximum wait time in seconds
    :return: Timestamp when Reboot RPC was sent, or None if not found
    """
    ...


def is_cpe_online(acs: ACS, cpe: CPE, timeout: int = 30) -> bool:
    """Check if CPE is online and responding via ACS.
    
    .. hint:: This Use Case implements statements from the test suite such as:
    
        - Verify CPE is online and reachable via ACS
        - The CPE is online
    
    :param acs: ACS device instance
    :param cpe: CPE device instance
    :param timeout: Query timeout in seconds
    :return: True if CPE responds
    """
    ...
```

#### 1.2 Extend `boardfarm3/use_cases/cpe.py`

Add these functions to existing `cpe.py`:

```python
def wait_for_reboot_completion(
    board: CPE,
    timeout: int = 60,
) -> bool:
    """Wait for CPE to complete reboot process.
    
    .. hint:: This Use Case implements statements from the test suite such as:
    
        - The CPE executes the reboot command and restarts
        - Wait for CPE to become unresponsive then responsive
    
    :param board: CPE device instance
    :param timeout: Maximum wait time in seconds
    :return: True if reboot completed successfully
    """
    ...


def stop_tr069_client(board: CPE) -> None:
    """Stop TR-069 client on CPE (make unreachable for TR-069).
    
    .. hint:: This Use Case implements statements from the test suite such as:
    
        - The CPE is unreachable for TR-069 sessions
        - Stop the TR-069 agent
    
    :param board: CPE device instance
    """
    ...


def start_tr069_client(board: CPE) -> None:
    """Start TR-069 client on CPE (make reachable for TR-069).
    
    .. hint:: This Use Case implements statements from the test suite such as:
    
        - When the CPE comes online, it connects to the ACS
        - Start the TR-069 agent
    
    :param board: CPE device instance
    """
    ...


def refresh_console_connection(board: CPE) -> bool:
    """Refresh CPE console connection after reboot.
    
    .. hint:: This Use Case implements statements from the test suite such as:
    
        - Reconnect to CPE console after reboot
        - Refresh console connection
    
    :param board: CPE device instance
    :return: True if reconnection successful
    """
    ...


def verify_config_preservation(
    board: CPE,
    acs: "ACS",
    config_before: dict,
) -> list[str]:
    """Verify CPE configuration preserved after reboot.
    
    .. hint:: This Use Case implements statements from the test suite such as:
    
        - The CPE's configuration and operational state are preserved after reboot
        - Verify config parameters match pre-reboot values
    
    :param board: CPE device instance
    :param acs: ACS device instance
    :param config_before: Configuration captured before reboot
    :return: List of verification errors (empty if all preserved)
    """
    ...
```

#### 1.3 Create Utility use_cases

Consider a `boardfarm3/use_cases/log_utils.py` for log parsing utilities shared across ACS operations.

### Phase 2: Refactor Step Definitions (Priority: HIGH)

**Objective**: Convert step definitions to thin wrappers around use_cases.

#### 2.1 Refactoring Order (by Impact)

1. **`cpe_steps.py`** - Highest complexity, most direct device calls
2. **`acs_steps.py`** - Core ACS operations
3. **`operator_steps.py`** - Reboot orchestration
4. **`sip_phone_steps.py`** - Voice operations (use_cases already exist)
5. **`background_steps.py`** - Setup/teardown operations
6. **`acs_gui_steps.py`** - GUI operations (may need new use_cases)

#### 2.2 Refactoring Template

For each step definition:

1. **Identify the test operation** being performed
2. **Find or create** the corresponding use_case function
3. **Replace** direct device calls with use_case calls
4. **Keep** only:
   - Fixture access (e.g., `bf_context.reboot_cpe_id`)
   - Assertions (e.g., `assert result, "Error message"`)
   - Logging (e.g., `print("✓ Step completed")`)

#### 2.3 Example Refactoring: `cpe_steps.py`

**Before:**

```python
@then("the CPE sends an Inform message to the ACS")
def cpe_sends_inform_message(acs, cpe, bf_context):
    cpe_id = bf_context.reboot_cpe_id
    max_attempts = 30
    
    for _attempt in range(max_attempts):
        try:
            acs_console = acs.console
            logs = acs_console.execute_command(
                "tail -n 300 /var/log/genieacs/genieacs-cwmp-access.log | grep -i inform",
                timeout=10,
            )
            log_lines = [line for line in logs.split("\n") if line.strip()]
            start_timestamp = getattr(bf_context, "test_start_timestamp", None)
            filtered_lines = filter_logs_by_timestamp(log_lines, start_timestamp)
            filtered_lines = filter_logs_by_cpe_id(filtered_lines, cpe_id)
            # ... 50+ more lines
```

**After:**

```python
from boardfarm3.use_cases import acs as acs_use_cases

@then("the CPE sends an Inform message to the ACS")
def cpe_sends_inform_message(acs, cpe, bf_context):
    """CPE sends Inform message - delegates to use_case."""
    cpe_id = bf_context.reboot_cpe_id
    since = getattr(bf_context, "test_start_timestamp", None)
    
    found = acs_use_cases.wait_for_inform_message(
        acs, cpe_id, since=since, timeout=30
    )
    
    assert found, f"CPE {cpe_id} did not send Inform message within expected time"
    print(f"✓ CPE {cpe_id} sent Inform message")
```

#### 2.4 Voice Steps Refactoring

Voice use_cases already exist in `boardfarm3/use_cases/voice.py`. Refactor:

**Before:**

```python
@when('the {caller_role} dials the {callee_role}\'s number')
def phone_dials_number(caller_role, callee_role, bf_context):
    caller = get_phone_by_role(bf_context, caller_role)
    callee = get_phone_by_role(bf_context, callee_role)
    caller.dial(callee.number)  # Direct device call
```

**After:**

```python
from boardfarm3.use_cases import voice as voice_use_cases

@when('the {caller_role} dials the {callee_role}\'s number')
def phone_dials_number(caller_role, callee_role, bf_context):
    """Caller dials callee - delegates to use_case."""
    caller = get_phone_by_role(bf_context, caller_role)
    callee = get_phone_by_role(bf_context, callee_role)
    
    voice_use_cases.call_a_phone(caller, callee)
    
    print(f"✓ {caller.name} dialed {callee.number}")
```

### Phase 3: Deprecation Handling (Priority: MEDIUM)

**Objective**: Implement consistent deprecation handling using `debtcollector`.

#### 3.1 Add debtcollector to Boardfarm

Update `boardfarm/pyproject.toml`:

```toml
[project]
dependencies = [
    "debtcollector>=3.0.0",
    # ... existing deps
]
```

#### 3.2 Deprecation Patterns

**Pattern 1: Function Renamed**

```python
from debtcollector import moves

def get_cpu_usage(board: CPE) -> float:
    """Return the current CPU usage of CPE."""
    return board.sw.get_load_avg()

# Old name, now deprecated
get_cpu_load = moves.moved_function(
    get_cpu_usage,
    'get_cpu_load',
    __name__,
    message="Use get_cpu_usage instead"
)
```

**Pattern 2: Function Removed**

```python
from debtcollector import removals

@removals.remove(message="Use acs.wait_for_inform_message instead", removal_version="2.0")
def poll_acs_logs_for_inform(acs, cpe_id, timeout):
    """Deprecated: Use acs.wait_for_inform_message instead."""
    return acs_use_cases.wait_for_inform_message(acs, cpe_id, timeout=timeout)
```

**Pattern 3: Argument Renamed**

```python
from debtcollector import renames

@renames.renamed_kwarg('ping_ip', 'target_ip', version="1.5")
def ping(device, target_ip: str, ping_count: int = 4) -> bool:
    """Ping remote host IP."""
    return device.ping(target_ip, ping_count)
```

#### 3.3 Deprecation of helpers.py Functions

The functions in `helpers.py` should be deprecated as they're replaced by use_cases:

```python
# helpers.py - Add deprecation warnings
from debtcollector import removals

@removals.remove(
    message="Use boardfarm3.use_cases.acs.get_parameter_value instead",
    removal_version="2.0"
)
def gpv_value(acs, cpe, param, retries=6):
    """DEPRECATED: Use acs.get_parameter_value instead."""
    from boardfarm3.use_cases import acs as acs_use_cases
    return acs_use_cases.get_parameter_value(acs, cpe, param, retries=retries)
```

### Phase 4: Validation (Priority: HIGH)

**Objective**: Ensure refactored steps work correctly.

#### 4.1 Validation Strategy

1. **Unit Tests** - Test use_case functions in isolation
2. **Integration Tests** - Test step definitions with mocked devices
3. **System Tests** - Execute full scenarios against testbed
4. **Regression Tests** - Compare results before/after refactoring

#### 4.2 Unit Test Structure

Create `boardfarm/unittests/use_cases/` with:

```
boardfarm/unittests/use_cases/
├── __init__.py
├── test_acs_use_cases.py
├── test_cpe_use_cases.py
├── test_voice_use_cases.py
└── conftest.py  # Shared fixtures
```

**Example Test:**

```python
# test_acs_use_cases.py
import pytest
from unittest.mock import Mock, patch
from boardfarm3.use_cases import acs as acs_use_cases


class TestGetParameterValue:
    """Tests for acs.get_parameter_value use case."""
    
    def test_returns_value_on_success(self, mock_acs, mock_cpe):
        """Should return parameter value when ACS responds."""
        mock_acs.GPV.return_value = [{"value": "1.0.0"}]
        
        result = acs_use_cases.get_parameter_value(
            mock_acs, mock_cpe, "Device.DeviceInfo.SoftwareVersion"
        )
        
        assert result == "1.0.0"
    
    def test_retries_on_failure(self, mock_acs, mock_cpe):
        """Should retry on transient failures."""
        mock_acs.GPV.side_effect = [None, None, [{"value": "1.0.0"}]]
        
        result = acs_use_cases.get_parameter_value(
            mock_acs, mock_cpe, "Device.DeviceInfo.SoftwareVersion", retries=3
        )
        
        assert result == "1.0.0"
        assert mock_acs.GPV.call_count == 3
```

#### 4.3 Validation Checklist

| Scenario | Test Method | Pass Criteria |
|----------|-------------|---------------|
| CPE Reboot (NBI) | System test | All steps pass, logs show use_case calls |
| CPE Reboot (GUI) | System test | All steps pass, GUI interactions work |
| Voice Call Setup | System test | Call connects, RTP established |
| Deprecation Warnings | Unit test | Warnings emitted for deprecated functions |
| Error Handling | Unit test | Exceptions propagate correctly |

### Phase 5: Documentation (Priority: MEDIUM)

**Objective**: Document the new architecture and migration guide.

#### 5.1 Documentation Deliverables

1. **Architecture Guide** - `boardfarm-bdd/docs/use_case_architecture.md`
2. **Migration Guide** - `boardfarm-bdd/docs/step_migration_guide.md`
3. **use_case Reference** - Auto-generated from docstrings
4. **Deprecation Notice** - Update README with deprecation info

#### 5.2 Step Definition Guidelines

Add to project documentation:

```markdown
## Step Definition Guidelines

### DO:
- Call use_case functions for all test operations
- Keep steps as thin wrappers (< 20 lines)
- Use fixtures for device access
- Include assertions for verification
- Log progress with print statements

### DON'T:
- Call device methods directly (e.g., `cpe.sw.get_uptime()`)
- Embed business logic in steps
- Parse logs or data in steps
- Create helper functions for device operations
```

---

## Implementation Timeline

| Phase | Description | Estimated Duration | Dependencies |
|-------|-------------|-------------------|--------------|
| Phase 1.1 | Create `acs.py` use_cases | 2-3 days | None |
| Phase 1.2 | Extend `cpe.py` use_cases | 1-2 days | None |
| Phase 2.1 | Refactor `cpe_steps.py` | 2-3 days | Phase 1 |
| Phase 2.2 | Refactor `acs_steps.py` | 1-2 days | Phase 1 |
| Phase 2.3 | Refactor `operator_steps.py` | 1 day | Phase 1 |
| Phase 2.4 | Refactor `sip_phone_steps.py` | 2-3 days | None |
| Phase 3 | Deprecation handling | 1-2 days | Phase 2 |
| Phase 4 | Validation | 2-3 days | All previous |
| Phase 5 | Documentation | 1-2 days | All previous |

**Total Estimated Duration**: 13-21 days

---

## Success Criteria

1. **Portability Achieved**
   - [ ] Step definitions use only use_case calls
   - [ ] No direct device method calls in steps
   - [ ] Same use_cases usable by robotframework-boardfarm
   - [ ] Interface selection via `via` parameter where applicable

2. **Single Source of Truth**
   - [ ] All test logic in use_cases modules
   - [ ] Steps are thin wrappers (< 20 lines average)
   - [ ] helpers.py deprecated with warnings

3. **Deprecation Compliance**
   - [ ] debtcollector added to Boardfarm dependencies
   - [ ] Deprecated functions emit warnings
   - [ ] Migration path documented

4. **Validation Complete**
   - [ ] All existing scenarios pass
   - [ ] Unit tests for use_cases (80%+ coverage)
   - [ ] No regression in test execution time

5. **Documentation Complete**
   - [ ] Architecture guide written
   - [ ] Migration guide for contributors
   - [ ] use_case API reference generated

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing tests | High | Phased rollout, extensive validation |
| Missing use_case coverage | Medium | Gap analysis before refactoring |
| Performance degradation | Low | Benchmark before/after |
| Complex edge cases | Medium | Keep fallback to device methods initially |
| Team adoption | Medium | Clear documentation, code review |

---

## Appendix A: Files to Create/Modify

### New Files

| File | Description |
|------|-------------|
| `boardfarm3/use_cases/acs.py` | ACS use case functions |
| `boardfarm3/use_cases/log_utils.py` | Log parsing utilities (optional) |
| `boardfarm/unittests/use_cases/test_acs_use_cases.py` | Unit tests |
| `boardfarm-bdd/docs/use_case_architecture.md` | Architecture documentation |
| `boardfarm-bdd/docs/step_migration_guide.md` | Migration guide |

### Modified Files

| File | Changes |
|------|---------|
| `boardfarm3/use_cases/cpe.py` | Add 5+ new functions |
| `boardfarm-bdd/tests/step_defs/cpe_steps.py` | Refactor to use_cases |
| `boardfarm-bdd/tests/step_defs/acs_steps.py` | Refactor to use_cases |
| `boardfarm-bdd/tests/step_defs/sip_phone_steps.py` | Refactor to use_cases |
| `boardfarm-bdd/tests/step_defs/operator_steps.py` | Refactor to use_cases |
| `boardfarm-bdd/tests/step_defs/helpers.py` | Add deprecation warnings |
| `boardfarm/pyproject.toml` | Add debtcollector dependency |

---

## Appendix B: use_case Function Mapping

### cpe_steps.py → use_cases

| Step Function | Target use_case |
|---------------|-----------------|
| `cpe_receives_connection_request_and_initiates_session` | `acs.wait_for_inform_message` |
| `cpe_sends_inform_message` | `acs.wait_for_inform_message` |
| `cpe_receives_and_acknowledges_reboot_rpc` | `acs.wait_for_reboot_rpc` |
| `cpe_executes_reboot_and_restarts` | `cpe.wait_for_reboot_completion` |
| `cpe_sends_inform_after_boot_completion` | `acs.wait_for_inform_message` |
| `cpe_resumes_normal_operation` | `acs.is_cpe_online` |
| `cpe_configuration_preserved_after_reboot` | `cpe.verify_config_preservation` |
| `cpe_does_not_reboot` | `cpe.get_seconds_uptime` (existing) |
| `cpe_is_unreachable_for_tr069` | `cpe.stop_tr069_client` |
| `cpe_comes_online_and_connects` | `cpe.start_tr069_client` + `acs.wait_for_inform_message` |

### acs_steps.py → use_cases

| Step Function | Target use_case |
|---------------|-----------------|
| `acs_sends_connection_request` | `acs.initiate_reboot` (implicit) |
| `acs_responds_to_inform_and_issues_reboot_rpc` | `acs.wait_for_reboot_rpc` |
| `acs_queues_reboot_rpc` | `acs.initiate_reboot` |
| `acs_issues_queued_reboot_rpc` | `acs.wait_for_reboot_rpc` |
| `acs_cannot_send_connection_request` | Verification only |

### sip_phone_steps.py → use_cases

| Step Function | Target use_case |
|---------------|-----------------|
| `phone_dials_number` | `voice.call_a_phone` |
| `phone_answers_call` | `voice.answer_a_call` |
| `phone_hangs_up` | `voice.disconnect_the_call` |
| `phone_is_idle` | `voice.is_call_idle` |
| `both_phones_connected` | `voice.is_call_connected` |
| `phone_rejects_call` | Custom use_case needed |

---

**Document Version**: 1.1  
**Last Updated**: January 26, 2026  
**Author**: AI Assistant  
**Status**: Pending Review

### Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Jan 26, 2026 | Initial draft |
| 1.1 | Jan 26, 2026 | Added Interface Handling section with `via` parameter pattern |
