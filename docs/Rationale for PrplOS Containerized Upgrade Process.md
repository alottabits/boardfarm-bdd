# Rationale for PrplOS Containerized Upgrade Process

## Summary

A minimal-intervention approach was designed to enable validation of UC-12345 firmware upgrade behavior in a containerized testbed environment. The architecture uses a "Wrapper + Hook" strategy to bridge the gap where containerization prevents normal PrplOS operations (specifically, writing to FLASH memory), while preserving all native PrplOS behavior for validation purposes.

The testbed's purpose is to validate that the CPE, ACS, and file server components perform their usual activities correctly, not to simulate production behavior. Where containerization creates gaps (e.g., no FLASH memory), we use minimal hooks to bridge those gaps without interfering with the native PrplOS upgrade process.

## Purpose: Enabling Validation, Not Simulation

The containerized testbed is designed to **validate** UC-12345 firmware upgrade behavior, not to simulate a production environment. The testbed must allow:

- **CPE**: To perform its normal upgrade activities (TR-069 processing, firmware validation, installation)
- **ACS**: To perform its normal management activities (issuing Download RPCs, receiving status updates)
- **File Server**: To serve firmware images via standard protocols (TFTP/HTTP)

### **The Containerization Gap:**

Containerization creates one fundamental gap: **no FLASH memory**. In a real CPE, firmware is written to dedicated FLASH partitions. In a container, we must bridge this gap with minimal intervention.

### **Minimal Intervention Principle:**

We intervene **only** where containerization prevents normal operation:
- ✅ **Intercept FLASH writes**: Redirect to container filesystem operations
- ✅ **Handle URL downloads**: Convert TR-069 URLs to local file paths
- ❌ **Do NOT build self-healing mechanisms**: That's what we're validating, not simulating
- ❌ **Do NOT modify TR-069 behavior**: PrplOS handles this natively
- ❌ **Do NOT change validation logic**: PrplOS handles this natively

The goal is to enable validation of UC-12345's Main Success Scenario and Extensions, ensuring that PrplOS's native upgrade process works correctly in a containerized test environment.

## The "Wrapper + Hook" Minimal Intervention Strategy

To enable validation of UC-12345 while preserving native PrplOS behavior, we use minimal hooks that bridge only the containerization gap (no FLASH memory). We do **not** replace PrplOS functionality; we only redirect operations that cannot work in a container.

**Key Principle**: Every hook should answer "Does containerization prevent this from working?" If yes, bridge the gap. If no, let PrplOS handle it natively.

1.  **Renaming:** The `Dockerfile` renames the original `/sbin/sysupgrade` to `/sbin/sysupgrade.orig`.
2.  **The Wrapper:** A thin wrapper script is placed at `/sbin/sysupgrade`. When triggered by the high-level `ubus` call or TR-069 Download command, its only job is to handle a potential URL by downloading the firmware to a local file. It then uses `exec` to hand off control to the original `/sbin/sysupgrade.orig` script.
3.  **The Hook:** A platform hook script (`container-hooks.sh`) is placed in `/lib/upgrade/`. The original `sysupgrade.orig` script is designed to automatically source any scripts in this directory. Our hook script defines a function called `platform_do_upgrade`.
4.  **The Interception:** The `sysupgrade.orig` script runs all of its internal validation logic (signature verification, device compatibility, etc.). When it reaches the final step where it would normally write to flash memory, it instead calls our `platform_do_upgrade` function. This function bridges the containerization gap: it extracts the new root filesystem to `/new_rootfs_pending` and creates the `/boot/.do_upgrade` flag.
5.  **Reboot:** The `sysupgrade.orig` script then completes its execution and reboots the device. The container entrypoint applies the new filesystem at boot time.

## Native PrplOS Process Preservation

The containerized upgrade process maintains **maximum compatibility** with the native PrplOS upgrade flow by leveraging the exact same functions and processes that PrplOS uses internally.

### **Native PrplOS Image Processing Flow:**

1. **Image Parsing:** Uses `get_partitions()` function to parse GPT partition tables using `dd` and `hexdump`
2. **Partition Extraction:** Uses `get_image_dd()` function to extract raw partition data from firmware images
3. **Block Device Writing:** Writes raw partition data directly to block devices (e.g., `/dev/sda2`)
4. **Filesystem Mounting:** At boot time, the kernel mounts the partition as the root filesystem

### **Bridging the Containerization Gap:**

