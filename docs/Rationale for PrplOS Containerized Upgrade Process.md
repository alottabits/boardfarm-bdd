# Rationale for PrplOS Containerized Upgrade Process

## Summary

A multi-stage, self-healing process was designed to simulate a software upgrade for the containerized PrplOS device. The final architecture uses a "Wrapper + Hook" strategy to intercept the native PrplOS upgrade process. This approach is highly robust and future-proof, as it executes the official `sysupgrade` script, preserving all its validation logic, while injecting our container-specific behavior at the precise moment it's needed.

This intercepted process seamlessly connects to a self-healing mechanism, orchestrated by a simulated bootloader (`/docker-entrypoint.sh`), which makes the container an autonomous unit capable of recovering from a failed upgrade without external intervention.

## The "Wrapper + Hook" Upgrade Initiation

To guard against future changes in the PrplOS upgrade scripts, the initial stage of the upgrade does not replace the official `/sbin/sysupgrade` script, but rather intercepts its final step.

1.  **Renaming:** The `Dockerfile` renames the original `/sbin/sysupgrade` to `/sbin/sysupgrade.orig`.
2.  **The Wrapper:** A thin wrapper script is placed at `/sbin/sysupgrade`. When triggered by the high-level `ubus` call, its only job is to handle a potential URL by downloading the firmware to a local file. It then uses `exec` to hand off control to the original `/sbin/sysupgrade.orig` script.
3.  **The Hook:** A platform hook script (`container-hooks.sh`) is placed in `/lib/upgrade/`. The original `sysupgrade.orig` script is designed to automatically source any scripts in this directory. Our hook script defines a function called `platform_do_upgrade`.
4.  **The Interception:** The `sysupgrade.orig` script runs all of its internal validation logic. When it reaches the final step where it would normally write to flash memory, it instead calls our `platform_do_upgrade` function. This function executes our custom logic: it extracts the new root filesystem to `/new_rootfs_pending` and creates the `/boot/.do_upgrade` flag.
5.  **Reboot:** The `sysupgrade.orig` script then completes its execution and reboots the device, initiating the self-healing phase.

## Native PrplOS Process Preservation

The containerized upgrade process maintains **maximum compatibility** with the native PrplOS upgrade flow by leveraging the exact same functions and processes that PrplOS uses internally.

### **Native PrplOS Image Processing Flow:**

1. **Image Parsing:** Uses `get_partitions()` function to parse GPT partition tables using `dd` and `hexdump`
2. **Partition Extraction:** Uses `get_image_dd()` function to extract raw partition data from firmware images
3. **Block Device Writing:** Writes raw partition data directly to block devices (e.g., `/dev/sda2`)
4. **Filesystem Mounting:** At boot time, the kernel mounts the partition as the root filesystem

### **Container Adaptation Strategy:**

Instead of reimplementing complex partition parsing logic, our approach **intercepts only at the block device write point** and redirects the output to a file:

1. **Native Functions:** Uses the exact same `get_partitions()` and `get_image_dd()` functions that PrplOS uses
2. **Raw Partition Data:** Extracts the same raw partition data that would be written to flash memory
3. **Loop Device Mounting:** Uses PrplOS's built-in loop device support (`/dev/loop0-37`) to mount SquashFS images
4. **Filesystem Operations:** Performs standard Linux filesystem operations to install the new rootfs

### **Key Advantages:**

- **Future-Proof:** Automatically inherits any improvements to PrplOS partition handling
- **Minimal Code:** Only ~40 lines vs. 100+ lines of custom implementation
- **Native Compatibility:** Uses battle-tested PrplOS code paths
- **No External Dependencies:** Uses only tools already present in PrplOS
- **Security Preservation:** Maintains all validation and signature checking

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

### **Container Adaptation for Configuration Preservation:**

Instead of implementing custom configuration restoration logic, our approach **intercepts only at the configuration backup preservation point**:

1. **Native Backup Creation:** PrplOS creates `/tmp/sysupgrade.tgz` using its standard process
2. **Hook Preservation:** Our container hooks preserve this backup alongside the rootfs image
3. **Native Restoration:** PrplOS handles configuration restoration during boot using its proven logic
4. **User Account Merging:** PrplOS's sophisticated user account preservation ensures no data loss

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

## The Self-Healing Mechanism

The rest of the process is a state machine managed by the `/docker-entrypoint.sh` script, using flags in `/boot`.

### Stage 1: Upgrade Activation & Watchdog Arming (Entrypoint)

On boot, the entrypoint script detects the `/boot/.do_upgrade` flag and proceeds to:
1.  Back up the current root filesystem to `/old_root`.
2.  Move the new filesystem from `/new_rootfs_pending` into place.
3.  **Arm the recovery mechanism:** It creates a new flag, `/boot/.upgrade_in_progress`, and launches a background `/upgrade-watchdog.sh` script.
4.  It removes the `.do_upgrade` flag and proceeds to boot the new firmware.

### Stage 2: Health Check (Live System)

A service script (`/etc/init.d/health-check`) runs and, if it sees the `.upgrade_in_progress` flag, it polls for a successful boot (e.g., WAN interface is up). If the check passes, it creates a `/boot/.boot_successful` flag and removes the `.upgrade_in_progress` flag, marking the upgrade as complete.

### Stage 3: Automatic Rollback (Watchdog & Entrypoint)

The `/upgrade-watchdog.sh` script acts as a dead man's switch. After a timeout, it checks for the `/boot/.boot_successful` flag. If the flag is missing, it forces a reboot. On this next boot, the entrypoint script sees that the `.upgrade_in_progress` flag is still present, which is the definitive signal of a failed boot. It then triggers the rollback: restoring the backup from `/old_root`, clearing all flags, and booting safely with the original firmware.
