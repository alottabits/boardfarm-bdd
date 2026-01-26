# Step Definition Migration Guide

This guide explains how to write new step definitions or migrate existing ones
to use the `boardfarm3.use_cases` modules.

## Overview

Step definitions should be **thin wrappers** that delegate all business logic
to `use_cases` functions. This ensures:

- **Portability**: Same logic works in pytest-bdd and robotframework-boardfarm
- **Maintainability**: Business logic centralized in one place
- **Testability**: use_cases can be unit tested independently

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Test Framework Layer                          │
│  ┌──────────────────────┐    ┌──────────────────────────────┐  │
│  │     pytest-bdd       │    │   robotframework-boardfarm    │  │
│  │  (Step Definitions)  │    │      (Keywords/Library)       │  │
│  └──────────┬───────────┘    └──────────────┬───────────────┘  │
└─────────────┼───────────────────────────────┼───────────────────┘
              │                               │
              ▼                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                 boardfarm3.use_cases Layer                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   acs.py    │  │   cpe.py    │  │       voice.py          │  │
│  │ (ACS ops)   │  │ (CPE ops)   │  │    (Voice/SIP ops)      │  │
│  └──────┬──────┘  └──────┬──────┘  └────────────┬────────────┘  │
└─────────┼────────────────┼──────────────────────┼───────────────┘
          │                │                      │
          ▼                ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Device Templates Layer                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  ACS (nbi,  │  │  CPE (sw,   │  │      SIPPhone           │  │
│  │   gui)      │  │   hw)       │  │                         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Step Definition Guidelines

### DO ✅

```python
from boardfarm3.use_cases import acs as acs_use_cases
from boardfarm3.use_cases import cpe as cpe_use_cases
from boardfarm3.use_cases import voice as voice_use_cases

@then("the CPE resumes normal operation")
def cpe_resumes_normal_operation(acs, cpe, bf_context):
    """Verify CPE is online - delegates to use_case."""
    cpe_id = bf_context.reboot_cpe_id
    
    # Call use_case for the verification
    is_online = acs_use_cases.is_cpe_online(acs, cpe, timeout=30)
    
    assert is_online, f"CPE {cpe_id} is not responding"
    print(f"✓ CPE {cpe_id} has resumed normal operation")
```

### DON'T ❌

```python
@then("the CPE resumes normal operation")
def cpe_resumes_normal_operation(acs, cpe, bf_context):
    """BAD: Direct device calls embedded in step."""
    cpe_id = bf_context.reboot_cpe_id
    
    # ❌ Don't call device methods directly
    result = acs.GPV("Device.DeviceInfo.SoftwareVersion", cpe_id=cpe_id)
    
    # ❌ Don't embed business logic in steps
    if not result:
        for attempt in range(3):
            time.sleep(5)
            result = acs.GPV("Device.DeviceInfo.SoftwareVersion", cpe_id=cpe_id)
            if result:
                break
    
    assert result, f"CPE {cpe_id} is not responding"
```

## Available use_cases Modules

### ACS Operations (`boardfarm3.use_cases.acs`)

```python
from boardfarm3.use_cases import acs as acs_use_cases

# Get parameter value (with retry)
value = acs_use_cases.get_parameter_value(acs, cpe, "Device.DeviceInfo.SoftwareVersion")

# Set parameter value
success = acs_use_cases.set_parameter_value(acs, cpe, "Device.WiFi.SSID.1.SSID", "NewSSID")

# Initiate reboot
acs_use_cases.initiate_reboot(acs, cpe, command_key="reboot")

# Check if CPE is online
is_online = acs_use_cases.is_cpe_online(acs, cpe, timeout=30)

# Wait for Inform message
acs_use_cases.wait_for_inform_message(acs, cpe_id, event_codes=["1 BOOT"], since=timestamp)

# Wait for Reboot RPC
timestamp = acs_use_cases.wait_for_reboot_rpc(acs, cpe_id, since=timestamp, timeout=90)

# Wait for boot Inform
timestamp = acs_use_cases.wait_for_boot_inform(acs, cpe_id, since=timestamp, timeout=240)

# Send connection request
success = acs_use_cases.send_connection_request(acs, cpe)

# Verify queued task
found = acs_use_cases.verify_queued_task(acs, cpe_id, task_type="reboot", since=timestamp)
```

### CPE Operations (`boardfarm3.use_cases.cpe`)

