# Configuration Cleanup Process

## Overview

To ensure test isolation and prevent configuration changes from one scenario affecting subsequent scenarios, this project implements automatic cleanup systems for:

1. **CPE Configuration**: Restores TR-069 configuration parameters to their original state
2. **SIP Phones**: Terminates active calls, de-registers phones, and stops pjsua processes


## Why Cleanup is Necessary

When test scenarios modify CPE configuration (e.g., changing username/password, SSID settings), these changes persist in the CPE's persistent storage. Without cleanup:

- **Test Pollution**: Configuration changes from one scenario can affect subsequent scenarios
- **Unpredictable Behavior**: Tests may pass or fail based on configuration left by previous tests
- **Maintenance Burden**: Manual cleanup steps would be required in every feature file

## How It Works

### 1. Capture Original Values Before Changes

Before making any configuration changes, step definitions must capture the original values and store them in `bf_context.original_config` with the following structure:

```python
bf_context.original_config = {
    "users": {
        "items": {
            "1": {
                "Username": {
                    "gpv_param": "Device.Users.User.1.Username",
                    "value": "original_username"
                },
                "Password": {
                    "gpv_param": "Device.Users.User.1.Password",
                    "value": "original_encrypted_password"
                }
            }
        }
    },
    "wifi_ssids": {
        "items": {
            "1": {
                "SSID": {
                    "gpv_param": "Device.WiFi.SSID.1.SSID",
                    "value": "original_ssid"
                },
                "Enable": {
                    "gpv_param": "Device.WiFi.SSID.1.Enable",
                    "value": True
                }
            }
        }
    }
}
```

**Key Requirements:**
- Each configuration item must include the `gpv_param` (TR-069 parameter path) and `value` (original value)
- Values must be captured **BEFORE** making changes
- The structure mirrors `config_before_reboot` for consistency

### 2. Automatic Cleanup Fixture

A pytest fixture (`cleanup_cpe_config_after_scenario`) in `conftest.py` automatically:

- Runs after every scenario (using `autouse=True`)
- Executes cleanup even if the scenario fails (using `yield` pattern)
- Iterates through `original_config` generically
- Restores all values using stored `gpv_param` paths via TR-069 SPV

**Implementation Location:** `conftest.py`

### 3. Generic Cleanup Logic

The cleanup fixture automatically discovers and restores all items in `original_config`:

1. Iterates through all top-level keys (e.g., `users`, `wifi_ssids`)
2. For each key with `items`, iterates through all items
3. For each item, collects all fields with `gpv_param` and `value`
4. Restores values using TR-069 SPV with the stored parameter paths

This generic approach means:
- **No hardcoded cleanup logic** - automatically handles any configuration items
- **Easy to extend** - just add items to `original_config` following the structure
- **Consistent** - uses the same structure as `config_before_reboot`

## Implementation Guidelines

### For Step Definitions That Change Configuration

When implementing a step definition that modifies CPE configuration:

1. **Initialize `original_config`** if needed:
   ```python
   if not hasattr(bf_context, "original_config"):
       bf_context.original_config = {}
   ```

2. **Capture original values BEFORE making changes**:
   ```python
   # Capture original value
   original_value = gpv_value(acs, cpe, "Device.Some.Parameter")
   
   # Store in original_config with gpv_param
   if "some_config" not in bf_context.original_config:
       bf_context.original_config["some_config"] = {
           "items": {}
       }
   
   bf_context.original_config["some_config"]["items"]["1"] = {
       "Parameter": {
           "gpv_param": "Device.Some.Parameter",
           "value": original_value
       }
   }
   ```

3. **Then make the change**:
   ```python
   acs.SPV([{"Device.Some.Parameter": new_value}], cpe_id=cpe_id)
   ```

### Structure Requirements

The `original_config` structure must follow this pattern:

- **Simple values**: Not currently used, but could be added
- **Dict-based configs** (users, wifi_ssids, etc.):
  ```python
  {
      "config_name": {
          "items": {
              "item_index": {
                  "field_name": {
                      "gpv_param": "Device.Path.To.Parameter",
                      "value": original_value  # Can be str, int, or bool
                  }
              }
          }
      }
  }
  ```

### Example: Adding a New Configuration Item

To add cleanup for a new configuration item (e.g., DNS settings):

1. **In the step definition that changes DNS**:
   ```python
   # Capture original DNS before change
   original_dns = gpv_value(acs, cpe, "Device.DNS.Client.Server.1")
   
   # Store in original_config
   if "dns" not in bf_context.original_config:
       bf_context.original_config["dns"] = {"items": {}}
   
   bf_context.original_config["dns"]["items"]["1"] = {
       "Server": {
           "gpv_param": "Device.DNS.Client.Server.1",
           "value": original_dns
       }
   }
   
   # Then make the change
   acs.SPV([{"Device.DNS.Client.Server.1": new_dns}], cpe_id=cpe_id)
   ```

2. **The cleanup fixture will automatically restore it** - no additional code needed!

## Benefits

1. **Automatic**: No manual cleanup steps required in feature files
2. **Resilient**: Cleanup runs even if scenarios fail
3. **Generic**: Automatically handles any items added to `original_config`
4. **Consistent**: Uses the same structure as `config_before_reboot`
5. **Extensible**: Easy to add new configuration items to track

## Container Initialization Behavior

The PrplOS container initialization script (`container-init.sh`) ensures clean state:

