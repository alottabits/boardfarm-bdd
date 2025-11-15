#!/bin/sh
# Container init wrapper script that handles boot-time upgrade application
# This script bridges the containerization gap where FLASH mounting would occur
# Uses CMD instead of ENTRYPOINT to avoid Docker lifecycle timing issues with Raikou

UPGRADE_FLAG="/boot/.do_upgrade"

# Fast path: Check for upgrade flag immediately, before any setup
# If no upgrade flag exists, immediately exec init without any overhead
if [ ! -f "$UPGRADE_FLAG" ]; then
    # No upgrade pending - exec init immediately for normal boot
    exec /sbin/init "$@"
fi

# Upgrade path: Only execute below if upgrade flag exists
NEW_ROOTFS="/new_rootfs_pending"
OLD_ROOTFS_BACKUP_DIR="/firmware/backups"
ENTRYPOINT_LOG="/boot/entrypoint_debug.log"

# Ensure /boot directory exists for logs and upgrade flags
mkdir -p /boot

# Log entrypoint execution (only for upgrade path)
echo "=== Container init wrapper started at $(date) ===" >> "$ENTRYPOINT_LOG" 2>&1
echo "Upgrade flag found, applying upgrade..." >> "$ENTRYPOINT_LOG" 2>&1

# Upgrade is pending
if [ -f "$UPGRADE_FLAG" ]; then
    echo "Container upgrade: Applying new rootfs..." >> "$ENTRYPOINT_LOG" 2>&1
    echo "Container upgrade: Applying new rootfs..."
    
    # Read firmware image path from upgrade flag file
    firmware_image=$(cat "$UPGRADE_FLAG" 2>/dev/null | head -1)
    
    if [ -z "$firmware_image" ] || [ ! -f "$firmware_image" ]; then
        echo "ERROR: Firmware image not found or invalid path: $firmware_image" >> "$ENTRYPOINT_LOG" 2>&1
        echo "Container upgrade: ERROR - Firmware image not found: $firmware_image"
        rm -f "$UPGRADE_FLAG"
        exit 1
    fi
    
    echo "Found firmware image: $firmware_image" >> "$ENTRYPOINT_LOG" 2>&1
    
    # Extract rootfs from firmware image using unsquashfs
    # unsquashfs binary is included in the image (built during Docker build)
    # It will be removed after upgrade completes (see cleanup section below)
    echo "Extracting rootfs from firmware image using unsquashfs..." >> "$ENTRYPOINT_LOG" 2>&1
    
    # Check if unsquashfs is available (should be included in image)
    if ! command -v unsquashfs >/dev/null 2>&1; then
        echo "ERROR: unsquashfs not found - cannot extract rootfs" >> "$ENTRYPOINT_LOG" 2>&1
        echo "Container upgrade: ERROR - unsquashfs tool not available"
        echo "Container upgrade: ERROR - unsquashfs tool not available" >&2
        rm -f "$UPGRADE_FLAG"
        exit 1
    fi
    
    # Parse partition table to find rootfs partition (partition 2) offset
    # Try sfdisk first (same method as Dockerfile builder), fall back to PrplOS get_partitions
    offset=""
    
    if command -v sfdisk >/dev/null 2>&1; then
        echo "Using sfdisk to parse partition table..." >> "$ENTRYPOINT_LOG" 2>&1
        offset=$(sfdisk -d "$firmware_image" 2>> "$ENTRYPOINT_LOG" | grep "image.img2" | sed -E 's/.*start=\s+([0-9]+).*/\1/g' 2>> "$ENTRYPOINT_LOG")
    fi
    
    # Fallback: Try to use PrplOS get_partitions function if sfdisk not available
    if [ -z "$offset" ]; then
        echo "sfdisk not available, trying PrplOS get_partitions function..." >> "$ENTRYPOINT_LOG" 2>&1
        # Source common.sh to get get_partitions function (if available)
        if [ -f /lib/upgrade/common.sh ]; then
            . /lib/upgrade/common.sh 2>> "$ENTRYPOINT_LOG"
            if type get_partitions >/dev/null 2>&1; then
                echo "Using PrplOS get_partitions function..." >> "$ENTRYPOINT_LOG" 2>&1
                get_partitions "$firmware_image" image 2>> "$ENTRYPOINT_LOG"
                if [ -f /tmp/partmap.image ]; then
                    while read part start size; do
                        if [ "$part" = "2" ]; then
                            offset=$start
                            break
                        fi
                    done < /tmp/partmap.image
                    rm -f /tmp/partmap.image
                fi
            fi
        fi
    fi
    
    if [ -z "$offset" ]; then
        echo "ERROR: Failed to find rootfs partition offset in firmware image" >> "$ENTRYPOINT_LOG" 2>&1
        echo "Container upgrade: ERROR - Cannot find rootfs partition (tried sfdisk and get_partitions)"
        rm -f "$UPGRADE_FLAG"
        exit 1
    fi
    
    echo "Found rootfs partition at offset: $offset (sectors)" >> "$ENTRYPOINT_LOG" 2>&1
    
    # Create temporary directory for extraction
    mkdir -p "$NEW_ROOTFS"
    
    # Extract SquashFS directly from firmware image using offset
    # Same command as Dockerfile builder: unsquashfs -offset $(( 512 * offset )) -dest dest image.img
    echo "Extracting SquashFS with offset $(( 512 * offset ))..." >> "$ENTRYPOINT_LOG" 2>&1
    unsquashfs -no-progress -quiet -offset $(( 512 * offset )) -dest "$NEW_ROOTFS" "$firmware_image" >> "$ENTRYPOINT_LOG" 2>&1
    
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to extract rootfs from firmware image" >> "$ENTRYPOINT_LOG" 2>&1
        echo "Container upgrade: ERROR - Failed to extract rootfs"
        rm -rf "$NEW_ROOTFS"
        rm -f "$UPGRADE_FLAG"
        exit 1
    fi
    
    echo "Rootfs extracted successfully to $NEW_ROOTFS" >> "$ENTRYPOINT_LOG" 2>&1
    
    # Backup current rootfs before applying upgrade
    # Pack as SquashFS image in /firmware/backups/ for potential rollback
    echo "Creating backup of current rootfs..." >> "$ENTRYPOINT_LOG" 2>&1
    mkdir -p "$OLD_ROOTFS_BACKUP_DIR"
    timestamp=$(date +%Y%m%d_%H%M%S)
    backup_image="$OLD_ROOTFS_BACKUP_DIR/rootfs_backup_${timestamp}.img"
    
    # Try to create SquashFS backup of current rootfs
    if command -v mksquashfs >/dev/null 2>&1; then
        echo "Packing current rootfs as SquashFS image..." >> "$ENTRYPOINT_LOG" 2>&1
        # Create temporary directory for backup (exclude virtual filesystems and temporary data)
        backup_temp="/tmp/rootfs_backup_temp"
        mkdir -p "$backup_temp"
        
        # Copy essential directories to backup temp (exclude /proc, /sys, /dev, /tmp, /run, etc.)
        # This creates a clean backup of the actual filesystem content
        for dir in bin etc lib lib64 opt root sbin usr var www boot; do
            if [ -d "/$dir" ] && [ "$dir" != "proc" ] && [ "$dir" != "sys" ] && [ "$dir" != "dev" ] && [ "$dir" != "tmp" ] && [ "$dir" != "run" ]; then
                echo "  Copying /$dir..." >> "$ENTRYPOINT_LOG" 2>&1
                cp -a "/$dir" "$backup_temp"/ 2>> "$ENTRYPOINT_LOG" || {
                    echo "  Warning: Some files in /$dir may not have been copied" >> "$ENTRYPOINT_LOG" 2>&1
                }
            fi
        done
        
        # Create SquashFS image from backup temp directory
        # Use compression and exclude patterns similar to production SquashFS
        mksquashfs "$backup_temp" "$backup_image" \
            -no-progress \
            -comp xz \
            -noappend \
            -e "$backup_temp/tmp/*" \
            -e "$backup_temp/var/tmp/*" \
            -e "$backup_temp/var/log/*" \
            -e "$backup_temp/var/run/*" \
            >> "$ENTRYPOINT_LOG" 2>&1
        
        if [ $? -eq 0 ]; then
            echo "Successfully created rootfs backup: $backup_image" >> "$ENTRYPOINT_LOG" 2>&1
            # Record backup metadata
            {
                echo "Backup created: $(date)"
                echo "Backup image: $backup_image"
                echo "Source firmware image: $firmware_image"
                if [ -f /etc/os-release ]; then
                    echo "OS version: $(grep VERSION= /etc/os-release | cut -d'"' -f2 || echo 'unknown')"
                fi
                echo "Backup type: SquashFS image (can be extracted with unsquashfs)"
            } > "$backup_image.info" 2>> "$ENTRYPOINT_LOG" || true
        else
            echo "Warning: Failed to create SquashFS backup, recording source image path only" >> "$ENTRYPOINT_LOG" 2>&1
            {
                echo "Backup created: $(date)"
                echo "Backup image: (not created - mksquashfs failed)"
                echo "Source firmware image: $firmware_image"
                if [ -f /etc/os-release ]; then
                    echo "OS version: $(grep VERSION= /etc/os-release | cut -d'"' -f2 || echo 'unknown')"
                fi
                echo "Backup type: Reference to source firmware image only"
                echo "Note: Use source firmware image for rollback: $firmware_image"
            } > "$backup_image.info" 2>> "$ENTRYPOINT_LOG" || true
        fi
        
        # Clean up temporary backup directory
        rm -rf "$backup_temp"
    else
        echo "mksquashfs not available, recording source firmware image path only" >> "$ENTRYPOINT_LOG" 2>&1
        # Fallback: Just record the source firmware image path
        # The original firmware image can serve as a backup reference
        {
            echo "Backup created: $(date)"
            echo "Backup image: (not created - mksquashfs not available)"
            echo "Source firmware image: $firmware_image"
            if [ -f /etc/os-release ]; then
                echo "OS version: $(grep VERSION= /etc/os-release | cut -d'"' -f2 || echo 'unknown')"
            fi
            echo "Backup type: Reference to source firmware image only"
            echo "Note: To restore, use the original firmware image: $firmware_image"
        } > "$backup_image.info" 2>> "$ENTRYPOINT_LOG" || true
    fi
    
    # Restore PrplOS config backup before applying new rootfs
    # PrplOS expects /sysupgrade.tgz or /tmp/sysupgrade.tar during boot restoration
    # We preserved it in /boot/sysupgrade.tgz, now restore it to where PrplOS expects it
    if [ -f "/boot/sysupgrade.tgz" ]; then
        echo "Restoring PrplOS config backup for boot-time restoration..." >> "$ENTRYPOINT_LOG" 2>&1
        # PrplOS looks for /sysupgrade.tgz first, then /tmp/sysupgrade.tar
        # Place it in root so PrplOS preinit script can find it
        cp "/boot/sysupgrade.tgz" "/sysupgrade.tgz" 2>> "$ENTRYPOINT_LOG" || {
            echo "WARNING: Failed to restore config backup to /sysupgrade.tgz" >> "$ENTRYPOINT_LOG" 2>&1
        }
        # Also copy to /tmp as fallback (PrplOS checks both locations)
        mkdir -p /tmp
        cp "/boot/sysupgrade.tgz" "/tmp/sysupgrade.tgz" 2>> "$ENTRYPOINT_LOG" || {
            echo "WARNING: Failed to restore config backup to /tmp/sysupgrade.tgz" >> "$ENTRYPOINT_LOG" 2>&1
        }
        echo "Config backup restored - PrplOS will restore settings during boot" >> "$ENTRYPOINT_LOG" 2>&1
    else
        echo "No config backup found - upgrade will proceed without config restoration" >> "$ENTRYPOINT_LOG" 2>&1
    fi
    
    # Apply new rootfs
    echo "Container upgrade: Applying new rootfs from $NEW_ROOTFS..." >> "$ENTRYPOINT_LOG" 2>&1
    echo "Container upgrade: Applying new rootfs from $NEW_ROOTFS..."
    
    # Remove flag before applying (in case of failure during copy)
    rm -f "$UPGRADE_FLAG"
    echo "Removed upgrade flag" >> "$ENTRYPOINT_LOG" 2>&1
    
    # Copy new filesystem over current (during early boot, minimal processes)
    # This is safe because we're in wrapper script before most services start
    # Use rsync if available, otherwise use cp with proper handling
    if command -v rsync >/dev/null 2>&1; then
        echo "Using rsync to apply new rootfs..." >> "$ENTRYPOINT_LOG" 2>&1
        rsync -a --delete "$NEW_ROOTFS"/ / >> "$ENTRYPOINT_LOG" 2>&1 || {
            echo "Container upgrade: Error applying new rootfs with rsync" >> "$ENTRYPOINT_LOG" 2>&1
            echo "Container upgrade: Error applying new rootfs with rsync"
            exit 1
        }
    else
        # Fallback to cp if rsync not available
        # Use find to copy files individually, overwriting existing files
        echo "Using cp to apply new rootfs..." >> "$ENTRYPOINT_LOG" 2>&1
        (cd "$NEW_ROOTFS" && find . -type f -exec cp -f {} /{} \; 2>> "$ENTRYPOINT_LOG") || {
            echo "Container upgrade: Warning - Some files may not have been copied" >> "$ENTRYPOINT_LOG" 2>&1
        }
        (cd "$NEW_ROOTFS" && find . -type d -exec mkdir -p /{} \; 2>> "$ENTRYPOINT_LOG") || true
        (cd "$NEW_ROOTFS" && find . -type l -exec cp -a {} /{} \; 2>> "$ENTRYPOINT_LOG") || {
            echo "Container upgrade: Warning - Some symlinks may not have been copied" >> "$ENTRYPOINT_LOG" 2>&1
        }
        echo "cp-based upgrade completed (with possible warnings)" >> "$ENTRYPOINT_LOG" 2>&1
    fi
    
    echo "Container upgrade: New rootfs applied successfully" >> "$ENTRYPOINT_LOG" 2>&1
    echo "Container upgrade: New rootfs applied successfully"
    
    # Verify upgrade was applied
    if [ -f /etc/os-release ]; then
        echo "Current version after upgrade:" >> "$ENTRYPOINT_LOG" 2>&1
        grep VERSION /etc/os-release >> "$ENTRYPOINT_LOG" 2>&1 || true
    fi
    
    # Clean up extracted rootfs, firmware image, and upgrade tools
    echo "Cleaning up temporary files and upgrade tools..." >> "$ENTRYPOINT_LOG" 2>&1
    rm -rf "$NEW_ROOTFS"
    # Optionally keep firmware image for reference, or remove it
    # rm -f "$firmware_image"
    
    # Remove squashfs-tools package - it was only needed for upgrade, not part of PrplOS
    # This ensures the upgraded system doesn't have traces of upgrade tools
    # Same approach as initial Dockerfile build - tools used temporarily, then removed
    if command -v opkg >/dev/null 2>&1; then
        echo "Removing temporary upgrade tool: squashfs-tools" >> "$ENTRYPOINT_LOG" 2>&1
        opkg remove squashfs-tools >> "$ENTRYPOINT_LOG" 2>&1 || true
    elif [ -f /usr/bin/unsquashfs ]; then
        # Fallback: remove binary directly if opkg not available
        echo "Removing upgrade tool: /usr/bin/unsquashfs" >> "$ENTRYPOINT_LOG" 2>&1
        rm -f /usr/bin/unsquashfs
    fi
    
    echo "Upgrade completed successfully" >> "$ENTRYPOINT_LOG" 2>&1
fi

echo "=== Container init wrapper completed at $(date) ===" >> "$ENTRYPOINT_LOG" 2>&1

# Continue with normal boot (after upgrade or if upgrade flag was removed)
exec /sbin/init "$@"

