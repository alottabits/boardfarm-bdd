# Manual Firmware Image Preparation and Upgrade Testing Guide

## Overview

This guide provides step-by-step instructions for testing the PrplOS upgrade process in the containerized testbed. It covers three main areas:

1. **Image Preparation**: Prepare a firmware image with metadata and validation using the CPE container
2. **Local File Upgrade**: Test the upgrade process with a validated image from a local directory in the container
3. **Full Flow with HTTP Download**: Verify the entire upgrade flow including download from the HTTP file server

## Prerequisites

- CPE container is running (`docker ps | grep cpe`)
- WAN container is running (for HTTP server in Section 3)
- Source firmware image file available (e.g., `openwrt-x86-64-generic-squashfs-combined-efi.img` in `tests/test_artifacts`)
- Metadata file available (`tests/test_artifacts/metadata.json`)
- Access to the CPE container shell: `docker exec -it cpe ash`

## Resetting to Original State

After testing upgrades, the CPE container's filesystem will be modified (upgraded to a new PrplOS version). To reset back to the original PrplOS 3.0.2 state for fresh testing:

### Why Recreating the Container is Necessary

Simply rebuilding the image **will not** reset the container because:

- The container's filesystem persists independently of the image
- Rebuilding the image creates a new image, but the running container keeps its modified filesystem
- The upgrade modifies the container's rootfs, which survives image rebuilds
- The container must be recreated to get a fresh filesystem from the image

### Steps to Reset to Original State

**From the `boardfarm-bdd/raikou` directory**:

```bash
# Recreate the CPE container from the existing image
# This stops the current CPE container, removes it, and creates a new one
docker compose up -d --force-recreate cpe
```

**Note**: This command recreates only the CPE container without affecting other testbed services. The container will be recreated from the existing image, giving you a fresh PrplOS 3.0.2 filesystem. If you need to rebuild the image itself (e.g., after changing the Dockerfile), run `docker compose build cpe` first, then recreate the container.

### Verify Reset

After recreating, verify the CPE is back to original version:

```bash
# Check CPE version
docker exec cpe cat /etc/os-release | grep VERSION

# Expected output:
# VERSION="3.0.2"
# VERSION_ID="3.0.2"

# Verify no upgrade artifacts remain
docker exec cpe ls -la /boot/.do_upgrade 2>/dev/null && echo "Upgrade flag present!" || echo "Clean state"
docker exec cpe ls -lh /firmware/pending/ 2>/dev/null || echo "No pending firmware"
```

## Section 1: Prepare Upgrade Image

This section describes how to prepare a firmware image for upgrade testing using the CPE container. The prepared image will be stored in the `tests/test_artifacts` directory and can be reused for both local file upgrade testing (Section 2) and HTTP download testing (Section 3).

### Step 1: Enter Container and Prepare Environment

**On host**:
```bash
# Ensure CPE container is running
docker ps | grep cpe

# Enter the CPE container
docker exec -it cpe ash
```

**Inside container**:
```bash
# Create firmware directory
mkdir -p /firmware
```

### Step 2: Copy Source Image to Container

**In a separate terminal (on host)**:
```bash
# Navigate to test_artifacts directory (or wherever your source image is)
cd /home/rjvisser/projects/req-tst/boardfarm-bdd/tests/test_artifacts

# Copy source image to container
docker cp openwrt-x86-64-generic-squashfs-combined-efi.img cpe:/firmware/prepare_image.img
```

**Back in container**:
```bash
# Verify image was copied
ls -lh /firmware/prepare_image.img
```

### Step 3: Prepare Metadata

**Inside container**:
```bash
# Copy metadata from test_artifacts (or create it)
# First, let's copy it from the host if it exists
# Exit container temporarily
exit
```

**On host**:
```bash
# Copy metadata.json to container
docker cp tests/test_artifacts/metadata.json cpe:/tmp/metadata.json
```

**Back in container**:
```bash
docker exec -it cpe ash

# Verify metadata file
cat /tmp/metadata.json

# Add metadata to image
fwtool -I /tmp/metadata.json /firmware/prepare_image.img

# Verify metadata was added
fwtool -i /tmp/metadata_verify.json /firmware/prepare_image.img
cat /tmp/metadata_verify.json
```