The **only** gap containerization creates is the absence of FLASH memory. We bridge this gap at the precise point where PrplOS would write to FLASH:

1. **Native Functions:** Uses the exact same `get_partitions()` and `get_image_dd()` functions that PrplOS uses
2. **Raw Partition Data:** Extracts the same raw partition data that would be written to flash memory
3. **Gap Bridge:** Instead of writing to `/dev/sda2` (FLASH), we write to a container filesystem location (`/new_rootfs_pending`)
4. **Boot-Time Application:** The container entrypoint (`/docker-entrypoint.sh`) applies the new filesystem at boot time

**Key Point**: This is the **only** modification to PrplOS behavior. Everything else (validation, TR-069, configuration preservation) works exactly as PrplOS designed it.

### **Key Advantages:**

- **Future-Proof:** Automatically inherits any improvements to PrplOS partition handling
- **Minimal Code:** Only ~40 lines vs. 100+ lines of custom implementation
- **Native Compatibility:** Uses battle-tested PrplOS code paths
- **No External Dependencies:** Uses only tools already present in PrplOS
- **Security Preservation:** Maintains all validation and signature checking
- **Validation-Focused:** Enables validation of PrplOS behavior without simulating production systems

## Native PrplOS Configuration Preservation

The containerized upgrade process leverages PrplOS's **native configuration preservation mechanism** to maintain user settings across firmware upgrades, ensuring a seamless user experience without requiring manual reconfiguration.

### **Native PrplOS Configuration Flow:**

1. **Configuration Backup Creation:** During `sysupgrade`, PrplOS automatically creates `/tmp/sysupgrade.tgz` containing:
   - User configuration files from `/etc/config/` (wireless, network, system settings)
   - Modified package configuration files
   - User account information (`/etc/passwd`, `/etc/group`, `/etc/shadow`)
   - Custom files specified in `/etc/sysupgrade.conf` and `/lib/upgrade/keep.d/`

2. **Configuration Restoration:** During boot, PrplOS's `/lib/preinit/80_mount_root` script:
   - Detects `/sysupgrade.tgz` or `/tmp/sysupgrade.tar`
   - Preserves existing user accounts by backing them up to `/tmp`
   - Extracts the configuration archive to `/`
   - Merges user accounts using sophisticated `missing_lines()` logic
   - Syncs filesystem to prevent corruption

### **Container Handling for Configuration Preservation:**

Configuration preservation requires **no container-specific modifications**. PrplOS handles this entirely natively:

1. **Native Backup Creation:** PrplOS creates `/tmp/sysupgrade.tgz` using its standard process
2. **Native Preservation:** The container filesystem preserves this backup across container restarts (standard Docker behavior)
3. **Native Restoration:** PrplOS handles configuration restoration during boot using its proven logic (`/lib/preinit/80_mount_root`)
4. **User Account Merging:** PrplOS's sophisticated user account preservation ensures no data loss

**Key Point**: Configuration preservation is validated exactly as it works in native PrplOS deployments. The testbed enables this validation without any modifications.

### **Configuration Files Preserved:**

- **Network Settings:** WiFi SSIDs, passwords, security settings (`/etc/config/wireless`)
- **System Configuration:** Hostname, timezone, IP addresses (`/etc/config/network`, `/etc/config/system`)
- **User Accounts:** SSH keys, user passwords, group memberships (`/etc/dropbear/`, `/etc/passwd`)
- **Custom Settings:** Any files specified in `/etc/sysupgrade.conf` and `/lib/upgrade/keep.d/`

### **Benefits of Native Configuration Preservation:**

- **Zero User Intervention:** Users don't need to reconfigure WiFi, passwords, or network settings
- **Proven Reliability:** Uses PrplOS's battle-tested configuration preservation logic
- **Account Safety:** Sophisticated user account merging prevents data loss
- **Future Compatibility:** Automatically inherits any PrplOS configuration improvements
- **No Configuration Conflicts:** Eliminates infinite loops caused by configuration mismatches

## Firmware Image Requirements and Validation

For a firmware image to successfully pass through the PrplOS upgrade process, it must meet specific requirements that are validated at multiple stages. Understanding these requirements is crucial for ensuring compatibility and successful upgrades.

### **PrplOS Firmware Image Requirements:**

#### **1. Basic Image Structure:**
- **Magic Word**: Must start with valid boot sector signature (e.g., `0xeb63` for x86)
- **Partition Table**: Must contain a valid GPT partition table
- **Rootfs Partition**: Must have rootfs data in partition 2 (standard PrplOS layout)
- **Filesystem Format**: Rootfs must be in SquashFS format

