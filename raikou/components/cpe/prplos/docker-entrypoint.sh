#!/bin/sh
# Container entrypoint script that handles boot-time upgrade application
# This script bridges the containerization gap where FLASH mounting would occur

UPGRADE_FLAG="/boot/.do_upgrade"
NEW_ROOTFS="/new_rootfs_pending"
OLD_ROOTFS="/old_root"

# Wait for eth1 interface to be available (added by Raikou)
# and populate HWMACADDRESS in /etc/environment if not already set
if ! grep -q 'HWMACADDRESS="[^"]*"' /etc/environment 2>/dev/null; then
    # Wait for eth1 to be created by Raikou
    while [ ! -f /sys/class/net/eth1/address ]; do
        echo "Waiting for eth1 interface to be created by Raikou..."
        sleep 1
    done
    
    # Read MAC address from eth1
    ETH1_MAC=$(cat /sys/class/net/eth1/address 2>/dev/null || echo "")
    if [ -n "$ETH1_MAC" ]; then
        # Update or add HWMACADDRESS to /etc/environment
        if grep -q "^export HWMACADDRESS=" /etc/environment 2>/dev/null; then
            sed -i "s|^export HWMACADDRESS=.*|export HWMACADDRESS=\"$ETH1_MAC\"|" /etc/environment
        else
            echo "export HWMACADDRESS=\"$ETH1_MAC\"" >> /etc/environment
        fi
        echo "Set HWMACADDRESS=$ETH1_MAC in /etc/environment"
    fi
fi

# Check if upgrade is pending
if [ -f "$UPGRADE_FLAG" ]; then
    echo "Container upgrade: Applying new rootfs..."
    
    # Backup current rootfs (for potential rollback validation)
    if [ -d "$NEW_ROOTFS" ]; then
        # Backup current rootfs (best effort - may fail for some files)
        echo "Container upgrade: Backing up current rootfs to $OLD_ROOTFS"
        mkdir -p "$OLD_ROOTFS" 2>/dev/null || true
        cp -a / "$OLD_ROOTFS"/ 2>/dev/null || {
            echo "Container upgrade: Warning - Could not complete full backup (some files may be in use)"
            # Continue anyway - this is best effort
        }
        
        # Apply new rootfs
        echo "Container upgrade: Applying new rootfs from $NEW_ROOTFS..."
        
        # Remove flag before applying (in case of failure during copy)
        rm -f "$UPGRADE_FLAG"
        
        # Copy new filesystem over current (during early boot, minimal processes)
        # This is safe because we're in entrypoint before most services start
        # Use rsync if available, otherwise use cp
        if command -v rsync >/dev/null 2>&1; then
            rsync -a --delete "$NEW_ROOTFS"/ / || {
                echo "Container upgrade: Error applying new rootfs with rsync"
                exit 1
            }
        else
            # Fallback to cp if rsync not available
            cp -a "$NEW_ROOTFS"/* / || {
                echo "Container upgrade: Error applying new rootfs with cp"
                exit 1
            }
        fi
        
        echo "Container upgrade: New rootfs applied successfully"
        
        # Clean up extracted rootfs (optional - can keep for debugging)
        # rm -rf "$NEW_ROOTFS"
    else
        echo "Container upgrade: Flag present but $NEW_ROOTFS not found, skipping"
        rm -f "$UPGRADE_FLAG"
    fi
fi

# Continue with normal boot
exec /sbin/init "$@"