### Step 4: Validate Image

**Inside container**:
```bash
# Validate the prepared image
/usr/libexec/validate_firmware_image /firmware/prepare_image.img
```

**Expected Output**:
```json
{
    "tests": {
        "fwtool_signature": true,
        "fwtool_device_match": true
    },
    "valid": false,
    "forceable": true,
    "allow_backup": true
}
```

**Note**: `valid: false` with `forceable: true` is common for test images due to partition layout differences. This is acceptable for testing purposes. Use `--force` flag when upgrading.

### Step 5: Copy Prepared Image to test_artifacts

**Exit container**:
```bash
exit
```

**On host**:
```bash
# Ensure we're in the project root
cd /home/rjvisser/projects/req-tst/boardfarm-bdd

# Copy prepared image to test_artifacts directory
docker cp cpe:/firmware/prepare_image.img tests/test_artifacts/prepared-openwrt-x86-64-squashfs-combined-efi.img

# Verify the prepared image exists
ls -lh tests/test_artifacts/prepared-openwrt-x86-64-squashfs-combined-efi.img
```

**Success**: The prepared image is now available in `tests/test_artifacts/prepared-openwrt-x86-64-squashfs-combined-efi.img` and can be used for upgrade testing in Sections 2 and 3.

**Note**: This preparation step only needs to be done once per firmware image version. The prepared image can be reused for multiple upgrade tests until you need to test a different firmware version.

## Section 2: Test Upgrade Process with Local Image

This section tests the upgrade process using a prepared image file stored locally in the container's `/firmware` directory.

**Prerequisites**: Complete Section 1 first to prepare the upgrade image. The prepared image should be available at `tests/test_artifacts/prepared-openwrt-x86-64-squashfs-combined-efi.img`.

### Step 1: Enter Container and Prepare Environment

```bash
# Enter the CPE container
docker exec -it cpe ash

# Inside container: Create firmware directory
mkdir -p /firmware
```

### Step 2: Copy Prepared Image to Container (from host)

**In a separate terminal (on host)**:
```bash
# Navigate to project root
cd /home/rjvisser/projects/req-tst/boardfarm-bdd

# Copy prepared image from test_artifacts to container
docker cp tests/test_artifacts/prepared-openwrt-x86-64-squashfs-combined-efi.img cpe:/firmware/test_firmware.img
```

**Back in container**:
```bash
# Verify image was copied
ls -lh /firmware/test_firmware.img
```

**Note**: The image is already prepared with metadata and validated (from Section 1), so we can proceed directly to the upgrade test.

### Step 3: Check Current Version

**Inside container**:
```bash
# Record current firmware version
cat /etc/os-release | grep VERSION

# Check for pending upgrades (should be clean)
ls -la /boot/.do_upgrade 2>/dev/null && echo "Upgrade pending!" || echo "No pending upgrades"
ls -lh /firmware/pending/ 2>/dev/null || echo "No firmware images in pending"
ls -lh /firmware/backups/ 2>/dev/null || echo "No rootfs backups"
```

### Step 4: Trigger Upgrade

**Inside container**:
```bash
# Trigger upgrade (use --force since prepared images typically return valid: false)
sysupgrade --force -v /firmware/test_firmware.img
```

**Expected Behavior**:
1. Image validation runs
2. Configuration backup is created (`/tmp/sysupgrade.tgz`)
3. Upgrade process starts
4. Hook stores full firmware image to `/firmware/pending/firmware_<timestamp>.img`
5. Hook preserves config backup: `/tmp/sysupgrade.tgz` → `/boot/sysupgrade.tgz`
6. `/boot/.do_upgrade` flag is created with firmware image path
7. Container reboots (connection will be lost)

**Note**: The container will reboot. You'll need to reconnect after it restarts.

### Step 5: Verify Upgrade Applied

