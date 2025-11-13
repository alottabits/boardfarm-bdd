# Rationale for PrplOS Containerized Upgrade Process

## Summary

A minimal-intervention approach was designed to enable validation of UC-12345 firmware upgrade behavior in a containerized testbed environment. The architecture uses a "Wrapper + Hook" strategy to bridge the gap where containerization prevents normal PrplOS operations (specifically, writing to FLASH memory), while preserving all native PrplOS behavior for validation purposes.

The testbed's purpose is to validate that the CPE, ACS, and file server components perform their usual activities correctly, not to simulate production behavior. Where containerization creates gaps (e.g., no FLASH memory), we use minimal hooks to bridge those gaps without interfering with the native PrplOS upgrade process.

## Purpose: Enabling Validation, Not Simulation

The containerized testbed is designed to **validate** UC-12345 firmware upgrade behavior, not to simulate a production environment. The testbed must allow:

- **CPE**: To perform its normal upgrade activities (TR-069 processing, firmware validation, config backup creation)
- **ACS**: To perform its normal management activities (issuing Download RPCs, receiving status updates)
- **File Server**: To serve firmware images via standard protocols (TFTP/HTTP)

### **Minimal Intervention Principle:**

We intervene **only** where containerization prevents normal operation. Containerization creates two fundamental gaps:

1. **No FLASH memory**: In a real CPE, firmware is written to dedicated FLASH partitions. In a container, we store the firmware image and extract/apply it at boot time.
2. **`/tmp` cleared on restart**: PrplOS creates config backup in `/tmp/sysupgrade.tgz`, but `/tmp` is cleared on container restart. We preserve it to `/boot/sysupgrade.tgz` and restore it before PrplOS boot continues.

**What PrplOS Does Natively** (we do NOT modify):

- ✅ TR-069 processing (receives Download RPC, downloads firmware, reports status)
- ✅ Firmware validation (signature, device compatibility, partition structure)
- ✅ Configuration backup creation (`/tmp/sysupgrade.tgz` with user settings and accounts)
- ✅ Configuration restoration (during boot from `/sysupgrade.tgz`)

**What We Do** (bridging containerization gaps):

- ✅ Store firmware image to persistent location (`/firmware/pending/`) instead of writing to FLASH
- ✅ Preserve config backup (`/tmp/sysupgrade.tgz` → `/boot/sysupgrade.tgz`) before reboot
- ✅ Extract rootfs using `unsquashfs` directly (no loop devices) and apply at boot time
- ✅ Restore config backup to where PrplOS expects it (`/sysupgrade.tgz`)

**Key Point**: We do **NOT** perform firmware installation in the PrplOS sense (writing to FLASH). Instead, we bridge the containerization gap by storing the firmware image and extracting/applying it at boot time. PrplOS still handles all validation, config backup creation, and config restoration natively.

## The "Hook + Entrypoint" Minimal Intervention Strategy

To enable validation of UC-12345 while preserving native PrplOS behavior, we use minimal hooks that bridge only the containerization gap (no FLASH memory). We do **not** replace PrplOS functionality; we only redirect operations that cannot work in a container.

**Key Principle**: Every hook should answer "Does containerization prevent this from working?" If yes, bridge the gap. If no, let PrplOS handle it natively.

### **Upgrade Flow:**

**PrplOS Native Process:**
1. **Native sysupgrade:** PrplOS `/sbin/sysupgrade` handles HTTP/HTTPS URLs natively - **we use the native script directly, no wrapper**.
2. **Firmware Validation:** PrplOS validates image signature, device compatibility, partition structure - **we do NOT modify this**.
3. **Config Backup Creation:** PrplOS creates `/tmp/sysupgrade.tgz` with user settings and accounts - **we do NOT modify this**.
4. **Platform Hook Call:** PrplOS calls `platform_do_upgrade()` function (normally writes to FLASH) - **we intercept this**.

**Container Bridge:**

1. **The Interception:** Our hook script (`z-container-hooks.sh`) overrides `platform_do_upgrade()` and bridges the containerization gap:
   - Stores full firmware image to `/firmware/pending/firmware_<timestamp>.img` (instead of writing to FLASH)
   - Preserves config backup: `/tmp/sysupgrade.tgz` → `/boot/sysupgrade.tgz` (since `/tmp` is cleared on restart)
   - Creates `/boot/.do_upgrade` flag with firmware image path
2. **Reboot:** PrplOS `sysupgrade` script completes its execution and reboots the device - **we do NOT modify this**.
3. **Boot-Time Application:** The container entrypoint (`/docker-entrypoint.sh`) detects the upgrade flag, extracts rootfs using `unsquashfs` directly on the firmware image, restores config backup to `/sysupgrade.tgz`, applies the new filesystem, and continues boot.

**PrplOS Native Process:**

1. **Configuration Restoration:** PrplOS `/lib/preinit/80_mount_root` detects `/sysupgrade.tgz` and restores configuration automatically - **we do NOT modify this**.

### **Key Advantages:**

- **Future-Proof:** Automatically inherits any improvements to PrplOS partition handling
- **Minimal Code:** Only ~40 lines vs. 100+ lines of custom implementation
- **Native Compatibility:** Uses battle-tested PrplOS code paths
- **No External Dependencies:** Uses only tools already present in PrplOS
- **Security Preservation:** Maintains all validation and signature checking
- **Validation-Focused:** Enables validation of PrplOS behavior without simulating production systems

## Native PrplOS Configuration Preservation

The containerized upgrade process leverages PrplOS's **native configuration preservation mechanism** to maintain user settings across firmware upgrades. We only bridge the gap where `/tmp` is cleared on container restart.

**PrplOS Native Process:**
- During `sysupgrade`, PrplOS automatically creates `/tmp/sysupgrade.tgz` containing user configuration files, modified package configs, user accounts, and custom files specified in `/etc/sysupgrade.conf` and `/lib/upgrade/keep.d/`
- During boot, PrplOS's `/lib/preinit/80_mount_root` script detects `/sysupgrade.tgz`, extracts the configuration archive, and merges user accounts using sophisticated logic

**Container Handling:**
- Our hook preserves `/tmp/sysupgrade.tgz` to `/boot/sysupgrade.tgz` before reboot (since `/tmp` is cleared on container restart)
- Our entrypoint restores `/boot/sysupgrade.tgz` to `/sysupgrade.tgz` and `/tmp/sysupgrade.tgz` before applying new rootfs
- PrplOS then handles configuration restoration automatically during boot using its proven logic

**Configuration Preserved:** Network settings (WiFi SSIDs, passwords), system configuration (hostname, timezone, IP addresses), user accounts (SSH keys, passwords), and custom files specified in configuration.

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
| 5. CPE downloads firmware | TR-069 client handles download | **None** - PrplOS `/sbin/sysupgrade` handles HTTP/HTTPS URLs natively (no wrapper script) |
| 6. CPE validates firmware | Native validation logic | **None** - PrplOS handles validation |
| 7. CPE installs & reboots | Native installation logic (writes to FLASH) | **Bridge gap** - Store firmware image, extract/apply at boot |
| 8. CPE reconnects to ACS | Native TR-069 reconnection | **None** - PrplOS handles reconnection |
| 9. ACS reflects version | Native TR-069 reporting | **None** - PrplOS handles reporting |

**Note on Step 7**: In native PrplOS, "installation" means writing firmware to FLASH partitions. In containers, we bridge this gap by storing the firmware image and extracting/applying the rootfs at boot time. PrplOS still handles all validation, config backup creation, and config restoration natively.

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