#### **2. Security Requirements:**
- **Digital Signature**: Image should be signed with a valid certificate
- **Signature Verification**: Signature must be verifiable against trusted keys in `/etc/opkg/keys`

#### **3. Metadata Requirements:**
- **Device Compatibility**: Must contain metadata specifying supported devices
- **Version Information**: Should include version and compatibility information
- **Board Name Match**: Metadata must include the target board name (e.g., `asus-all-series`)

#### **4. Content Requirements:**
- **Valid SquashFS**: Rootfs partition must contain a valid SquashFS filesystem
- **Bootable System**: Must contain a functional init system and basic utilities
- **Compatible Architecture**: Must match the target system architecture (x86/64)

### **Pre-Validation Process:**

#### **Step 1: Basic Structure Validation**
```bash
# Check magic word
hexdump -C firmware.img | head -1
# Should show: 00000000 eb 63 90 00 00 00 00 00 00 00 00 00 00 00 00 00

# Check partition table
sfdisk -d firmware.img
# Should show valid GPT with partition 2 containing rootfs
```

#### **Step 2: Content Validation**
```bash
# Extract and examine rootfs
offset=$(sfdisk -d firmware.img | grep "firmware.img2" | sed -E 's/.*start=\s+([0-9]+).*/\1/g')
unsquashfs -l -offset $(( 512 * offset )) firmware.img | head -20
# Should show valid filesystem structure
```

#### **Step 3: Metadata and Signature Validation**
```bash
# Check for existing metadata
fwtool -i /tmp/metadata.json firmware.img
# If "Data not found", metadata needs to be added

# Check for signature
fwtool -s /tmp/signature.ucert firmware.img
# Should extract signature if present
```

### **Metadata Enhancement Process:**

If an image lacks proper metadata (common with custom builds), it can be enhanced using `fwtool`:

#### **Step 1: Create Metadata Template**
```bash
cat > metadata.json << 'EOF'
{
    "version": "3.0.3",
    "compat_version": "1.0",
    "supported_devices": {
        "asus-all-series": "asus-all-series"
    },
    "new_supported_devices": {
        "asus-all-series": "asus-all-series"
    }
}
EOF
```

#### **Step 2: Add Metadata to Image**
```bash
# Add metadata to firmware image
fwtool -I metadata.json firmware.img

# Verify metadata was added
fwtool -i /tmp/verify.json firmware.img
cat /tmp/verify.json
```

#### **Step 3: Validate Enhanced Image**
```bash
# Test validation with enhanced image
/usr/libexec/validate_firmware_image firmware.img
# Should return: {"valid": true, "forceable": true, "allow_backup": true}
```

### **Validation Results Interpretation:**

#### **Successful Validation Output:**
```json
{
    "tests": {
        "fwtool_signature": true,
        "fwtool_device_match": true
    },
    "valid": true,
    "forceable": true,
    "allow_backup": true
}
```

#### **Common Validation Failures:**
- **`fwtool_signature: false`**: Image lacks valid signature (can be forced with `--force`)
- **`fwtool_device_match: false`**: Board name mismatch in metadata
- **`valid: false`**: Image fails validation (may still be forceable)

### **Container-Specific Considerations:**

#### **Device Name Mapping:**
The container environment uses mock device names (`sda`, `sda2`) but the firmware metadata must still specify the actual target board name:
- **Container Board Name**: `asus-all-series` (from `/tmp/sysinfo/board_name`)
- **Metadata Requirement**: Must include `asus-all-series` in supported devices
- **Case Sensitivity**: Device names must match exactly (lowercase)

#### **Force Flag Usage:**
Images that fail validation can still be upgraded using the `--force` flag:
```bash
sysupgrade --force firmware.img
```
This bypasses validation but preserves the native PrplOS upgrade process.

### **Best Practices for Firmware Preparation:**

1. **Always Include Metadata**: Even if validation passes without it, metadata ensures proper device compatibility
2. **Use Proper Device Names**: Match the exact board name from `/tmp/sysinfo/board_name`
3. **Test Validation Locally**: Run `/usr/libexec/validate_firmware_image` before deployment
4. **Preserve Signatures**: Maintain digital signatures for security validation
5. **Document Compatibility**: Keep track of which images work with which board configurations

### **Troubleshooting Common Issues:**

