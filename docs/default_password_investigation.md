# Default Password 'admin' - Investigation Results

## Summary

The default password **`admin`** is **NOT explicitly set** in the PrplOS container configuration or initialization scripts. Instead, it's a **hardcoded default** in the Boardfarm3 framework that is used when no `gui_password` is specified in the device configuration.

## Where 'admin' is Defined

### 1. Boardfarm3 Framework (Primary Source)

The default password `admin` is hardcoded in multiple locations within the Boardfarm3 framework:

#### [`boardfarm3/lib/gui/prplos/pages/page_helper.py:31-32`](file:///home/rjvisser/projects/req-tst/boardfarm/boardfarm3/lib/gui/prplos/pages/page_helper.py#L31-L32)

```python
PRPLOS_USER = "admin"
PRPLOS_PASSWORD = "admin"  # noqa: S105  # super secret!!!!
```

This is used for GUI automation and web interface login.

#### [`boardfarm3/devices/prplos_cpe.py:313-319`](file:///home/rjvisser/projects/req-tst/boardfarm/boardfarm3/devices/prplos_cpe.py#L313-L319)

```python
@property
def gui_password(self) -> str:
    """GUI login password.

    :return: GUI password
    :rtype: str
    """
    return self._hw.config.get("gui_password", "admin")
```

**This is the key location**: If `gui_password` is not specified in the device configuration, it defaults to `"admin"`.

The same pattern exists in:
- [`boardfarm3/devices/rpirdkb_cpe.py`](file:///home/rjvisser/projects/req-tst/boardfarm/boardfarm3/devices/rpirdkb_cpe.py) (RDK-B devices)
- [`boardfarm3/devices/vcpe_ofw.py`](file:///home/rjvisser/projects/req-tst/boardfarm/boardfarm3/devices/vcpe_ofw.py) (OpenWrt containers)

### 2. Boardfarm Configuration Files

The `gui_password` can be **optionally** specified in the boardfarm configuration:

#### [`boardfarm-bdd/bf_config/boardfarm_config_example.json:9`](file:///home/rjvisser/projects/req-tst/boardfarm-bdd/bf_config/boardfarm_config_example.json#L9)

```json
{
    "devices": [
        {
            "name": "board",
            "type": "bf_cpe",
            "gui_password": "admin",
            ...
        }
    ]
}
```

**Note**: This is just documenting the default - it's not actually setting it. If this line is omitted, the framework still defaults to `"admin"`.

### 3. PrplOS System - No Explicit Configuration

**Important finding**: The PrplOS container itself does **NOT** have any explicit password configuration in:

- ❌ No password in [`raikou-net/components/cpe/prplos/Dockerfile`](file:///home/rjvisser/projects/req-tst/raikou-net/components/cpe/prplos/Dockerfile)
- ❌ No UCI configuration for users/passwords
- ❌ No initialization scripts setting passwords
- ❌ No default configuration files with user credentials

The PrplOS container uses the **upstream PrplOS image** which presumably has `admin:admin` as the factory default credentials.

## How It Works

### Password Flow

1. **PrplOS Container Starts**: Uses factory default credentials (likely `admin:admin` from upstream PrplOS)
2. **Boardfarm Connects**: Reads device configuration from inventory JSON
3. **GUI Password Property**: Returns `config.get("gui_password", "admin")`
   - If `gui_password` is in config → uses that value
   - If `gui_password` is missing → defaults to `"admin"`
4. **Test Steps**: Use the `gui_password` property when setting passwords via TR-069

### TR-069 User Management

The actual user accounts are managed via TR-069 parameters:
- `Device.Users.User.{i}.Username` - typically `"admin"` for the GUI user
- `Device.Users.User.{i}.Password` - encrypted/hashed password value

When tests set a new password via SPV, they're updating the TR-069 data model, which PrplOS then applies to the system.

## Why Cleanup Uses 'admin'

The cleanup process in [`conftest.py:333-342`](file:///home/rjvisser/projects/req-tst/boardfarm-bdd/conftest.py#L333-L342) restores passwords to `"admin"` because:

1. **Cannot decrypt**: GPV returns encrypted passwords, SPV expects plaintext
2. **Known default**: `"admin"` is the documented default for PrplOS
3. **Boardfarm convention**: All PrplOS devices use `admin:admin` as baseline

This aligns with the Boardfarm framework's assumption that `"admin"` is the default password.

## Configuration Hierarchy

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

## Verification

To verify the actual default password in your environment:

1. **Start a fresh PrplOS container** (no tests run)
2. **Query via TR-069**:
   ```python
   # Find admin user
   admin_idx = discover_admin_user_index(acs, cpe)
   
   # Get current password (will be encrypted)
   password = gpv_value(acs, cpe, f"Device.Users.User.{admin_idx}.Password")
   print(f"Encrypted password: {password}")
   ```
3. **Try logging in** via GUI with `admin:admin`

## Conclusion

The default password `"admin"` is:
- ✅ **Hardcoded in Boardfarm3** framework as fallback
- ✅ **Assumed to be PrplOS factory default** (from upstream image)
- ❌ **NOT explicitly configured** in Raikou-Net or container setup
- ✅ **Correct choice for cleanup** restoration

The cleanup process using `"admin"` is the right approach given this architecture.

## Related Files

- Framework defaults: [`boardfarm3/lib/gui/prplos/pages/page_helper.py`](file:///home/rjvisser/projects/req-tst/boardfarm/boardfarm3/lib/gui/prplos/pages/page_helper.py)
- Device property: [`boardfarm3/devices/prplos_cpe.py`](file:///home/rjvisser/projects/req-tst/boardfarm/boardfarm3/devices/prplos_cpe.py)
- Config example: [`boardfarm-bdd/bf_config/boardfarm_config_example.json`](file:///home/rjvisser/projects/req-tst/boardfarm-bdd/bf_config/boardfarm_config_example.json)
- Cleanup logic: [`boardfarm-bdd/conftest.py`](file:///home/rjvisser/projects/req-tst/boardfarm-bdd/conftest.py)
- PrplOS container: [`raikou-net/components/cpe/prplos/Dockerfile`](file:///home/rjvisser/projects/req-tst/raikou-net/components/cpe/prplos/Dockerfile)
