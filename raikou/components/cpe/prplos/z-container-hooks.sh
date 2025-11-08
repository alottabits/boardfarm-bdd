#!/bin/sh
# Container hook that overrides platform_do_upgrade() and platform_check_image()
# This script is sourced by /lib/upgrade/do_stage2 after platform.sh
# The 'z-' prefix ensures it's loaded alphabetically after platform.sh

# Debug: Log that this script is being sourced
echo "Container upgrade: z-container-hooks.sh is being sourced" >&2
logger -t container-upgrade "z-container-hooks.sh is being sourced"

# Override rootfs_type() to return empty in containers
# This causes stage2 to skip the ramfs switch (which uses pivot_root and may fail in containers)
# For containerized upgrades, we don't need to unmount root filesystem since we're not writing to FLASH
rootfs_type() {
    # Return empty string so stage2 skips ramfs switch
    v "Container upgrade: rootfs_type() returning empty (skipping ramfs switch)"
    echo "Container upgrade: Skipping ramfs switch for containerized upgrade" >&2
    logger -t container-upgrade "Skipping ramfs switch for containerized upgrade"
    return 0
}

# Override platform_check_image() to skip boot device check in containers
# The native function tries to call export_bootdevice which fails in containers
platform_check_image() {
    local image="$1"
    
    v "Container upgrade: Overriding platform_check_image()"
    
    # In containerized environment, we skip boot device checks
    # We still validate the image structure using native functions
    # Check that image exists and is readable
    [ -f "$image" ] || {
        v "Container upgrade: Image file not found: $image"
        return 1
    }
    
    # Use native get_partitions to validate image structure
    # This validates partition table without needing boot device
    get_partitions "$image" image || {
        v "Container upgrade: Failed to parse partition table"
        rm -f /tmp/partmap.image
        return 1
    }
    
    # Check that partition 2 (rootfs) exists
    local found_rootfs=0
    while read part start size; do
        if [ "$part" = "2" ]; then
            found_rootfs=1
            break
        fi
    done < /tmp/partmap.image
    
    rm -f /tmp/partmap.image
    
    if [ "$found_rootfs" = "0" ]; then
        v "Container upgrade: Rootfs partition (partition 2) not found in image"
        return 1
    fi
    
    v "Container upgrade: Image structure validated successfully"
    return 0
}