**After container restarts, reconnect**:
```bash
# Enter container again
docker exec -it cpe ash

# Check upgrade flag was processed
ls -la /boot/.do_upgrade 2>/dev/null && echo "Upgrade flag still present!" || echo "Upgrade applied"

# Check firmware image was stored
ls -lh /firmware/pending/ 2>/dev/null || echo "No firmware images in pending"

# Check old rootfs backup was created (optional)
ls -lh /firmware/backups/ 2>/dev/null || echo "No rootfs backups"

# Check config backup was preserved
ls -lh /boot/sysupgrade.tgz 2>/dev/null && echo "Config backup preserved" || echo "Config backup restored (normal after upgrade)"

# Verify new firmware version
cat /etc/os-release | grep VERSION

# Verify configuration was restored (check network settings, etc.)
uci show network | head -5
uci show system | head -5

# Check system is operational
ps aux | head -5
```

**Success**: 
- Version should have changed (e.g., from `3.0.2` to `3.0.3`)
- Configuration should be restored (network settings, user accounts preserved)
- System should be operational

## Section 3: Verify Full Flow with HTTP Download

This section tests the complete upgrade flow including downloading the firmware image from the HTTP file server.

**Prerequisites**: Complete Section 1 first to prepare the upgrade image. The prepared image should be available at `tests/test_artifacts/prepared-openwrt-x86-64-squashfs-combined-efi.img`.

### Step 1: Copy Prepared Image to HTTP Server

**On host**:
```bash
# Navigate to project root
cd /home/rjvisser/projects/req-tst/boardfarm-bdd

# Copy prepared image from test_artifacts to WAN container (HTTP server)
docker cp tests/test_artifacts/prepared-openwrt-x86-64-squashfs-combined-efi.img wan:/tftpboot/openwrt-upgrade.img

# Verify image is accessible
docker exec wan ls -lh /tftpboot/openwrt-upgrade.img

# Get WAN container IP (usually 172.25.1.2)
docker exec wan hostname -I | awk '{print $1}'
```

**Note**: The image is already prepared with metadata and validated (from Section 1), so we can proceed directly to testing the HTTP download flow.

### Step 2: Verify HTTP Access

**Enter CPE container**:
```bash
docker exec -it cpe ash
```

**Inside container**:
```bash
# Test HTTP access to firmware image
wget -O /dev/null http://172.25.1.2/openwrt-upgrade.img && echo "HTTP access OK" || echo "HTTP access failed"

# Check current version
cat /etc/os-release | grep VERSION
```

### Step 3: Trigger Upgrade via HTTP URL

**Inside container**:
```bash
# Trigger upgrade using HTTP URL (tests full flow including download)
sysupgrade --force -v http://172.25.1.2/openwrt-upgrade.img
```

**Expected Behavior**:
1. sysupgrade downloads image from HTTP URL to `/tmp/sysupgrade.img`
2. Image validation runs
3. Configuration backup is created (`/tmp/sysupgrade.tgz`)
4. Upgrade process starts
5. Hook stores full firmware image to `/firmware/pending/firmware_<timestamp>.img`
6. Hook preserves config backup: `/tmp/sysupgrade.tgz` → `/boot/sysupgrade.tgz`
7. `/boot/.do_upgrade` flag is created with firmware image path
8. Container reboots

**Note**: The container will reboot. You'll need to reconnect after it restarts.

### Step 4: Verify Upgrade Applied

**After container restarts, reconnect**:
```bash
# Enter container
docker exec -it cpe ash

# Verify upgrade was applied
cat /etc/os-release | grep VERSION

# Check upgrade artifacts
ls -la /boot/.do_upgrade 2>/dev/null && echo "Upgrade flag still present!" || echo "Upgrade flag removed (upgrade applied)"

# Check firmware images
ls -lh /firmware/pending/ 2>/dev/null || echo "No firmware images in pending"

# Check old rootfs backups
ls -lh /firmware/backups/ 2>/dev/null || echo "No rootfs backups"

# Check config backup
ls -lh /boot/sysupgrade.tgz 2>/dev/null && echo "Config backup preserved" || echo "Config backup restored (normal after upgrade)"

# Verify configuration was restored (check network settings, etc.)
uci show network | head -5
uci show system | head -5

# Verify system is operational
ps aux | head -5
```

