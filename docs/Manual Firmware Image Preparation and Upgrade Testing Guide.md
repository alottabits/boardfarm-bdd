# Manual Firmware Image Preparation and Upgrade Testing Guide

## Overview

This guide provides step-by-step instructions for testing the PrplOS upgrade process in the containerized testbed. It covers two scenarios:

1. **Local File Upgrade**: Test the upgrade process with a validated image from a local directory in the container
2. **Full Flow with HTTP Download**: Verify the entire upgrade flow including download from the HTTP file server

## Prerequisites

- CPE container is running (`docker ps | grep cpe`)
- WAN container is running (for HTTP server in Section 2)
- Firmware image file available (e.g., `openwrt-x86-64-generic-squashfs-combined-efi.img`)
- Access to the CPE container shell: `docker exec -it cpe ash`

## Section 1: Test Upgrade Process with Local Image

This section tests the upgrade process using an image file stored locally in the container's `/firmware` directory.

### Step 1: Enter Container and Prepare Environment

```bash
# Enter the CPE container
docker exec -it cpe ash

# Inside container: Create firmware directory
mkdir -p /firmware
```

### Step 2: Copy Image to Container (from host)

**In a separate terminal (on host)**:
```bash
# Copy image to container
docker cp openwrt-x86-64-generic-squashfs-combined-efi.img cpe:/firmware/test_firmware.img
```

**Back in container**:
```bash
# Verify image was copied
ls -lh /firmware/test_firmware.img
```

### Step 3: Prepare Metadata

**Inside container**:
```bash
# Create metadata file
cat > /tmp/metadata.json << 'EOF'
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

# Add metadata to image
fwtool -I /tmp/metadata.json /firmware/test_firmware.img

# Verify metadata was added
fwtool -i /tmp/metadata_verify.json /firmware/test_firmware.img
cat /tmp/metadata_verify.json
```

### Step 4: Validate Image

**Inside container**:
```bash
# Validate the image
/usr/libexec/validate_firmware_image /firmware/test_firmware.img
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

**Note**: `valid: false` with `forceable: true` is common for test images due to partition layout differences. Use `--force` flag when upgrading.

### Step 5: Check Current Version

**Inside container**:
```bash
# Record current firmware version
cat /etc/os-release | grep VERSION

# Check for pending upgrades (should be clean)
ls -la /boot/.do_upgrade /new_rootfs_pending /old_root 2>/dev/null || echo "No pending upgrades"
```

### Step 6: Trigger Upgrade

**Inside container**:
```bash
# Trigger upgrade (use --force if validation returned valid: false)
sysupgrade --force -v /firmware/test_firmware.img
```

**Expected Behavior**:
1. Image validation runs
2. Configuration backup is created (`/tmp/sysupgrade.tgz`)
3. Upgrade process starts
4. Hook extracts rootfs to `/new_rootfs_pending`
5. `/boot/.do_upgrade` flag is created
6. Container reboots (connection will be lost)

**Note**: The container will reboot. You'll need to reconnect after it restarts.

### Step 7: Verify Upgrade Applied

**After container restarts, reconnect**:
```bash
# Enter container again
docker exec -it cpe ash

# Check upgrade flag was processed
ls -la /boot/.do_upgrade 2>/dev/null && echo "Upgrade flag still present!" || echo "Upgrade applied"

# Check new rootfs was applied
ls -la /new_rootfs_pending 2>/dev/null && echo "New rootfs still present" || echo "New rootfs applied"

# Verify new firmware version
cat /etc/os-release | grep VERSION

# Check system is operational
ps aux | head -5
```

**Success**: Version should have changed (e.g., from `3.0.2` to `3.0.3`).

## Section 2: Verify Full Flow with HTTP Download

This section tests the complete upgrade flow including downloading the firmware image from the HTTP file server.

### Step 1: Prepare Image on Host

**On host**:
```bash
# Copy image to WAN container (HTTP server)
docker cp openwrt-x86-64-generic-squashfs-combined-efi.img wan:/tftpboot/openwrt-upgrade.img

# Verify image is accessible
docker exec wan ls -lh /tftpboot/openwrt-upgrade.img

