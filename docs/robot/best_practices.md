# Robot Framework Keyword Best Practices

This guide documents important lessons learned and best practices for writing Robot Framework keywords with the boardfarm integration. Following these guidelines will help avoid common pitfalls.

## Table of Contents

- [Keyword Decorator Patterns](#keyword-decorator-patterns)
- [Avoiding Recursive Keyword Calls](#avoiding-recursive-keyword-calls)
- [Timing and Timestamp Filtering](#timing-and-timestamp-filtering)
- [CPE Reboot Handling](#cpe-reboot-handling)
- [Password and Configuration Handling](#password-and-configuration-handling)
- [Cleanup Best Practices](#cleanup-best-practices)
- [GenieACS Task Behavior](#genieacs-task-behavior)

---

## Keyword Decorator Patterns

### Problem: Multiple @keyword Decorators Don't Work

Robot Framework's `@keyword` decorator only registers the **first** decorator on a method. Multiple decorators are silently ignored:

```python
# ❌ WRONG - Only "Primary keyword name" will be registered
@keyword("Primary keyword name")
@keyword("Alias keyword name")
@keyword("Another alias")
def my_keyword(self, acs, cpe):
    pass
```

### Solution: Use Separate Alias Methods

Create separate methods for each keyword name, with aliases calling the primary method:

```python
# ✅ CORRECT - Each keyword is a separate method
@keyword("Primary keyword name")
def my_keyword(self, acs, cpe):
    """Primary implementation."""
    # ... implementation ...

@keyword("Alias keyword name")
def my_keyword_alias(self, acs, cpe):
    """Alias for Primary keyword name."""
    return self.my_keyword(acs, cpe)

@keyword("Another alias")
def my_keyword_another_alias(self, acs, cpe):
    """Alias for Primary keyword name."""
    return self.my_keyword(acs, cpe)
```

---

## Avoiding Recursive Keyword Calls

### Problem: Local Keywords Shadow Library Keywords

When a local keyword in a `.robot` file has the same name as a library keyword, calling it without qualification causes infinite recursion:

```robot
*** Keywords ***
# ❌ WRONG - This calls itself recursively
A CPE Is Online And Fully Provisioned
    ${acs}=    Get Device By Type    ACS
    ${cpe}=    Get Device By Type    CPE
    # This calls the LOCAL keyword, not the library keyword!
    ${result}=    A CPE Is Online And Fully Provisioned    ${acs}    ${cpe}
```

Error message: `Keyword 'A CPE Is Online And Fully Provisioned' expected 0 arguments, got 2.`

### Solution: Use Fully Qualified Library Names

Prefix the keyword call with the library name to explicitly call the library keyword:

```robot
*** Keywords ***
# ✅ CORRECT - Uses fully qualified name
A CPE Is Online And Fully Provisioned
    ${acs}=    Get Device By Type    ACS
    ${cpe}=    Get Device By Type    CPE
    # Explicitly calls the library keyword
    ${result}=    background_keywords.A CPE Is Online And Fully Provisioned    ${acs}    ${cpe}
```

### Best Practice: Name Local Keywords Differently

Alternatively, give local keywords unique names that don't shadow library keywords:

```robot
*** Keywords ***
# ✅ CORRECT - Different name avoids shadowing
Setup CPE Online And Provisioned
    ${acs}=    Get Device By Type    ACS
    ${cpe}=    Get Device By Type    CPE
    ${result}=    A CPE Is Online And Fully Provisioned    ${acs}    ${cpe}
    Set Suite Variable    ${BASELINE}    ${result}
```

---

## Timing and Timestamp Filtering

### Problem: Timestamp Filtering Misses Events

Many use cases filter ACS logs by timestamp using a `since` parameter. If the timestamp is captured too late, relevant log entries may be filtered out:

```robot
# ❌ PROBLEM - REBOOT_TIMESTAMP captured AFTER reboot events already occurred
The Operator Initiates A Reboot Task On The ACS
    ${result}=    Initiate Reboot Task    ${ACS}    ${CPE}
    # If CPE reboots very quickly, boot Inform might already be in logs
    # with timestamp BEFORE this moment
    Set Suite Variable    ${REBOOT_TIMESTAMP}    ${result}[timestamp]
```

### Solution: Capture Timestamp Early with Buffer

Capture timestamps **before** initiating actions, with a small buffer for clock differences:

```python
# ✅ CORRECT - Capture timestamp 5 seconds before "now"
from datetime import datetime, timedelta, timezone

def initiate_reboot_task(self, acs, cpe):
    # Capture timestamp BEFORE the action, with 5-second buffer
    test_start_timestamp = (
        datetime.now(timezone.utc) - timedelta(seconds=5)
    ).replace(tzinfo=None)
    
    # Now initiate the reboot
    acs_use_cases.initiate_reboot(acs, cpe)
    
    return {"test_start_timestamp": test_start_timestamp}
```

### Use Appropriate Timeouts

Different operations need different timeouts. Match the timeout to the expected operation duration:

| Operation | Recommended Timeout |
|-----------|-------------------|
| Simple Inform message | 30-60 seconds |
| Boot Inform after reboot | 240 seconds (4 minutes) |
| CPE online check | 30-60 seconds |
| Parameter operations | 30 seconds |

```python
# ✅ CORRECT - Use longer timeout for boot Inform
@keyword("The CPE sends an Inform message after boot completion")
def send_inform_after_boot(self, acs, cpe, since=None, timeout=240):
    """Wait for boot Inform - needs longer timeout."""
    return acs_use_cases.wait_for_boot_inform(
        acs, cpe.sw.cpe_id, since=since, timeout=timeout
    )
```

---

## CPE Reboot Handling

### Always Refresh Console Connection After Reboot

After a CPE reboot, the console connection may become stale or invalid. Always refresh it:

```python
@keyword("The CPE sends an Inform message after boot completion")
def send_inform_after_boot(self, acs, cpe, since=None, timeout=240):
    # Wait for boot Inform
    inform_timestamp = acs_use_cases.wait_for_boot_inform(
        acs, cpe.sw.cpe_id, since=since, timeout=timeout
    )
    
    # ✅ IMPORTANT: Refresh console connection after reboot
    print("↻ Refreshing CPE console connection after reboot...")
    if cpe_use_cases.refresh_console_connection(cpe):
        print("✓ Console connection refreshed successfully")
    else:
        print("⚠ Could not refresh console connection")
    
    return str(inform_timestamp)
```

### Wait for CPE to Be Ready Before TR-069 Operations

After reboot, the CPE may not be immediately ready for TR-069 operations:

```python
def restore_password_after_reboot(self, acs, cpe, admin_user_index):
    # ✅ Wait for CPE to be fully online first
    print("Waiting for CPE to be ready...")
    for i in range(30):
        try:
            if acs_use_cases.is_cpe_online(acs, cpe, timeout=5):
                print("✓ CPE is online and ready")
                break
        except Exception:
            pass
        time.sleep(1)
    else:
        print("⚠ CPE may not be fully ready")
    
    # Now perform TR-069 operations
    acs_use_cases.set_parameter_value(acs, cpe, param_path, value)
```

---

## Password and Configuration Handling

### Problem: TR-069 Password Values Are Encrypted

TR-069 typically returns password values as encrypted hashes, not plaintext. You cannot restore a password by setting it back to the encrypted value:

```python
# ❌ WRONG - Can't restore encrypted password
original_password = acs_use_cases.get_parameter_value(
    acs, cpe, "Device.Users.User.10.Password"
)
# original_password is an encrypted hash like "$6$rounds=5000$..."

# Later, trying to restore:
acs_use_cases.set_parameter_value(
    acs, cpe, "Device.Users.User.10.Password",
    original_password  # This sets the hash as the password, not the original!
)
```

### Solution: Restore to Known Default Value

Always restore passwords to a known default value (e.g., "admin"):

```python
# ✅ CORRECT - Restore to default password
@keyword("Restore CPE GUI Password To Default")
def restore_cpe_gui_password_to_default(self, acs, cpe, admin_user_index):
    """Restore password to default 'admin'.
    
    TR-069 returns encrypted hashes, so we can't restore from the
    original value. Instead, restore to the known default.
    """
    default_password = "admin"  # Known default for PrplOS
    
    acs_use_cases.set_parameter_value(
        acs, cpe,
        f"Device.Users.User.{admin_user_index}.Password",
        default_password
    )
```

---

## Cleanup Best Practices

### Align Robot Cleanup with pytest Cleanup

Robot Framework cleanup should mirror the pytest `cleanup_cpe_config_after_scenario` fixture behavior:

```robot
*** Keywords ***
Cleanup After Reboot Test
    [Documentation]    Cleanup after reboot test - aligned with pytest fixture.
    # Run common cleanup (includes console refresh)
    Run Keyword And Ignore Error    Cleanup After Test
    
    # Restore password to default 'admin' (not original encrypted value)
    ${has_index}=    Run Keyword And Return Status    Variable Should Exist    ${ADMIN_USER_INDEX}
    IF    ${has_index}
        Run Keyword And Ignore Error    Restore CPE GUI Password To Default
        ...    ${ACS}    ${CPE}    ${ADMIN_USER_INDEX}
    END
```

### Common Cleanup Should Refresh Console

The common cleanup keyword should always refresh the console connection:

```robot
Cleanup After Test
    [Documentation]    Common test teardown.
    Log    Cleaning up after test...
    
    # Always refresh console - previous test might have rebooted CPE
    ${cpe}=    Run Keyword And Ignore Error    Get CPE Device
    ${cpe_available}=    Set Variable    ${cpe}[0] == 'PASS'
    IF    ${cpe_available}
        Run Keyword And Ignore Error    Refresh CPE Console Connection    ${cpe}[1]
    END
```

### Use Run Keyword And Ignore Error for Cleanup

Cleanup should not fail the test if something goes wrong:

```robot
# ✅ CORRECT - Cleanup continues even if individual steps fail
Cleanup After Test
    Run Keyword And Ignore Error    Cleanup SIP Phones
    Run Keyword And Ignore Error    Cleanup ACS GUI Session
    Run Keyword And Ignore Error    Refresh CPE Console Connection    ${CPE}
```

---

## GenieACS Task Behavior

### Problem: Tasks May Persist and Re-Execute

GenieACS queues tasks and may re-execute them if not completed:

1. Test initiates Reboot task
2. GenieACS sends Reboot RPC to CPE
3. CPE reboots, connection drops
4. Task may still be "pending" in GenieACS
5. CPE boots, sends Inform
6. **GenieACS sends another Reboot!** (task retry)

This can cause double reboots and extended test times.

### Awareness

This is a GenieACS behavior to be aware of. The test will still pass, but may take longer due to the extra reboot cycle.

### Mitigation (Optional)

If needed, pending tasks can be cleared via the GenieACS NBI API:

```python
import requests

def clear_pending_tasks(acs_url, cpe_id):
    """Clear pending tasks for a CPE (optional cleanup step)."""
    tasks_url = f"{acs_url}/devices/{cpe_id}/tasks"
    response = requests.get(tasks_url, timeout=10)
    
    if response.ok:
        tasks = response.json()
        for task in tasks:
            task_id = task.get("_id")
            if task_id:
                requests.delete(f"{tasks_url}/{task_id}", timeout=10)
```

---

## Summary Checklist

When writing new Robot Framework keywords:

- [ ] Use single `@keyword` decorator per method (create alias methods if needed)
- [ ] Use fully qualified names when calling library keywords from local keywords
- [ ] Capture timestamps **before** actions with a 5-second buffer
- [ ] Use appropriate timeouts (240s for boot Inform, 30-60s for other operations)
- [ ] Refresh console connection after CPE reboot
- [ ] Wait for CPE to be online before TR-069 operations
- [ ] Restore passwords to default value, not original encrypted value
- [ ] Align cleanup with pytest fixture behavior
- [ ] Use `Run Keyword And Ignore Error` for cleanup steps
- [ ] Be aware of GenieACS task retry behavior

---

## Further Reading

- [Getting Started Guide](getting_started.md)
- [Keyword Reference](keyword_reference.md)
- [Configuration Cleanup Process](../Configuration%20Cleanup%20Process.md)
- [pytest conftest.py cleanup](../../tests/conftest.py) - Reference implementation
