# Firmware Image Requirements for PrplOS Verification

## Overview

This document describes the requirements that firmware image files must meet to successfully pass PrplOS verification during the upgrade process. Understanding these requirements is essential for preparing firmware images that will be accepted by the PrplOS upgrade system.

## PrplOS Validation Process

PrplOS performs firmware validation through `/usr/libexec/validate_firmware_image`, which checks:

1. **Digital Signature**: Verifies cryptographic signature using `fwtool_check_signature`
2. **Device Compatibility**: Verifies device metadata match using `fwtool_check_image`
3. **Platform Compatibility**: Calls `platform_check_image()` for platform-specific checks

The validation returns a JSON result indicating whether the image is valid, forceable, and allows backup preservation.

## Firmware Image Requirements

### 1. Basic Image Structure

#### **Boot Sector Signature**
- **Requirement**: Image must start with a valid boot sector signature
- **x86/64 Systems**: Must start with `0xeb63` (or `0xeb48` for some variants)
- **Verification**:
  ```bash
  hexdump -C firmware.img | head -1
  # Expected: 00000000 eb 63 90 00 00 00 00 00 00 00 00 00 00 00 00 00
  ```

#### **Partition Table**
- **Requirement**: Must contain a valid GPT (GUID Partition Table) or MBR partition table
- **Standard Layout**: 
  - Partition 1: Boot partition (typically FAT32 or ext4)
  - Partition 2: Root filesystem (SquashFS)
- **Verification**:
  ```bash
  sfdisk -d firmware.img
  # Should show valid partition table with partition 2 containing rootfs
  ```

#### **Root Filesystem Format**
- **Requirement**: Rootfs partition (partition 2) must contain a valid SquashFS filesystem
- **Verification**:
  ```bash
  # Extract partition offset
  offset=$(sfdisk -d firmware.img | grep "firmware.img2" | sed -E 's/.*start=\s+([0-9]+).*/\1/g')
  
  # Verify SquashFS structure
  unsquashfs -l -offset $(( 512 * offset )) firmware.img | head -20
  # Should show valid filesystem structure with directories like /bin, /etc, /usr
  ```

### 2. Security Requirements

#### **Digital Signature**
- **Requirement**: Image should be cryptographically signed with a valid certificate
- **Signature Format**: Uses `fwtool` signature format (`.ucert` certificate)
- **Verification Keys**: Must be verifiable against trusted keys in `/etc/opkg/keys`
- **Check Signature**:
  ```bash
  fwtool -s /tmp/signature.ucert firmware.img
  # Should extract signature if present
  ```
- **Note**: Images without signatures can still be installed using `--force` flag, but this bypasses security validation

#### **Signature Verification Process**
- PrplOS calls `fwtool_check_signature` which:
  - Extracts signature from image metadata
  - Verifies signature against trusted keys
  - Returns error code if signature is invalid or missing

### 3. Metadata Requirements

#### **Device Compatibility Metadata**
- **Requirement**: Image must contain metadata specifying supported devices
- **Metadata Format**: JSON embedded in firmware image using `fwtool`
- **Required Fields**:
  ```json
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
  ```

#### **Board Name Matching**
- **Requirement**: Metadata must include the target board name
- **Container Environment**: Uses `asus-all-series` (from `/tmp/sysinfo/board_name`)
- **Case Sensitivity**: Device names must match exactly (lowercase)
- **Check Metadata**:
  ```bash
  fwtool -i /tmp/metadata.json firmware.img
  cat /tmp/metadata.json
  # Should show device compatibility information
  ```

#### **Version Information**
- **Requirement**: Should include version and compatibility information
- **Fields**: `version`, `compat_version` help determine upgrade compatibility

### 4. Content Requirements

#### **Valid SquashFS Filesystem**
- **Requirement**: Rootfs partition must contain a valid, mountable SquashFS filesystem
- **Contents**: Must include essential system directories and files:
  - `/bin`, `/sbin` - Essential binaries
  - `/etc` - Configuration files
  - `/usr` - User programs and libraries
  - `/lib` - System libraries
  - `/sbin/init` - Init system