#### **"Device not supported" Error:**
- **Cause**: Board name mismatch in metadata
- **Solution**: Update metadata with correct device name

#### **"Image metadata not present" Warning:**
- **Cause**: Missing metadata in firmware image
- **Solution**: Add metadata using `fwtool -I`

#### **"Invalid image type" Error:**
- **Cause**: Corrupted image or invalid structure
- **Solution**: Verify image integrity and structure

This validation process ensures that firmware images are compatible with the PrplOS upgrade system while maintaining the security and reliability standards expected in production environments.

## UC-12345 Validation Capabilities

The containerized testbed enables validation of UC-12345 requirements:

### **Main Success Scenario Validation:**

| UC Step | PrplOS Native Behavior | Testbed Intervention |
|---------|----------------------|---------------------|
| 5. CPE downloads firmware | TR-069 client handles download | Wrapper converts URL to local file |
| 6. CPE validates firmware | Native validation logic | **None** - PrplOS handles validation |
| 7. CPE installs & reboots | Native installation logic | Hook redirects FLASH write to filesystem |
| 8. CPE reconnects to ACS | Native TR-069 reconnection | **None** - PrplOS handles reconnection |
| 9. ACS reflects version | Native TR-069 reporting | **None** - PrplOS handles reporting |

### **Extension Validation:**

- **6.a (Validation Failure)**: PrplOS's native validation failure handling is preserved; testbed validates that PrplOS reports failures correctly to ACS
- **8.a (Rollback)**: If PrplOS has native rollback, testbed preserves it; if not, this is a PrplOS requirement, not a testbed simulation
- **10.a (Config Reset)**: Testbed validates PrplOS's native configuration preservation behavior

### **What We Do NOT Simulate:**

- ❌ Self-healing mechanisms (that's what we validate)
- ❌ TR-069 protocol behavior (PrplOS handles this)
- ❌ Firmware validation logic (PrplOS handles this)
- ❌ Configuration preservation (PrplOS handles this)
- ❌ ACS communication (PrplOS handles this)

The testbed provides the **minimal infrastructure** needed to validate that PrplOS performs these functions correctly.

## Container Boot-Time Upgrade Application

The container entrypoint (`/docker-entrypoint.sh`) handles the application of the new filesystem at boot time, bridging the containerization gap where FLASH operations would normally occur.

### **Upgrade Application Process:**

On boot, the entrypoint script detects the `/boot/.do_upgrade` flag (created by the hook during upgrade) and proceeds to:

1. **Backup Current Rootfs:** Back up the current root filesystem to `/old_root` for potential rollback validation
2. **Apply New Filesystem:** Move the new filesystem from `/new_rootfs_pending` into place
3. **Remove Flag:** Remove the `.do_upgrade` flag
4. **Continue Boot:** Proceed to boot the new firmware using PrplOS's standard boot process

**Key Point**: This process bridges the containerization gap (no FLASH) but does not implement production rollback mechanisms. If rollback validation is needed (UC-12345 Extension 8.a), it would be handled by PrplOS's native mechanisms, not by testbed simulation.

## Validating Rollback Behavior (UC-12345 Extension 8.a)

UC-12345 Extension 8.a specifies that "the device rolls back autonomously to the previous firmware and reboots" if provisioning fails after upgrade.

**Important**: The testbed does **not** implement this rollback mechanism. Instead, the testbed enables validation of whether PrplOS's native rollback behavior (if it exists) works correctly.

### **Containerization Impact on Rollback Validation:**

If PrplOS has native rollback capabilities, our container hooks must preserve that behavior:
- The hook's filesystem operations should not interfere with PrplOS's rollback detection
- Configuration preservation should work identically to native PrplOS
- Any rollback mechanisms in PrplOS should function normally
- The backup stored at `/old_root` enables validation of rollback behavior if PrplOS implements it

If PrplOS does **not** have native rollback capabilities, then Extension 8.a represents a requirement for PrplOS itself, not something the testbed should simulate.

### **Testbed Responsibility:**

The testbed's responsibility is to:
1. Enable the upgrade process to complete (bridging the FLASH gap)
2. Allow validation of post-upgrade behavior (ACS reconnection, provisioning)
3. Enable detection of upgrade failures (if PrplOS reports them natively)
4. Preserve any native PrplOS rollback mechanisms without modification
5. **NOT** to implement rollback mechanisms that PrplOS doesn't have

This ensures we validate actual PrplOS behavior, not simulated testbed behavior.
