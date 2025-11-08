#!/bin/sh
# Container entrypoint script that handles boot-time upgrade application
# This script bridges the containerization gap where FLASH mounting would occur

UPGRADE_FLAG="/boot/.do_upgrade"
NEW_ROOTFS="/new_rootfs_pending"
OLD_ROOTFS="/old_root"
ENTRYPOINT_LOG="/boot/entrypoint_debug.log"

# Log entrypoint execution
echo "=== Entrypoint script started at $(date) ===" >> "$ENTRYPOINT_LOG" 2>&1
echo "Checking for upgrade flag: $UPGRADE_FLAG" >> "$ENTRYPOINT_LOG" 2>&1

# Check if upgrade is pending
if [ -f "$UPGRADE_FLAG" ]; then
    echo "Container upgrade: Applying new rootfs..." >> "$ENTRYPOINT_LOG" 2>&1
    echo "Container upgrade: Applying new rootfs..."
    
    # Backup current rootfs (for potential rollback validation)
    if [ -d "$NEW_ROOTFS" ]; then
        echo "Found $NEW_ROOTFS directory" >> "$ENTRYPOINT_LOG" 2>&1
        # Backup current rootfs (best effort - may fail for some files)
        echo "Container upgrade: Backing up current rootfs to $OLD_ROOTFS" >> "$ENTRYPOINT_LOG" 2>&1
        echo "Container upgrade: Backing up current rootfs to $OLD_ROOTFS"
        mkdir -p "$OLD_ROOTFS" 2>> "$ENTRYPOINT_LOG" || true
        # Backup only essential directories, excluding virtual filesystems
        # This is best-effort and errors are expected for some files
        for dir in bin etc lib lib64 opt root sbin usr var www; do
            if [ -d "/$dir" ]; then
                cp -a "/$dir" "$OLD_ROOTFS"/ 2>> "$ENTRYPOINT_LOG" || true
            fi
        done
        echo "Backup completed (best effort)" >> "$ENTRYPOINT_LOG" 2>&1
        
        # Apply new rootfs
        echo "Container upgrade: Applying new rootfs from $NEW_ROOTFS..." >> "$ENTRYPOINT_LOG" 2>&1
        echo "Container upgrade: Applying new rootfs from $NEW_ROOTFS..."

        # Remove flag before applying (in case of failure during copy)
        rm -f "$UPGRADE_FLAG"
        echo "Removed upgrade flag" >> "$ENTRYPOINT_LOG" 2>&1
        
        # Copy new filesystem over current (during early boot, minimal processes)
        # This is safe because we're in entrypoint before most services start
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
        
        # Clean up extracted rootfs (optional - can keep for debugging)
        # rm -rf "$NEW_ROOTFS"
    else
        echo "Container upgrade: Flag present but $NEW_ROOTFS not found, skipping" >> "$ENTRYPOINT_LOG" 2>&1
        echo "Container upgrade: Flag present but $NEW_ROOTFS not found, skipping"
        rm -f "$UPGRADE_FLAG"
    fi
else
    echo "No upgrade flag found, continuing normal boot" >> "$ENTRYPOINT_LOG" 2>&1
fi

echo "=== Entrypoint script completed at $(date) ===" >> "$ENTRYPOINT_LOG" 2>&1

# Continue with normal boot
exec /sbin/init "$@"