#### **Bootable System**
- **Requirement**: Must contain a functional init system (`/sbin/init`)
- **Requirement**: Must include basic utilities needed for system operation
- **Requirement**: Must be compatible with PrplOS boot process

#### **Architecture Compatibility**
- **Requirement**: Must match the target system architecture
- **Container Environment**: x86/64 architecture
- **Verification**: Check binary architecture:
  ```bash
  # After extracting rootfs
  file /new_rootfs_pending/bin/busybox
  # Should show: ELF 64-bit LSB executable, x86-64
  ```

## Validation Process Flow

### Step 1: Image Structure Check (`platform_check_image`)

PrplOS calls `platform_check_image()` which verifies:
- Magic word (boot sector signature)
- Partition table validity
- Partition layout compatibility

**Example Output**:
```
Valid image type
```

### Step 2: Signature Verification (`fwtool_check_signature`)

PrplOS verifies cryptographic signature:
- Extracts signature from image
- Verifies against trusted keys
- Returns success (0) or failure (non-zero)

**Example Output** (on success):
```
(no output - silent success)
```

**Example Output** (on failure):
```
Image signature not found
```

### Step 3: Device Compatibility Check (`fwtool_check_image`)

PrplOS verifies device metadata:
- Extracts metadata from image
- Compares with current device board name
- Returns success (0) or failure (non-zero)

**Example Output** (on success):
```
(no output - silent success)
```

**Example Output** (on failure):
```
Device asus-all-series not supported by this image
```

### Step 4: Validation Result

The validation script returns JSON:
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

## Preparing Firmware Images

### For Custom/Test Images

If you have a firmware image that lacks proper metadata, you can enhance it:

#### Step 1: Create Metadata Template

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

#### Step 2: Add Metadata to Image

```bash
# Add metadata to firmware image
fwtool -I metadata.json firmware.img

# Verify metadata was added
fwtool -i /tmp/verify.json firmware.img
cat /tmp/verify.json
```

#### Step 3: Validate Enhanced Image

```bash
# Test validation with enhanced image
/usr/libexec/validate_firmware_image firmware.img
# Should return: {"valid": true, "forceable": true, "allow_backup": true}
```

### For Production Images

Production firmware images should:
1. **Include Digital Signatures**: Sign images with trusted certificates
2. **Include Complete Metadata**: Ensure all required metadata fields are present
3. **Match Target Device**: Verify board name matches target device exactly
4. **Test Validation**: Run validation locally before deployment

## Validation Results Interpretation

### Successful Validation

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

**Meaning**: Image passes all checks and can be installed normally.

### Partial Validation (Forceable)

```json
{
    "tests": {
        "fwtool_signature": false,
        "fwtool_device_match": true
    },
    "valid": false,
    "forceable": true,
    "allow_backup": true
}
```

**Meaning**: Image fails signature check but can be installed with `--force` flag.

**Usage**:
```bash
sysupgrade --force firmware.img
```

### Failed Validation (Not Forceable)

```json
{
    "tests": {
        "fwtool_signature": false,
        "fwtool_device_match": false
    },
    "valid": false,
    "forceable": false,
    "allow_backup": true
}
```

**Meaning**: Image fails validation and cannot be installed even with `--force`.

## Common Validation Failures and Solutions

### Error: "Device not supported"

**Symptoms**:
```json
{
    "tests": {
        "fwtool_device_match": false
    },
    "valid": false
}
```

**Cause**: Board name mismatch in metadata

**Solution**:
1. Check current device board name:
   ```bash
   cat /tmp/sysinfo/board_name
   # Example output: asus-all-series
   ```

2. Update metadata with correct device name:
   ```bash
   # Create metadata with matching board name
   fwtool -I metadata.json firmware.img
   ```

3. Verify metadata:
   ```bash
   fwtool -i /tmp/check.json firmware.img
   grep -i "asus-all-series" /tmp/check.json
   ```

### Error: "Image signature not found"

**Symptoms**:
```json
{
    "tests": {
        "fwtool_signature": false
    },
    "valid": false,
    "forceable": true
}
```

