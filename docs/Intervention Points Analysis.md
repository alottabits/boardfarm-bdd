# PrplOS Containerized Upgrade: Intervention Points Analysis

## Executive Summary

After analyzing the PrplOS upgrade process in the container, we have identified **two minimal intervention points** that bridge the containerization gap (no FLASH memory) while preserving all native PrplOS behavior:

1. **Platform Hook** (`/lib/upgrade/z-container-hooks.sh`): Intercepts FLASH write operations
2. **Entrypoint Script** (`/docker-entrypoint.sh`): Applies new filesystem at boot time

**Note**: A wrapper script for URL handling is **NOT needed** - native PrplOS sysupgrade handles HTTP/HTTPS URLs directly.

## PrplOS Upgrade Process Flow

### Native Flow (Production CPE)

```
TR-069 Download Command
  ↓
cwmpd downloads firmware to /tmp/image_name
  ↓
/usr/bin/tr069_1_fw_upgrade /tmp/image_name
  ↓
sysupgrade -v /tmp/image_name
  ↓
  ├─ Validates image (/usr/libexec/validate_firmware_image)
  ├─ Creates config backup (/tmp/sysupgrade.tgz)
  └─ Calls: ubus call system sysupgrade
      ↓
/lib/upgrade/stage2
  ├─ Switches to ramfs
  └─ Calls: /lib/upgrade/do_stage2
      ↓
platform_do_upgrade() [from /lib/upgrade/platform.sh]
  ├─ Writes to /dev/sda2 (FLASH partition)
  └─ Reboots
```

### Containerized Flow (Testbed)

```
TR-069 Download Command
  ↓
cwmpd downloads firmware to /tmp/image_name
  ↓
/usr/bin/tr069_1_fw_upgrade /tmp/image_name
  ↓
/sbin/sysupgrade [NATIVE] -v /tmp/image_name
  ├─ If URL: downloads to /tmp/sysupgrade.img (native handling)
  ├─ Validates image (native PrplOS)
  ├─ Creates config backup (native PrplOS)
  └─ Calls: ubus call system sysupgrade
      ↓
/lib/upgrade/stage2 (native PrplOS)
  ├─ Switches to ramfs ⚠️ (may fail in containers - needs verification)
  └─ Calls: /lib/upgrade/do_stage2
      ↓
platform_do_upgrade() [HOOK: /lib/upgrade/z-container-hooks.sh]
  ├─ Extracts rootfs to /new_rootfs_pending
  ├─ Creates /boot/.do_upgrade flag
  └─ Reboots
      ↓
/docker-entrypoint.sh [ENTRYPOINT]
  ├─ Detects /boot/.do_upgrade flag
  ├─ Backs up current rootfs to /old_root
  ├─ Applies new rootfs from /new_rootfs_pending
  └─ Continues normal boot
```

**⚠️ Open Question**: Does the ramfs switch in `/lib/upgrade/stage2` work in containers? This may require:
- Privileged container (CAP_SYS_ADMIN)
- Or an additional intervention point to handle ramfs operations
- Or verification that ramfs switch is not needed for containerized upgrades

## Intervention Point 1: Wrapper Script (`/sbin/sysupgrade`)

### Purpose
**NOT NEEDED** - Native PrplOS sysupgrade handles HTTP/HTTPS URLs directly.

### Verified Behavior
- ✅ Native PrplOS sysupgrade handles `http://` and `https://` URLs natively
- ✅ Uses `wget` internally to download URLs to `/tmp/sysupgrade.img`
- ✅ The WAN container in the testbed provides HTTP service via lighttpd (port 80)
- ✅ Files are served from `/tftpboot` directory (symlinked to `/var/www/html`)

**Test Results:**
```
# Verified on PrplOS CPE:
$ grep -i "http\|wget\|curl" /sbin/sysupgrade
	http://*|\
	https://*)
		wget -O/tmp/sysupgrade.img "$IMAGE" || exit 1

$ sysupgrade -n http://172.25.1.2/test.img
Downloading 'http://172.25.1.2/test.img'
Connecting to 172.25.1.2:80
```

### Implementation Approach

**Conclusion**: No wrapper script is needed for HTTP/HTTPS URL handling. Native sysupgrade handles URLs directly.

**However**, if you need to intercept or modify sysupgrade behavior for other reasons (e.g., container-specific logic), you can still wrap it:

**Location**: `/sbin/sysupgrade` (replaces original, which moves to `/sbin/sysupgrade.orig`)

**Logic** (only if you need to intercept for other reasons):
```bash
#!/bin/sh
# Wrapper that can add container-specific logic, then execs sysupgrade.orig

# For now, just pass through - native sysupgrade handles URLs
exec /sbin/sysupgrade.orig "$@"
```

**Key Points**:
- Native sysupgrade already handles HTTP/HTTPS URLs
- No need to download URLs manually before calling sysupgrade
- Wrapper only needed if you need to intercept for other container-specific logic
- TFTP handling is not needed since we standardize on HTTP(S) in the testbed

