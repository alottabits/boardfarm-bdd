# Manual Firmware Image Preparation and Upgrade Testing Guide

## Overview

This guide provides step-by-step instructions for preparing a firmware image for PrplOS upgrade and manually testing the upgrade process in the containerized testbed.

## Prerequisites

- CPE container is running and provisioned (`docker ps | grep cpe`)
- Firmware image file available in `tests/test_artifacts/`
- Access to the CPE container via Docker exec
- Basic understanding of Docker commands

## Part 1: Prepare Firmware Image

### Step 1: Verify Image Structure

First, verify that the image has the correct structure:

```bash
cd /home/rjvisser/projects/req-tst/boardfarm-bdd/tests/test_artifacts

# Check file exists and size
ls -lh openwrt-x86-64-generic-squashfs-combined-efi.img

# Check boot sector signature (should start with 0xeb63 or 0xeb48 for x86)
hexdump -C openwrt-x86-64-generic-squashfs-combined-efi.img | head -1
# Expected: 00000000 eb 63 90 00 ... or 00000000 eb 48 90 00 ...

# Check partition table
sfdisk -d openwrt-x86-64-generic-squashfs-combined-efi.img
# Should show valid GPT partition table with partition 2 (rootfs)
```

**Expected Output**:
```
Device                                    Start       End   Sectors  Size Type
openwrt-x86-64-generic-squashfs-combined-efi.img1      34      2047      2014  1007K EFI System
openwrt-x86-64-generic-squashfs-combined-efi.img2    2048    <end>    <size>  <size> Linux filesystem
```

### Step 2: Check Current Metadata

Check if the image already has metadata:

```bash
# Copy image to container
docker cp openwrt-x86-64-generic-squashfs-combined-efi.img cpe:/tmp/test_firmware.img

# Check for existing metadata
docker exec cpe fwtool -i /tmp/metadata_check.json /tmp/test_firmware.img

# View metadata if present
docker exec cpe cat /tmp/metadata_check.json 2>/dev/null || echo "No metadata found"
```

**If metadata exists**: Review it to ensure it includes the correct board name.

**If no metadata**: Proceed to Step 3 to add metadata.

### Step 3: Get Target Board Name

Determine the board name that the container expects:

```bash
# Check board name in container
docker exec cpe cat /tmp/sysinfo/board_name 2>/dev/null || \
docker exec cpe cat /proc/device-tree/model 2>/dev/null || \
echo "asus-all-series"  # Default for containerized testbed
```

**Expected Output**: `asus-all-series`

### Step 4: Create Metadata File

Create a metadata JSON file with the correct board name:

```bash
# Create metadata file
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

# Verify metadata file
cat metadata.json
```

**Note**: Adjust the `version` field to match your firmware version if different.

### Step 5: Add Metadata to Image

Add metadata to the firmware image using `fwtool`:

```bash
# Copy metadata to container
docker cp metadata.json cpe:/tmp/metadata.json

# Add metadata to firmware image
docker exec cpe fwtool -I /tmp/metadata.json /tmp/test_firmware.img

# Verify metadata was added
docker exec cpe fwtool -i /tmp/metadata_verify.json /tmp/test_firmware.img
docker exec cpe cat /tmp/metadata_verify.json
```

**Expected Output**:
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

### Step 6: Validate Image

Validate the image using PrplOS validation script:

```bash
# Run validation
docker exec cpe /usr/libexec/validate_firmware_image /tmp/test_firmware.img
```

**Expected Output** (successful validation):
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

**If validation fails**:
- Check that metadata includes the correct board name
- If `fwtool_signature: false`, this is OK for test images (can use `--force`)
- If `fwtool_device_match: false`, verify board name matches

### Step 7: Copy Prepared Image Back to Host

Copy the prepared image back to your host:

```bash
# Copy validated image back
docker cp cpe:/tmp/test_firmware.img ./openwrt-x86-64-generic-squashfs-combined-efi-prepared.img

# Verify file
ls -lh openwrt-x86-64-generic-squashfs-combined-efi-prepared.img
```

## Part 2: Prepare Test Environment

### Step 8: Copy Image to HTTP Server

Copy the prepared image to the WAN container's HTTP server:

```bash
# Copy image to WAN container (HTTP server)
docker cp openwrt-x86-64-generic-squashfs-combined-efi-prepared.img wan:/tftpboot/

# Verify image is accessible
docker exec wan ls -lh /tftpboot/openwrt-x86-64-generic-squashfs-combined-efi-prepared.img

# Get WAN container IP for URL
docker exec wan hostname -I | awk '{print $1}'
# Note this IP - you'll need it for the TR-069 Download URL
```