```python
from boardfarm3.use_cases import cpe as cpe_use_cases

# Wait for reboot completion
cpe_use_cases.wait_for_reboot_completion(cpe, timeout=60)

# Stop/Start TR-069 client
cpe_use_cases.stop_tr069_client(cpe)
cpe_use_cases.start_tr069_client(cpe)

# Check if TR-069 agent is running
is_running = cpe_use_cases.is_tr069_agent_running(cpe)

# Refresh console connection
success = cpe_use_cases.refresh_console_connection(cpe)

# Get console uptime
uptime = cpe_use_cases.get_console_uptime_seconds(cpe)

# Verify config preservation
errors = cpe_use_cases.verify_config_preservation(cpe, acs, config_before)
```

### Voice Operations (`boardfarm3.use_cases.voice`)

```python
from boardfarm3.use_cases import voice as voice_use_cases

# Make a call
voice_use_cases.call_a_phone(caller, callee)

# Answer a call
success = voice_use_cases.answer_a_call(phone)

# Disconnect a call
voice_use_cases.disconnect_the_call(phone)

# Put phone off hook
voice_use_cases.put_phone_offhook(phone)
```

## Interface Selection with `via` Parameter

For ACS operations that can be performed via different interfaces (NBI API or GUI),
use the `via` parameter:

```python
# Default: Use NBI (REST API)
value = acs_use_cases.get_parameter_value(acs, cpe, parameter)

# Explicit NBI
value = acs_use_cases.get_parameter_value(acs, cpe, parameter, via="nbi")

# Use GUI instead
value = acs_use_cases.get_parameter_value(acs, cpe, parameter, via="gui")

# Reboot via GUI
acs_use_cases.initiate_reboot(acs, cpe, via="gui")
```

## Migration Examples

### Before: Direct Device Calls

```python
@when("the CPE sends an Inform message to the ACS")
def cpe_sends_inform_message(acs, cpe, bf_context):
    """BAD: Complex log parsing embedded in step."""
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
            
            # Complex filtering logic...
            filtered_lines = filter_logs_by_timestamp(log_lines, start_timestamp)
            filtered_lines = filter_logs_by_cpe_id(filtered_lines, cpe_id)
            
            if "inform" in "\n".join(filtered_lines).lower():
                print(f"✓ CPE {cpe_id} sent Inform message")
                return
        except Exception:
            pass
        
        time.sleep(1)
    
    raise AssertionError(f"CPE {cpe_id} did not send Inform message")
```

### After: use_case Delegation

```python
@when("the CPE sends an Inform message to the ACS")
def cpe_sends_inform_message(acs, cpe, bf_context):
    """GOOD: Delegates to use_case."""
    cpe_id = bf_context.reboot_cpe_id
    since = getattr(bf_context, "test_start_timestamp", None)

    print(f"Waiting for CPE {cpe_id} to send Inform message...")

    acs_use_cases.wait_for_inform_message(acs, cpe_id, since=since, timeout=30)

    print(f"✓ CPE {cpe_id} sent Inform message")
```

## Creating New use_cases

If you need functionality not covered by existing use_cases:

1. **Add to appropriate module** (`acs.py`, `cpe.py`, or `voice.py`)
2. **Follow docstring convention**:

```python
def new_operation(
    acs: ACS,
    cpe: CPE,
    parameter: str,
    via: InterfaceType = "nbi",
) -> bool:
    """Short description of the operation.

    .. hint:: This Use Case implements statements from the test suite such as:

        - Step text that this function supports
        - Another related step text

    :param acs: ACS device instance
    :type acs: ACS
    :param cpe: CPE device instance  
    :type cpe: CPE
    :param parameter: Description of parameter
    :type parameter: str
    :param via: Interface to use ("nbi" for API, "gui" for web interface)
    :type via: InterfaceType
    :return: Description of return value
    :rtype: bool
    :raises UseCaseFailure: When operation fails
    """
    # Implementation...
```

3. **Add unit tests** in `boardfarm/unittests/use_cases/`

## Testing

### Running Unit Tests

```bash
# Run use_cases unit tests
cd boardfarm
python -m pytest unittests/use_cases/ -v

# Run step definition unit tests
cd boardfarm-bdd
python -m pytest tests/unit/ -v
```

### Test Structure

```
boardfarm/unittests/use_cases/
├── __init__.py
├── conftest.py          # Shared fixtures (mock_acs, mock_cpe, etc.)
├── test_acs_use_cases.py
└── test_cpe_use_cases.py
```

---

**Document Version**: 1.0  
**Last Updated**: January 26, 2026  
**Author**: AI Assistant