## Intervention Point 2: Platform Hook (`/lib/upgrade/z-container-hooks.sh`)

### Purpose
Intercept `platform_do_upgrade()` call to redirect FLASH writes to container filesystem.

### Current Behavior
- `/lib/upgrade/platform.sh` defines `platform_do_upgrade()` that writes directly to `/dev/sda2`
- Uses `get_image_dd()` to write raw partition data to block device
- This fails in containers (no real FLASH device)
- **Note**: The ramfs switch in `/lib/upgrade/stage2` (which happens before this hook) may also need verification in containers (see "Open Questions" section below)

### Implementation Approach

**Location**: `/lib/upgrade/z-container-hooks.sh` (alphabetically after `platform.sh`)

**Why `z-` prefix?**:
- `include /lib/upgrade` sources all `.sh` files alphabetically
- Our hook must be sourced AFTER `platform.sh` to override `platform_do_upgrade()`
- Files: `common.sh`, `fwtool.sh`, `platform.sh`, `z-container-hooks.sh`

**Logic**:
```bash
#!/bin/sh
# Container hook that overrides platform_do_upgrade()

platform_do_upgrade() {
    local diskdev partdev diff
    local image="$1"
    
    # Use native PrplOS functions to extract partition data
    . /lib/upgrade/common.sh  # Ensure functions are available
    
    export_bootdevice && export_partdevice diskdev 0 || {
        v "Unable to determine upgrade device"
        return 1
    }
    
    sync
    
    # Extract rootfs partition (partition 2) from image
    # Use native get_partitions and get_image_dd functions
    get_partitions "$image" image
    
    # Find partition 2 (rootfs) in the image
    local rootfs_start rootfs_size
    while read part start size; do
        if [ "$part" = "2" ]; then
            rootfs_start=$start
            rootfs_size=$size
            break
        fi
    done < /tmp/partmap.image
    
    # Extract rootfs partition to temporary location
    mkdir -p /new_rootfs_pending
    get_image_dd "$image" of=/tmp/rootfs.img ibs=512 skip="$rootfs_start" count="$rootfs_size"
    
    # Extract SquashFS from the partition image
    # Mount as loop device and copy files
    local loopdev=$(losetup -f)
    losetup $loopdev /tmp/rootfs.img
    mount -t squashfs $loopdev /mnt
    
    # Copy new rootfs
    cp -a /mnt/* /new_rootfs_pending/
    
    umount /mnt
    losetup -d $loopdev
    rm -f /tmp/rootfs.img /tmp/partmap.image
    
    # Create flag for entrypoint to detect upgrade
    mkdir -p /boot
    touch /boot/.do_upgrade
    
    v "Container upgrade: New rootfs extracted to /new_rootfs_pending"
    v "Upgrade will be applied on next boot"
}
```

**Key Points**:
- Uses native PrplOS functions (`get_partitions`, `get_image_dd`) - no reimplementation
- Extracts same data that would be written to FLASH
- Creates `/boot/.do_upgrade` flag for entrypoint
- Preserves all validation logic (happens before this hook is called)

## Intervention Point 3: Entrypoint Script (`/docker-entrypoint.sh`)

### Purpose
Apply new filesystem at boot time, bridging the containerization gap where FLASH mounting would occur.

### Current Behavior
- Container boots normally with existing rootfs
- No mechanism to detect or apply pending upgrades

### Implementation Approach

**Location**: `/docker-entrypoint.sh` (container ENTRYPOINT)

**Logic**:
```bash
#!/bin/sh
set -e

UPGRADE_FLAG="/boot/.do_upgrade"
NEW_ROOTFS="/new_rootfs_pending"
OLD_ROOTFS="/old_root"

# Check if upgrade is pending
if [ -f "$UPGRADE_FLAG" ]; then
    echo "Container upgrade: Applying new rootfs..."
    
    # Backup current rootfs (for potential rollback validation)
    if [ -d "$NEW_ROOTFS" ]; then
        # Backup current rootfs
        mkdir -p "$OLD_ROOTFS"
        cp -a / "$OLD_ROOTFS"/ || true  # Best effort backup
        
        # Apply new rootfs
        # Note: We can't replace running rootfs, so we'll use overlay or bind mounts
        # For simplicity, we'll copy over during early boot
        echo "Applying new rootfs from $NEW_ROOTFS..."
        
        # Remove flag
        rm -f "$UPGRADE_FLAG"
        
        # Copy new filesystem over current (during early boot, minimal processes)
        # This is safe because we're in entrypoint before most services start
        rsync -a --delete "$NEW_ROOTFS"/ /
        
        echo "Container upgrade: New rootfs applied"
    else
        echo "Container upgrade: Flag present but $NEW_ROOTFS not found, skipping"
        rm -f "$UPGRADE_FLAG"
    fi
fi

# Continue with normal boot
exec /sbin/init "$@"
```

