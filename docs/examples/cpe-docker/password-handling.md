# Password Handling — PrplOS CPE

## Overview

This document covers how the default GUI password (`admin`) flows through the
PrplOS CPE testbed stack, and how test cleanup restores passwords after
modification.

---

## Default Password: Where `admin` is Defined

The default password **`admin`** is **not explicitly set** in the PrplOS
container configuration or initialisation scripts. It is a **hardcoded
fallback** in the Boardfarm3 framework, used when no `gui_password` is
specified in the device configuration.

### Configuration Hierarchy

```
┌─────────────────────────────────────────────────────────┐
│ PrplOS Upstream Image                                   │
│ Factory Default: admin:admin (assumed)                  │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ Raikou-Net Container                                    │
│ No explicit password configuration                      │
│ Inherits from PrplOS upstream                           │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ Boardfarm3 Framework                                    │
│ Hardcoded default: "admin"                              │
│ Used when gui_password not in config                    │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ Boardfarm Configuration (Optional)                      │
│ Can override with: "gui_password": "custom"             │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ Test Execution                                          │
│ Uses gui_password property                              │
│ Cleanup restores to "admin"                             │
└─────────────────────────────────────────────────────────┘
```

### Source Locations

| Location | File | Detail |
|---|---|---|
| GUI helper constant | `boardfarm3/lib/gui/prplos/pages/page_helper.py` | `PRPLOS_PASSWORD = "admin"` |
| Device property | `boardfarm3/devices/prplos_cpe.py` | `config.get("gui_password", "admin")` — fallback when not in config |
| Config example | `bf_config/boardfarm_config_example.json` | Optional `"gui_password": "admin"` field |

The same fallback pattern exists in `rpirdkb_cpe.py` (RDK-B) and `vcpe_ofw.py` (OpenWrt).

### PrplOS Container — No Explicit Configuration

The PrplOS container does **not** configure a password anywhere:

- No password in the Dockerfile
- No UCI configuration for users/passwords
- No initialisation scripts setting credentials

The container inherits the upstream PrplOS factory defaults.

---

## Password Cleanup After Tests

### The Problem

When tests modify the GUI password via TR-069 SPV (Set Parameter Values), the
cleanup process must restore the original value. However:

1. **GPV returns encrypted/hashed values** — `Device.Users.User.X.Password`
   returns the already-encrypted password
2. **SPV expects plaintext** — to encrypt and store it
3. **No decrypt operation exists** in TR-069

This makes true password restoration impossible without tracking the plaintext.

### How Cleanup Works

Cleanup is **automatic** in both frameworks. The keyword/step that sets the
password registers its own teardown to restore `"admin"` (the known default):

**pytest-bdd** — cleanup runs after `yield`:

```python
@given("the user has set the CPE GUI password to {password}")
def set_gui_password(acs, cpe, password):
    admin_idx = discover_admin_user_index(acs, cpe)
    param_path = f"Device.Users.User.{admin_idx}.Password"
    acs_use_cases.set_parameter_value(acs, cpe, param_path, password)
    yield
    # Automatic cleanup — restore to known default
    acs_use_cases.set_parameter_value(acs, cpe, param_path, "admin")
```

**Robot Framework** — cleanup via the `BoardfarmListener` teardown stack:

```python
@keyword("The user has set the CPE GUI password to")
def set_cpe_gui_password(self, acs, cpe, password):
    admin_idx = discover_admin_user_index(acs, cpe)
    param_path = f"Device.Users.User.{admin_idx}.Password"
    acs_use_cases.set_parameter_value(acs, cpe, param_path, password)

    _get_listener().register_teardown(
        f"Restore password {param_path}",
        self._restore_password, acs, cpe, param_path,
    )

@staticmethod
def _restore_password(acs, cpe, param_path):
    acs_use_cases.set_parameter_value(acs, cpe, param_path, "admin")
```

In both cases the password is restored to `"admin"` because:
- `admin` is the documented default for all PrplOS devices
- The Boardfarm framework assumes `admin:admin` as the baseline
- All tests start from this known state

### Alternative Approaches Considered

| Option | Approach | Status |
|---|---|---|
| **1. Restore to `admin`** | Detect password fields, use known default | **Implemented** — current solution |
| **2. Track plaintext** | Store plaintext when setting, restore from context | Viable if tests need non-default passwords |
| **3. Skip capture** | Assume default, don't call GPV for passwords | Simpler but less robust |
| **4. Skip cleanup** | Don't restore passwords; rely on container restart | Poor test isolation |

The current approach (Option 1) is recommended for most scenarios.

### TR-069 Protocol Limitation

This is a fundamental TR-069 constraint: GPV returns encrypted values for
security, SPV expects plaintext values to encrypt. There is no decrypt
operation. Tracking plaintext values in the test context is the only way to
achieve true restoration.

---

## Verification

To verify the default password in a fresh environment:

1. Start a fresh PrplOS container (no tests run)
2. Query via TR-069:
   ```python
   admin_idx = discover_admin_user_index(acs, cpe)
   password = gpv_value(acs, cpe, f"Device.Users.User.{admin_idx}.Password")
   ```
3. Log in via GUI with `admin:admin`

---

## Related Files

- Framework defaults: `boardfarm3/lib/gui/prplos/pages/page_helper.py`
- Device property: `boardfarm3/devices/prplos_cpe.py`
- Config example: `bf_config/boardfarm_config_example.json`
- pytest-bdd cleanup: `tests/step_defs/background_steps.py` (yield-based)
- Robot Framework cleanup: `robot/libraries/background_keywords.py` (listener teardown stack)
- Cleanup architecture: [Test Cleanup Architecture](../../architecture/test-cleanup-architecture.md)
