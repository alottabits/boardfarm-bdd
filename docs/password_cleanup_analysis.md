# Password Cleanup Issue Analysis

## Problem Summary

The cleanup process retrieves the original password value using `gpv_value()`, which returns the **encrypted/hashed representation** of the password from the TR-069 parameter `Device.Users.User.X.Password`. When cleanup attempts to restore this encrypted value via SPV, it fails because:

1. **SPV expects plaintext passwords** - The TR-069 SPV (Set Parameter Values) operation expects to receive plaintext passwords that it will then encrypt/hash
2. **GPV returns encrypted passwords** - The TR-069 GPV (Get Parameter Values) operation returns the already-encrypted/hashed password value
3. **Cannot decrypt** - There's no way to decrypt the hashed password back to plaintext

This creates an impossible situation: we can't restore the original password because we don't know what the plaintext value was.

## Current Workaround

The code already implements a workaround in [`conftest.py:333-342`](file:///home/rjvisser/projects/req-tst/boardfarm-bdd/conftest.py#L333-L342):

```python
# Handle password restoration specially - SPV expects plaintext, not encrypted hash
# We restore to the default "admin" password since we can't restore from encrypted value
if "password" in field_name.lower():
    print(
        f"  ✓ Found password field '{field_name}' - "
        f"Restoring for {config_name} {item_idx} "
        f"to default 'admin' password "
        f"(cannot restore from encrypted hash)"
    )
    restore_value = "admin"  # Default PrplOS password
```

**This workaround restores passwords to the default "admin" value instead of the original encrypted value.**

## Why This Happens

### In `background_steps.py` (Lines 139-152)

When capturing the original password:

```python
original_password = gpv_value(
    acs, cpe, f"Device.Users.User.{admin_user_idx}.Password"
)
```

This retrieves the **encrypted** password value, not the plaintext.

### In `conftest.py` (Lines 330-354)

During cleanup, the code attempts to restore using SPV:

```python
restore_params[gpv_param] = restore_value
result = acs.SPV(spv_params, cpe_id=cpe_id, timeout=60)
```

SPV expects plaintext passwords that it will encrypt, but without the workaround, it would receive an already-encrypted value.

## Recommended Solutions

### Option 1: Current Workaround (Already Implemented) ✅

**Status**: Already in place and working

**Pros**:
- Simple and reliable
- Guarantees a known working password state
- No risk of password restore failures

**Cons**:
- Doesn't restore the actual original password
- May cause issues if tests depend on specific password values persisting

**Recommendation**: This is acceptable for most test scenarios where the default "admin" password is the baseline state.

---

### Option 2: Track Plaintext Passwords in Test Context

**Implementation**: Store the plaintext password when it's set, not the encrypted value from GPV.

**Changes Required**:

#### In `background_steps.py`:

```python
@given('the user has set the CPE GUI password to "{password}"')
def user_sets_cpe_gui_password(
    acs: AcsTemplate,
    cpe: CpeTemplate,
    bf_context: Any,
    password: str,
) -> None:
    # ... existing code ...
    
    # Instead of capturing encrypted password from GPV:
    # original_password = gpv_value(acs, cpe, f"Device.Users.User.{admin_user_idx}.Password")
    
    # Store the plaintext password we're setting FROM:
    if not hasattr(bf_context, 'admin_password_before_change'):
        # First time - assume default password
        bf_context.admin_password_before_change = "admin"
    
    original_password = bf_context.admin_password_before_change
    
    # ... set new password via SPV ...
    
    # Store for cleanup
    items[str(admin_user_idx)]["Password"] = {
        "gpv_param": f"Device.Users.User.{admin_user_idx}.Password",
        "value": original_password  # Plaintext password
    }
    
    # Update the tracked password for next change
    bf_context.admin_password_before_change = password
```

#### In `conftest.py`:

```python
# Remove the special password handling - just restore normally
restore_value = str(original_value)
restore_params[gpv_param] = restore_value
```

**Pros**:
- Restores actual original password
- More accurate test isolation
- Supports scenarios with multiple password changes

**Cons**:
- Requires tracking password state across test steps
- Assumes we know the initial password (must be documented)
- More complex implementation

---

### Option 3: Don't Capture Password Initially

**Implementation**: Only track password changes when we explicitly set them, assume default otherwise.

**Changes Required**:

#### In `background_steps.py`:

```python
# Don't try to capture original password via GPV
# Just assume it's "admin" (the default)
original_password = "admin"

# Store for cleanup
items[str(admin_user_idx)]["Password"] = {
    "gpv_param": f"Device.Users.User.{admin_user_idx}.Password",
    "value": "admin"  # Known default
}
```

**Pros**:
- Simplest implementation
- No GPV call needed
- Reliable restoration

**Cons**:
- Assumes default password is always "admin"
- Won't work if initial state has different password
- Less robust than Option 2

---

### Option 4: Skip Password Cleanup Entirely

**Implementation**: Don't restore passwords at all, rely on container/testbed reset.

**Changes Required**:

```python
# In conftest.py, skip password fields entirely
if "password" in field_name.lower():
    print(f"  ⚠ Skipping password field '{field_name}' - cannot restore encrypted values")
    continue
```

**Pros**:
- Avoids the problem entirely
- No risk of password restore failures

**Cons**:
- Password changes persist between tests
- Requires manual cleanup or container restart
- Poor test isolation

---

## Recommendation

**Use Option 1 (Current Workaround)** for most scenarios, as it's already implemented and working.

**Consider Option 2** if:
- Tests require specific password values to persist
- Multiple password changes occur within a single test
- You need true restoration of original passwords

**Implementation Priority**:
1. ✅ **Keep current workaround** (Option 1) - Already working
2. 📋 **Document the limitation** - Add note to cleanup documentation
3. 🔄 **Consider Option 2** - Only if test requirements demand it

## Additional Considerations

### Security Note

Storing plaintext passwords in test context (Option 2) is acceptable for test environments but should be clearly documented. The passwords are:
- Only in memory during test execution
- Not persisted to disk
- Only used in isolated test environments

### TR-069 Protocol Limitation

This is a fundamental limitation of the TR-069 protocol:
- **GPV** returns encrypted/hashed values for security
- **SPV** expects plaintext values to encrypt
- There's no "decrypt" operation available

This means **true password restoration is impossible** without tracking the plaintext values ourselves.

## Files Involved

- [`conftest.py:333-342`](file:///home/rjvisser/projects/req-tst/boardfarm-bdd/conftest.py#L333-L342) - Current workaround implementation
- [`background_steps.py:139-152`](file:///home/rjvisser/projects/req-tst/boardfarm-bdd/tests/step_defs/background_steps.py#L139-L152) - Original password capture
- [`background_steps.py:225-234`](file:///home/rjvisser/projects/req-tst/boardfarm-bdd/tests/step_defs/background_steps.py#L225-L234) - Cleanup config storage
- [`helpers.py:15-29`](file:///home/rjvisser/projects/req-tst/boardfarm-bdd/tests/step_defs/helpers.py#L15-L29) - GPV helper function