**Cause**: Image lacks valid signature

**Solutions**:
1. **For Test Images**: Use `--force` flag to bypass signature check
   ```bash
   sysupgrade --force firmware.img
   ```

2. **For Production Images**: Sign image with trusted certificate
   ```bash
   # Sign image (requires signing key)
   fwtool -s signature.ucert firmware.img
   ```

### Error: "Invalid image type"

**Symptoms**: `platform_check_image()` fails

**Cause**: Corrupted image or invalid structure

**Solutions**:
1. Verify image integrity:
   ```bash
   # Check file size
   ls -lh firmware.img
   
   # Check magic word
   hexdump -C firmware.img | head -1
   ```

2. Verify partition table:
   ```bash
   sfdisk -d firmware.img
   ```

3. Rebuild image if corrupted

### Error: "Image metadata not present"

**Symptoms**: `fwtool -i` returns "Data not found"

**Cause**: Missing metadata in firmware image

**Solution**: Add metadata using `fwtool -I` (see "Preparing Firmware Images" section above)

## Container-Specific Considerations

### Device Name Mapping

The containerized testbed environment uses mock device names but requires actual board names in metadata:

- **Container Device**: Mock `/dev/sda`, `/dev/sda2` (not real FLASH)
- **Metadata Requirement**: Must specify actual target board name (e.g., `asus-all-series`)
- **Board Name Source**: `/tmp/sysinfo/board_name` in container
- **Case Sensitivity**: Device names must match exactly (lowercase)

### Validation Behavior

The containerized environment preserves native PrplOS validation:
- ✅ All validation checks run identically to native PrplOS
- ✅ Signature verification works the same way
- ✅ Device compatibility checks work the same way
- ✅ No container-specific validation modifications

### Force Flag Usage

In test environments, you may need to use `--force` for unsigned test images:

```bash
sysupgrade --force firmware.img
```

**Note**: This bypasses validation but preserves the native PrplOS upgrade process. Use only for test images, not production.

## Best Practices

1. **Always Include Metadata**: Even if validation passes without it, metadata ensures proper device compatibility
2. **Use Proper Device Names**: Match the exact board name from `/tmp/sysinfo/board_name`
3. **Test Validation Locally**: Run `/usr/libexec/validate_firmware_image` before deployment
4. **Preserve Signatures**: Maintain digital signatures for security validation in production
5. **Document Compatibility**: Keep track of which images work with which board configurations
6. **Verify Image Structure**: Check partition table and filesystem format before deployment
7. **Test Upgrade Process**: Validate end-to-end upgrade process in test environment before production

## Testing Validation

### Quick Validation Test

```bash
# On PrplOS CPE container:
/usr/libexec/validate_firmware_image /path/to/firmware.img

# Expected output for valid image:
# {"tests":{"fwtool_signature":true,"fwtool_device_match":true},"valid":true,"forceable":true,"allow_backup":true}
```

### Pre-Deployment Checklist

- [ ] Image has valid boot sector signature
- [ ] Image has valid partition table
- [ ] Rootfs partition contains valid SquashFS
- [ ] Metadata includes correct board name
- [ ] Metadata includes version information
- [ ] Image passes `/usr/libexec/validate_firmware_image`
- [ ] Image can be extracted and examined
- [ ] Image contains required system files (`/sbin/init`, etc.)

## Related Documentation

- **Rationale Document**: See "Firmware Image Requirements and Validation" section for detailed technical background
- **Intervention Points Analysis**: See validation flow in containerized environment
- **UC-12345**: See Extension 6.a for validation failure scenarios

## Summary

Firmware images must meet these requirements to pass PrplOS verification:

1. ✅ **Valid Structure**: Boot sector signature, partition table, SquashFS rootfs
2. ✅ **Device Compatibility**: Metadata matching target board name
3. ✅ **Security**: Digital signature (optional for test images, required for production)
4. ✅ **Content**: Bootable system with required files and architecture match

Images that fail validation can often be installed with `--force` flag (if `forceable: true`), but this bypasses security checks and should only be used for test images.