**Key Points**:
- Runs before normal init process
- Only intervenes if `/boot/.do_upgrade` flag exists
- Creates backup for potential rollback validation (if PrplOS implements it)
- Applies new rootfs, then continues normal boot
- Minimal intervention - just bridges the FLASH gap

## File Structure Summary

```
Container Filesystem:
├── /sbin/
│   └── sysupgrade          [NATIVE] - Handles HTTP/HTTPS URLs directly
├── /lib/upgrade/
│   ├── common.sh            [NATIVE] - get_partitions, get_image_dd functions
│   ├── platform.sh          [NATIVE] - platform_do_upgrade (overridden)
│   └── z-container-hooks.sh [HOOK] - Overrides platform_do_upgrade()
├── /docker-entrypoint.sh    [ENTRYPOINT] - Applies upgrade at boot
├── /boot/                   [CREATED] - Upgrade flags directory
│   └── .do_upgrade          [FLAG] - Created by hook, read by entrypoint
├── /new_rootfs_pending/     [CREATED] - New rootfs extracted by hook
└── /old_root/               [CREATED] - Backup rootfs (for rollback validation)
```

## Validation Points

### What We Preserve (No Intervention)
- ✅ TR-069 protocol handling (cwmpd, tr069_1_fw_upgrade)
- ✅ Firmware image validation (`/usr/libexec/validate_firmware_image`)
- ✅ Configuration backup creation (`/tmp/sysupgrade.tgz`)
- ✅ Configuration restoration (PrplOS `/lib/preinit/80_mount_root`)
- ✅ All PrplOS validation logic
- ✅ Error reporting to ACS (native TR-069)

### What We Intervene (Containerization Gap)
- 🔧 FLASH write redirection (hook)
- 🔧 Boot-time filesystem application (entrypoint)

**Note**: URL download handling is handled natively by sysupgrade - no wrapper needed.

## Open Questions & Verification Needed

### 1. ramfs Switch in Containers ⚠️

**Question**: Does the ramfs switch in `/lib/upgrade/stage2` work correctly in containers?

**Test Results**:
```bash
# Verified on PrplOS CPE container:
$ cat /lib/upgrade/stage2 | grep -i "ramfs\|pivot"
# Shows pivot_root usage in switch_to_ramfs() function

$ cat /proc/self/status | grep Cap
CapEff: 000001ffffffffff  # Includes CAP_SYS_ADMIN (needed for pivot_root)
```

**Findings**:
- ✅ Container has CAP_SYS_ADMIN capability (required for `pivot_root`)
- ✅ stage2 script uses `pivot_root` to switch to ramfs
- ✅ Script has error handling: "Failed to switch over to ramfs. Please reboot."
- ⚠️ **Status**: UNCERTAIN - Capabilities are present, but `pivot_root` may still fail due to namespace restrictions

**Why it matters**: 
- Native PrplOS switches to ramfs to unmount root filesystem before writing to FLASH
- Containers may not have privileges to remount root filesystem
- This could cause the upgrade process to fail or behave unexpectedly

**Potential outcomes**:
- ✅ **Works**: Container has necessary privileges, ramfs switch succeeds
- ⚠️ **Fails silently**: Process continues but ramfs switch doesn't happen (may be OK if root doesn't need unmounting for containerized upgrades)
- ❌ **Fails with error**: Upgrade process fails - may need intervention

**If ramfs switch fails**:
- The script will output: "Failed to switch over to ramfs. Please reboot."
- Upgrade may still proceed if ramfs switch is not critical for containerized upgrades (since we're not writing to FLASH directly)
- May need to ensure container runs with `privileged: true` or verify namespace configuration
- Or intercept ramfs operations in a hook if critical

**Action**: ⚠️ **VERIFICATION NEEDED** - Test actual upgrade process to verify ramfs switch behavior.

## Testing Strategy

1. **Test URL Handling**: ✅ Verified - Native sysupgrade handles HTTP/HTTPS URLs directly
2. **Test ramfs Switch**: ⚠️ **PARTIALLY VERIFIED** - Container has CAP_SYS_ADMIN, but actual pivot_root behavior needs upgrade test (See "Open Questions" section)
3. **Test Hook Interception**: Verify `platform_do_upgrade()` is called and extracts rootfs
4. **Test Boot Application**: Verify entrypoint applies new rootfs correctly
5. **Test Native Behavior**: Verify all PrplOS validation still works
6. **Test TR-069 Integration**: Verify end-to-end upgrade via TR-069 Download command with HTTP URL

## Next Steps

1. ✅ Analyze PrplOS upgrade process (COMPLETE)
2. ✅ Verify sysupgrade URL support (COMPLETE - URLs supported natively)
3. ⏳ Implement platform hook
4. ⏳ Implement entrypoint script
5. ⏳ Test intervention points
6. ⏳ Validate UC-12345 scenarios