platform_do_upgrade() {
    local diskdev partdev diff
    local image="$1"
    
    # Use persistent location for debug logs (survives reboot)
    local debug_log="/boot/container_upgrade_debug.log"
    mkdir -p /boot
    
    # Log to both syslog and stderr for debugging - use multiple methods to ensure visibility
    # Write to file FIRST before anything else to ensure we capture the call
    echo "=== platform_do_upgrade CALLED at $(date) ===" >> "$debug_log" 2>&1
    echo "Image path: $image" >> "$debug_log" 2>&1
    echo "Function arguments: $@" >> "$debug_log" 2>&1
    
    v "Container upgrade: Intercepting platform_do_upgrade()"
    echo "Container upgrade: Intercepting platform_do_upgrade()" >&2
    echo "Container upgrade: platform_do_upgrade() called with image: $image" >&2
    logger -t container-upgrade "Intercepting platform_do_upgrade() for image: $image"
    
    # Verify image path is correct (might be in /tmp after sysupgrade copies it)
    echo "Checking image file: $image" >> "$debug_log" 2>&1
    if [ ! -f "$image" ]; then
        echo "Image not found at: $image, searching alternatives..." >> "$debug_log" 2>&1
        # Try to find the image in common locations
        if [ -f "/tmp/sysupgrade.img" ]; then
            image="/tmp/sysupgrade.img"
            echo "Found image at: $image" >> "$debug_log" 2>&1
            v "Container upgrade: Using image from /tmp/sysupgrade.img"
        elif [ -f "/tmp/$(basename "$image")" ]; then
            image="/tmp/$(basename "$image")"
            echo "Found image at: $image" >> "$debug_log" 2>&1
            v "Container upgrade: Using image from /tmp/$(basename "$image")"
        else
            echo "ERROR: Image file not found anywhere: $image" >> "$debug_log" 2>&1
            v "Container upgrade: Image file not found: $image"
            echo "Container upgrade: ERROR - Image file not found: $image" >&2
            return 1
        fi
    else
        echo "Image file found: $image" >> "$debug_log" 2>&1
    fi
    
    v "Container upgrade: Processing image: $image"
    echo "Processing image: $image" >> "$debug_log" 2>&1
    
    # In containerized environment, we don't need to identify a physical boot device
    # We work directly with the image file to extract partition data
    # Use native PrplOS functions to extract partition data
    # These functions are already available from common.sh (sourced earlier)
    
    sync
    
    # Extract rootfs partition (partition 2) from image
    # Use native get_partitions and get_image_dd functions
    echo "Calling get_partitions for image: $image" >> "$debug_log" 2>&1
    get_partitions "$image" image || {
        echo "ERROR: get_partitions failed" >> "$debug_log" 2>&1
        v "Container upgrade: Failed to get partitions from image"
        return 1
    }
    echo "get_partitions completed, checking /tmp/partmap.image" >> "$debug_log" 2>&1
    
    # Find partition 2 (rootfs) in the image
    local rootfs_start rootfs_size
    rootfs_start=""
    rootfs_size=""
    
    while read part start size; do
        if [ "$part" = "2" ]; then
            rootfs_start=$start
            rootfs_size=$size
            break
        fi
    done < /tmp/partmap.image
    
    if [ -z "$rootfs_start" ] || [ -z "$rootfs_size" ]; then
        v "Container upgrade: Failed to find rootfs partition (partition 2) in image"
        rm -f /tmp/partmap.image
        return 1
    fi
    
    v "Container upgrade: Found rootfs partition at offset $rootfs_start, size $rootfs_size"
    
    # Extract rootfs partition to temporary location
    mkdir -p /new_rootfs_pending
    echo "Created /new_rootfs_pending directory" >> "$debug_log" 2>&1
    
    # Log image extraction attempt
    echo "Extracting rootfs partition from image: $image" >> "$debug_log" 2>&1
    echo "Partition offset: $rootfs_start, size: $rootfs_size" >> "$debug_log" 2>&1
    
    get_image_dd "$image" of=/tmp/rootfs.img ibs=512 skip="$rootfs_start" count="$rootfs_size" || {
        echo "ERROR: get_image_dd failed" >> "$debug_log" 2>&1
        v "Container upgrade: Failed to extract rootfs partition"
        rm -f /tmp/rootfs.img /tmp/partmap.image
        return 1
    }
    
    echo "Rootfs partition extracted successfully" >> "$debug_log" 2>&1
    
    # Extract SquashFS from the partition image
    # Use mount -o loop which automatically handles loop devices (no losetup needed)
    echo "Mounting SquashFS using mount -o loop..." >> "$debug_log" 2>&1
    echo "Checking if /tmp/rootfs.img exists..." >> "$debug_log" 2>&1
    ls -lh /tmp/rootfs.img >> "$debug_log" 2>&1 || {
        echo "ERROR: /tmp/rootfs.img does not exist" >> "$debug_log" 2>&1
        v "Container upgrade: Rootfs partition image not found"
        rm -f /tmp/partmap.image
        return 1
    }
    
    # Ensure /mnt mount point exists
    mkdir -p /mnt
    echo "Created /mnt directory if needed" >> "$debug_log" 2>&1
    
    # Mount SquashFS directly using mount -o loop (automatically creates loop device)
    mount -o loop -t squashfs /tmp/rootfs.img /mnt >> "$debug_log" 2>&1
    local mount_result=$?
    if [ $mount_result -ne 0 ]; then
        echo "ERROR: Failed to mount SquashFS with mount -o loop (exit code: $mount_result)" >> "$debug_log" 2>&1
        echo "Checking if /mnt exists..." >> "$debug_log" 2>&1
        ls -ld /mnt >> "$debug_log" 2>&1 || echo "/mnt does not exist" >> "$debug_log" 2>&1
        echo "Checking if /tmp/rootfs.img exists..." >> "$debug_log" 2>&1
        ls -lh /tmp/rootfs.img >> "$debug_log" 2>&1 || echo "/tmp/rootfs.img does not exist" >> "$debug_log" 2>&1
        echo "Checking if /mnt is already mounted..." >> "$debug_log" 2>&1
        mount | grep /mnt >> "$debug_log" 2>&1 || echo "/mnt is not mounted" >> "$debug_log" 2>&1
        echo "Checking available loop devices..." >> "$debug_log" 2>&1
        ls -la /dev/loop* >> "$debug_log" 2>&1 || echo "No loop devices found" >> "$debug_log" 2>&1
        v "Container upgrade: Failed to mount SquashFS"
        rm -f /tmp/rootfs.img /tmp/partmap.image
        return 1
    fi
    echo "SquashFS mounted successfully using mount -o loop" >> "$debug_log" 2>&1
    
    # Copy new rootfs
    v "Container upgrade: Extracting rootfs to /new_rootfs_pending"
    echo "Copying files from /mnt to /new_rootfs_pending..." >> "$debug_log" 2>&1
    cp -a /mnt/* /new_rootfs_pending/ || {
        echo "ERROR: Failed to copy rootfs files" >> "$debug_log" 2>&1
        v "Container upgrade: Failed to copy rootfs files"
        umount /mnt
        rm -f /tmp/rootfs.img /tmp/partmap.image
        return 1
    }
    echo "Files copied successfully" >> "$debug_log" 2>&1
    
    umount /mnt
    echo "Unmounted SquashFS" >> "$debug_log" 2>&1
    rm -f /tmp/rootfs.img /tmp/partmap.image
    
    # Create flag for entrypoint to detect upgrade
    mkdir -p /boot
    touch /boot/.do_upgrade
    echo "Created /boot/.do_upgrade flag" >> "$debug_log" 2>&1
    
    v "Container upgrade: New rootfs extracted to /new_rootfs_pending"
    v "Container upgrade: Upgrade will be applied on next boot"
    echo "=== platform_do_upgrade completed successfully ===" >> "$debug_log" 2>&1
    
    # Return success
    return 0
}

# Debug: Verify function is defined after sourcing
# This will show if our override took effect
_platform_do_upgrade_check() {
    if type platform_do_upgrade >/dev/null 2>&1; then
        echo "Container upgrade: platform_do_upgrade function IS defined" >&2
        logger -t container-upgrade "platform_do_upgrade function IS defined"
        # Also verify it's our function, not the native one
        if type platform_do_upgrade 2>&1 | grep -q "Container upgrade"; then
            echo "Container upgrade: Confirmed - our platform_do_upgrade override is active" >&2
        fi
    else
        echo "Container upgrade: platform_do_upgrade function NOT found" >&2
        logger -t container-upgrade "platform_do_upgrade function NOT found"
    fi
}
_platform_do_upgrade_check

# Also add a wrapper to catch when do_stage2 tries to call the function
# This helps debug if the function isn't being found
_original_platform_do_upgrade=$(type platform_do_upgrade 2>&1 | head -1)
echo "Container upgrade: Function check result: $_original_platform_do_upgrade" >&2

# Override default_do_upgrade() as a fallback to ensure our logic runs
# This ensures that even if platform_do_upgrade() isn't found, we still intercept
default_do_upgrade() {
    local image="$1"
    local debug_log="/boot/container_upgrade_debug.log"
    mkdir -p /boot
    
    # Write to file FIRST to ensure we capture this call
    echo "=== default_do_upgrade CALLED at $(date) ===" >> "$debug_log" 2>&1
    echo "Image path: $image" >> "$debug_log" 2>&1
    v "Container upgrade: default_do_upgrade() called - redirecting to platform_do_upgrade()"
    echo "Container upgrade: WARNING - default_do_upgrade() called instead of platform_do_upgrade()" >&2
    logger -t container-upgrade "WARNING: default_do_upgrade() called, redirecting to platform_do_upgrade()"
    # Call our platform_do_upgrade function
    platform_do_upgrade "$image"
}