**Expected WAN IP**: `172.25.1.2` (check your docker-compose.yaml)

### Step 9: Verify HTTP Access

Test that the image is accessible via HTTP:

```bash
# Test HTTP access from CPE container
docker exec cpe wget -O /dev/null http://172.25.1.2/openwrt-x86-64-generic-squashfs-combined-efi-prepared.img
# Should download successfully (check exit code: echo $?)
```

## Part 3: Manual Upgrade Testing

### Step 10: Record Current Firmware Version

Before upgrading, record the current firmware version:

```bash
# Get current firmware version
docker exec cpe cat /etc/openwrt_release | grep DISTRIB_RELEASE || \
docker exec cpe cat /etc/os-release | grep VERSION || \
docker exec cpe opkg list-installed | grep -i "prplos\|openwrt" | head -5

# Record current rootfs checksum (optional, for verification)
docker exec cpe find / -maxdepth 1 -type f -name "*.img" 2>/dev/null || echo "No image files"
```

### Step 11: Check Current Rootfs State

Verify the container is in a clean state:

```bash
# Check for pending upgrades
docker exec cpe ls -la /boot/.do_upgrade 2>/dev/null && echo "Upgrade pending!" || echo "No upgrade pending"

# Check for new rootfs
docker exec cpe ls -la /new_rootfs_pending 2>/dev/null && echo "New rootfs exists!" || echo "No new rootfs"

# Check for old rootfs backup
docker exec cpe ls -la /old_root 2>/dev/null && echo "Old rootfs backup exists!" || echo "No backup"
```

### Step 12: Trigger Upgrade via sysupgrade

Test the upgrade process manually using sysupgrade:

```bash
# Option A: Use HTTP URL (recommended - tests full flow)
docker exec cpe sysupgrade -v http://172.25.1.2/openwrt-x86-64-generic-squashfs-combined-efi-prepared.img

# Option B: Copy image to container and use local file
docker cp openwrt-x86-64-generic-squashfs-combined-efi-prepared.img cpe:/tmp/upgrade.img
docker exec cpe sysupgrade -v /tmp/upgrade.img
```

**Expected Behavior**:
1. Image validation runs
2. Configuration backup is created (`/tmp/sysupgrade.tgz`)
3. Upgrade process starts
4. Hook intercepts and extracts rootfs to `/new_rootfs_pending`
5. `/boot/.do_upgrade` flag is created
6. Container reboots

**Note**: The container will reboot after this command completes.

### Step 13: Monitor Upgrade Process

While the upgrade is running, monitor the process:

```bash
# In a separate terminal, watch container logs
docker logs -f cpe

# Or check upgrade progress
docker exec cpe ls -la /new_rootfs_pending 2>/dev/null | head -10
docker exec cpe ls -la /boot/.do_upgrade 2>/dev/null
```

### Step 14: Wait for Reboot

After sysupgrade completes, the container will reboot:

```bash
# Wait for container to restart (may take 30-60 seconds)
# Check container status
docker ps | grep cpe

# If container is restarting, wait for it to come back up
while ! docker exec cpe echo "Container ready" 2>/dev/null; do
    echo "Waiting for container to restart..."
    sleep 2
done
```

### Step 15: Verify Upgrade Applied

After reboot, verify the upgrade was applied:

```bash
# Check if upgrade flag was processed
docker exec cpe ls -la /boot/.do_upgrade 2>/dev/null && echo "Upgrade flag still present!" || echo "Upgrade flag removed (upgrade applied)"

# Check if new rootfs was applied
docker exec cpe ls -la /new_rootfs_pending 2>/dev/null && echo "New rootfs still present" || echo "New rootfs applied and removed"

# Check firmware version (should match new version)
docker exec cpe cat /etc/openwrt_release | grep DISTRIB_RELEASE || \
docker exec cpe cat /etc/os-release | grep VERSION

# Verify system is operational
docker exec cpe ps aux | head -10
docker exec cpe ls -la /bin /sbin | head -10
```

### Step 16: Verify Configuration Preservation

Check that configuration was preserved:

```bash
# Check if config backup exists
docker exec cpe ls -la /tmp/sysupgrade.tgz 2>/dev/null || echo "Config backup not found"

# Check if config was restored (if PrplOS does this automatically)
docker exec cpe ls -la /etc/config/ 2>/dev/null | head -10

# Check network configuration (if configured before upgrade)
docker exec cpe cat /etc/config/network 2>/dev/null | head -20
```