- **Normal Boot**: Removes any leftover `/boot/sysupgrade.tgz` config backups
- **Upgrade Boot**: Preserves and restores config backups only during firmware upgrades

This means:
- Normal reboots (like in remote reboot scenarios) **preserve** TR-069 configuration changes
- The cleanup system is necessary to restore original values **between test scenarios**
- Container initialization handles cleanup of stale config backups, not test configuration

## Verification

To verify cleanup is working:

1. **Check test output**: Look for cleanup messages like:
   ```
   Cleaning up CPE configuration for CPE-123...
   ✓ Restored Users 1 to original values
   ✓ Restored Wifi Ssids 1 to original values
   ✓ CPE configuration cleanup completed successfully
   ```

2. **Check for errors**: If cleanup fails, warnings will be printed:
   ```
   ⚠ Cleanup warnings:
     - Failed to restore Users 1 (SPV status: 1)
   ```

3. **Verify isolation**: Run multiple scenarios and verify configuration doesn't persist between them

## SIP Phone Cleanup

### Overview

SIP phone cleanup ensures that phones are properly cleaned up between test scenarios, preventing active calls and registrations from affecting subsequent tests.

### How It Works

#### 1. Track Configured Phones

When phones are configured in the `validate_use_case_phone_requirements` step, they are tracked in `bf_context.configured_phones`:

```python
bf_context.configured_phones = {
    'lan_phone': ('lan_phone', phone_instance),
    'wan_phone': ('wan_phone', phone_instance),
    'wan_phone2': ('wan_phone2', phone_instance)
}
```

**Structure:**
- **Key**: Use case role name (e.g., `lan_phone`, `wan_phone`)
- **Value**: Tuple of `(fixture_name, phone_instance)`
  - `fixture_name`: Name of the phone in the testbed (e.g., `lan_phone`)
  - `phone_instance`: The actual PJSIPPhone device object

#### 2. Automatic Cleanup Fixture

A pytest fixture (`cleanup_sip_phones_after_scenario`) in `conftest.py` automatically:

- Runs after every scenario (using `autouse=True`)
- Executes cleanup even if the scenario fails (using `yield` pattern)
- Iterates through all configured phones in `bf_context.configured_phones`
- Performs cleanup actions for each phone

**Implementation Location:** `conftest.py`

#### 3. Cleanup Actions

For each configured phone, the cleanup fixture performs:

1. **Terminate Active Calls**: Calls `phone.hangup()` to end any ongoing calls
2. **Stop pjsua and De-register**: Calls `phone.phone_kill()` which:
   - Quits the pjsua process
   - Automatically de-registers from the SIP server
   - Resets the phone to a clean state

**Error Handling:**
- If no active call exists, the hangup attempt is silently ignored
- Cleanup errors are logged but don't fail the test
- All phones are cleaned up even if one fails

### Implementation Guidelines

#### For Step Definitions That Use SIP Phones

The `validate_use_case_phone_requirements` step automatically handles tracking:

```python
@given(parsers.parse("the following SIP phones are required for this use case:\n{datatable}"))
def validate_use_case_phone_requirements(
    sipcenter: SIPServer,
    bf_context: Any,
    devices: Any,
    datatable: Any,
) -> None:
    # ... phone discovery and mapping ...
    
    # Track configured phones for cleanup
    bf_context.configured_phones = {}
    for use_case_name, (fixture_name, phone) in phone_mapping.items():
        setattr(bf_context, use_case_name, phone)
        bf_context.configured_phones[use_case_name] = (fixture_name, phone)
```

**No additional cleanup code needed** - the fixture handles everything automatically!

### Benefits

1. **Automatic**: No manual cleanup steps required in feature files
2. **Resilient**: Cleanup runs even if scenarios fail
3. **Complete**: Handles calls, registrations, and process cleanup
4. **Isolated**: Each scenario starts with clean phone state
5. **Portable**: Works across different testbed configurations

### Cleanup Output

To verify cleanup is working, check test output for messages like:

```
Cleaning up 3 SIP phone(s)...
  Cleaning up lan_phone (lan_phone)...
    ℹ No active calls to terminate on lan_phone
    ✓ Stopped pjsua and de-registered lan_phone
  Cleaning up wan_phone (wan_phone)...
    ✓ Terminated active calls on wan_phone
    ✓ Stopped pjsua and de-registered wan_phone
  Cleaning up wan_phone2 (wan_phone2)...
    ℹ No active calls to terminate on wan_phone2
    ✓ Stopped pjsua and de-registered wan_phone2
  Cleaning up SIP server registrations...
    ℹ Phone numbers configured: 1000, 2000, 3000
    ✓ SIP server will auto-expire registrations
✓ SIP phone cleanup completed successfully
```

### Why This Prevents Issues

Without cleanup, phones would:
- Have active calls from previous scenarios
- Remain registered with the SIP server
- Have pjsua processes consuming resources
- Cause unpredictable behavior in subsequent tests

The cleanup system ensures each scenario starts fresh, just like the CPE configuration cleanup.

## Related Documentation


- **Configuration Verification**: See how `config_before_reboot` is used for verification in `reboot_main_scenario_steps.py`
- **Container Initialization**: See `raikou/components/cpe/prplos/container-init.sh` for container-level cleanup
- **Background Steps**: See `tests/step_defs/background_steps.py` for examples of capturing original values

