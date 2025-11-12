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
    
    sync
    
    # Store full firmware image in persistent location (survives container restart)
    # Use timestamp to avoid conflicts if multiple upgrades are attempted
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local firmware_dir="/firmware/pending"
    local persistent_image="$firmware_dir/firmware_${timestamp}.img"
    
    mkdir -p "$firmware_dir"
    echo "Storing full firmware image to persistent location: $persistent_image" >> "$debug_log" 2>&1
    
    # Copy the firmware image to persistent location
    cp "$image" "$persistent_image" || {
        echo "ERROR: Failed to copy firmware image to $persistent_image" >> "$debug_log" 2>&1
        v "Container upgrade: Failed to copy firmware image"
        return 1
    }
    
    echo "Firmware image stored successfully: $persistent_image" >> "$debug_log" 2>&1
    v "Container upgrade: Firmware image stored to $persistent_image"
    
    # Preserve PrplOS config backup (survives container restart)
    # PrplOS creates /tmp/sysupgrade.tgz during sysupgrade, but /tmp is cleared on restart
    # Copy it to persistent location so entrypoint can restore it before PrplOS boot
    if [ -f "/tmp/sysupgrade.tgz" ]; then
        local config_backup="/boot/sysupgrade.tgz"
        echo "Preserving PrplOS config backup: /tmp/sysupgrade.tgz -> $config_backup" >> "$debug_log" 2>&1
        cp "/tmp/sysupgrade.tgz" "$config_backup" || {
            echo "WARNING: Failed to preserve config backup" >> "$debug_log" 2>&1
            v "Container upgrade: WARNING - Config backup preservation failed"
        }
        echo "Config backup preserved successfully" >> "$debug_log" 2>&1
    else
        echo "No config backup found at /tmp/sysupgrade.tgz (may be normal if no custom config)" >> "$debug_log" 2>&1
    fi
    
    # Store image path in upgrade flag file for entrypoint to read
    mkdir -p /boot
    echo "$persistent_image" > /boot/.do_upgrade
    echo "Created /boot/.do_upgrade flag with image path: $persistent_image" >> "$debug_log" 2>&1
    
    v "Container upgrade: Upgrade will be applied on next boot from $persistent_image"
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