# Get WAN container IP (usually 172.25.1.2)
docker exec wan hostname -I | awk '{print $1}'
```

### Step 2: Enter Container and Prepare Metadata

**Enter CPE container**:
```bash
docker exec -it cpe ash
```

**Inside container**:
```bash
# Download image from HTTP server to prepare it
wget -O /firmware/test_firmware.img http://172.25.1.2/openwrt-upgrade.img

# Create metadata
cat > /tmp/metadata.json << 'EOF'
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

# Add metadata to downloaded image
fwtool -I /tmp/metadata.json /firmware/test_firmware.img

# Copy prepared image back to HTTP server (from host)
# Exit container first
exit
```

**On host**:
```bash
# Copy prepared image back to HTTP server
docker cp cpe:/firmware/test_firmware.img wan:/tftpboot/openwrt-upgrade.img
```

### Step 3: Verify HTTP Access

**Enter container again**:
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

### Step 4: Trigger Upgrade via HTTP URL

**Inside container**:
```bash
# Trigger upgrade using HTTP URL (tests full flow including download)
sysupgrade --force -v http://172.25.1.2/openwrt-upgrade.img
```

**Expected Behavior**:
1. sysupgrade downloads image from HTTP URL to `/tmp/sysupgrade.img`
2. Image validation runs
3. Configuration backup is created
4. Upgrade process starts
5. Hook extracts rootfs to `/new_rootfs_pending`
6. `/boot/.do_upgrade` flag is created
7. Container reboots

### Step 5: Verify Upgrade Applied

**After container restarts**:
```bash
# Enter container
docker exec -it cpe ash

# Verify upgrade was applied
cat /etc/os-release | grep VERSION

# Check upgrade artifacts
ls -la /boot/.do_upgrade /new_rootfs_pending /old_root 2>/dev/null || echo "Upgrade completed"

# Verify system is operational
ps aux | head -5
```

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
```

### Container Doesn't Reboot

**Check**:
```bash
# Check upgrade state
ls -la /boot/.do_upgrade /new_rootfs_pending

# If upgrade is pending, manually reboot (from host)
# docker restart cpe
```

### Upgrade Applied But Version Unchanged

**Check**:
```bash
# Check entrypoint logs
cat /boot/entrypoint_debug.log

# Verify new rootfs was extracted
ls -la /new_rootfs_pending
```

## Quick Reference

### Section 1: Local File Upgrade
```bash
# Inside container
mkdir -p /firmware
# (Copy image from host: docker cp image.img cpe:/firmware/test_firmware.img)
cat > /tmp/metadata.json << 'EOF'
{"version": "3.0.3", "compat_version": "1.0", "supported_devices": {"asus-all-series": "asus-all-series"}, "new_supported_devices": {"asus-all-series": "asus-all-series"}}
EOF
fwtool -I /tmp/metadata.json /firmware/test_firmware.img
/usr/libexec/validate_firmware_image /firmware/test_firmware.img
sysupgrade --force -v /firmware/test_firmware.img
# (Wait for reboot, then verify)
cat /etc/os-release | grep VERSION
```

### Section 2: Full Flow with HTTP Download
```bash
# On host
docker cp image.img wan:/tftpboot/openwrt-upgrade.img

# Inside container
wget -O /firmware/test_firmware.img http://172.25.1.2/openwrt-upgrade.img
# (Add metadata, copy back to HTTP server)
sysupgrade --force -v http://172.25.1.2/openwrt-upgrade.img
# (Wait for reboot, then verify)
cat /etc/os-release | grep VERSION
```

## Success Criteria

✅ Image passes validation (`"valid": true` or `"forceable": true`)  
✅ sysupgrade completes without errors  
✅ Container reboots successfully  
✅ `/boot/.do_upgrade` flag is removed after boot  
✅ New firmware version is reported  
✅ System is operational after upgrade  

## Expected Timeline

- **Image Preparation**: 1-2 minutes
- **Image Validation**: < 1 minute
- **Upgrade Process**: 1-3 minutes
- **Container Reboot**: 30-60 seconds
- **Total Time**: ~5-10 minutes per section