## Part 4: Troubleshooting

### Issue: Validation Fails

**Symptoms**: `validate_firmware_image` returns `"valid": false`

**Solutions**:
```bash
# Check metadata
docker exec cpe fwtool -i /tmp/check.json /tmp/test_firmware.img
docker exec cpe cat /tmp/check.json

# Verify board name matches
docker exec cpe cat /tmp/sysinfo/board_name

# Use --force flag if signature check fails (test images only)
docker exec cpe sysupgrade --force -v /tmp/test_firmware.img
```

### Issue: Upgrade Doesn't Trigger

**Symptoms**: sysupgrade runs but no `/boot/.do_upgrade` flag is created

**Check**:
```bash
# Verify hook is present
docker exec cpe ls -la /lib/upgrade/z-container-hooks.sh

# Check hook is executable
docker exec cpe test -x /lib/upgrade/z-container-hooks.sh && echo "Executable" || echo "Not executable"

# Test hook manually (if possible)
docker exec cpe cat /lib/upgrade/z-container-hooks.sh | grep platform_do_upgrade
```

### Issue: Container Doesn't Reboot

**Symptoms**: sysupgrade completes but container doesn't reboot

**Check**:
```bash
# Check if reboot was attempted
docker logs cpe | tail -20

# Manually check upgrade state
docker exec cpe ls -la /boot/.do_upgrade /new_rootfs_pending

# If upgrade is pending, manually reboot
docker restart cpe
```

### Issue: Upgrade Applied But System Broken

**Symptoms**: Container boots but services don't work

**Check**:
```bash
# Check if old rootfs backup exists
docker exec cpe ls -la /old_root 2>/dev/null | head -10

# Check container logs
docker logs cpe | tail -50

# Check system services
docker exec cpe ps aux
docker exec cpe ls -la /etc/init.d/ | head -10
```

## Part 5: Clean Up

### Step 17: Clean Up Test Artifacts

After testing, clean up:

```bash
# Remove test image from container
docker exec cpe rm -f /tmp/test_firmware.img /tmp/upgrade.img

# Remove metadata files
docker exec cpe rm -f /tmp/metadata*.json

# Remove prepared image from host (optional)
# rm openwrt-x86-64-generic-squashfs-combined-efi-prepared.img

# Keep metadata.json for future use (optional)
```

## Quick Reference: Complete Workflow

```bash
# 1. Prepare image
cd /home/rjvisser/projects/req-tst/boardfarm-bdd/tests/test_artifacts
docker cp openwrt-x86-64-generic-squashfs-combined-efi.img cpe:/tmp/test_firmware.img

# 2. Create and add metadata
cat > metadata.json << 'EOF'
{
    "version": "3.0.3",
    "compat_version": "1.0",
    "supported_devices": {"asus-all-series": "asus-all-series"},
    "new_supported_devices": {"asus-all-series": "asus-all-series"}
}
EOF
docker cp metadata.json cpe:/tmp/metadata.json
docker exec cpe fwtool -I /tmp/metadata.json /tmp/test_firmware.img

# 3. Validate
docker exec cpe /usr/libexec/validate_firmware_image /tmp/test_firmware.img

# 4. Copy to HTTP server
docker cp cpe:/tmp/test_firmware.img wan:/tftpboot/openwrt-upgrade.img

# 5. Trigger upgrade
docker exec cpe sysupgrade -v http://172.25.1.2/openwrt-upgrade.img

# 6. Wait for reboot and verify
sleep 60
docker exec cpe cat /etc/os-release | grep VERSION
```

## Expected Timeline

- **Image Preparation**: 2-5 minutes
- **Image Validation**: < 1 minute
- **Upgrade Process**: 1-3 minutes (sysupgrade execution)
- **Container Reboot**: 30-60 seconds
- **Total Time**: ~5-10 minutes

## Success Criteria

✅ Image passes validation (`"valid": true` or `"forceable": true`)  
✅ sysupgrade completes without errors  
✅ Container reboots successfully  
✅ `/boot/.do_upgrade` flag is removed after boot  
✅ New firmware version is reported  
✅ System is operational after upgrade  
✅ Configuration is preserved (if applicable)

## Next Steps

After successful manual testing:
1. Integrate into automated BDD tests
2. Test TR-069 Download command flow
3. Test validation failure scenarios (UC-12345 Extension 6.a)
4. Test rollback scenarios (if PrplOS supports it)