**Success**: 
- Version should have changed (e.g., from `3.0.2` to `3.0.3`)
- Configuration should be restored (network settings, user accounts preserved)
- System should be operational

## Troubleshooting

### Validation Returns `valid: false`

**Solution**: This is expected for test images. Use `--force` flag:
```bash
sysupgrade --force -v /firmware/test_firmware.img
```

### Upgrade Flag Not Created

**Check**:
```bash
# Verify hook is present
ls -la /lib/upgrade/z-container-hooks.sh

# Check hook logs
cat /boot/container_upgrade_debug.log

# Check if firmware image was stored
ls -lh /firmware/pending/

# Check if config backup was preserved
ls -lh /boot/sysupgrade.tgz
```

### Container Doesn't Reboot

**Check**:
```bash
# Check upgrade state
ls -la /boot/.do_upgrade
cat /boot/.do_upgrade 2>/dev/null && echo "Firmware image path:" && cat /boot/.do_upgrade

# Check if firmware image exists
ls -lh /firmware/pending/

# If upgrade is pending, manually reboot (from host)
# docker restart cpe
```

### Upgrade Applied But Version Unchanged

**Check**:
```bash
# Check entrypoint logs
cat /boot/entrypoint_debug.log

# Check if firmware image exists
ls -lh /firmware/pending/

# Check if rootfs extraction succeeded (entrypoint logs will show this)
grep -i "extract\|rootfs" /boot/entrypoint_debug.log

# Verify config backup was restored
ls -lh /sysupgrade.tgz /tmp/sysupgrade.tgz 2>/dev/null || echo "Config backup not found (may have been consumed by PrplOS)"
```

## Quick Reference

### Section 1: Prepare Upgrade Image
```bash
# On host
docker cp tests/test_artifacts/openwrt-x86-64-generic-squashfs-combined-efi.img cpe:/firmware/prepare_image.img
docker cp tests/test_artifacts/metadata.json cpe:/tmp/metadata.json

# Inside container
fwtool -I /tmp/metadata.json /firmware/prepare_image.img
/usr/libexec/validate_firmware_image /firmware/prepare_image.img

# On host (after exit)
docker cp cpe:/firmware/prepare_image.img tests/test_artifacts/prepared-openwrt-x86-64-squashfs-combined-efi.img
```

### Section 2: Local File Upgrade
```bash
# On host
docker cp tests/test_artifacts/prepared-openwrt-x86-64-squashfs-combined-efi.img cpe:/firmware/test_firmware.img

# Inside container
sysupgrade --force -v /firmware/test_firmware.img
# (Wait for reboot, then verify)
cat /etc/os-release | grep VERSION
```

### Section 3: Full Flow with HTTP Download
```bash
# On host
docker cp tests/test_artifacts/prepared-openwrt-x86-64-squashfs-combined-efi.img wan:/tftpboot/openwrt-upgrade.img

# Inside container
sysupgrade --force -v http://172.25.1.2/openwrt-upgrade.img
# (Wait for reboot, then verify)
cat /etc/os-release | grep VERSION
```

## Success Criteria

✅ Image passes validation (`"valid": true` or `"forceable": true`)  
✅ sysupgrade completes without errors  
✅ Firmware image stored to `/firmware/pending/firmware_<timestamp>.img`  
✅ Config backup preserved to `/boot/sysupgrade.tgz`  
✅ Container reboots successfully  
✅ `/boot/.do_upgrade` flag is removed after boot  
✅ Config backup restored to `/sysupgrade.tgz` (consumed by PrplOS during boot)  
✅ New firmware version is reported  
✅ Configuration restored (network settings, user accounts, etc.)  
✅ System is operational after upgrade  

## Expected Timeline

- **Image Preparation**: 1-2 minutes
- **Image Validation**: < 1 minute
- **Upgrade Process**: 1-3 minutes
- **Container Reboot**: 30-60 seconds
- **Total Time**: ~5-10 minutes per section
