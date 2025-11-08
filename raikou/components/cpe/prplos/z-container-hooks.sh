#!/bin/sh
# Container hook that overrides platform_do_upgrade()
# This script is sourced by /lib/upgrade/do_stage2 after platform.sh
# The 'z-' prefix ensures it's loaded alphabetically after platform.sh

platform_do_upgrade() {
    local diskdev partdev diff
    local image="$1"
    
    v "Container upgrade: Intercepting platform_do_upgrade()"
    
    # Use native PrplOS functions to extract partition data
    # These functions are already available from common.sh (sourced earlier)
    
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
    get_image_dd "$image" of=/tmp/rootfs.img ibs=512 skip="$rootfs_start" count="$rootfs_size"
    
    # Extract SquashFS from the partition image
    # Mount as loop device and copy files
    local loopdev=$(losetup -f)
    if [ -z "$loopdev" ]; then
        v "Container upgrade: Failed to find available loop device"
        rm -f /tmp/rootfs.img /tmp/partmap.image
        return 1
    fi
    
    losetup $loopdev /tmp/rootfs.img || {
        v "Container upgrade: Failed to setup loop device"
        rm -f /tmp/rootfs.img /tmp/partmap.image
        return 1
    }
    
    mount -t squashfs $loopdev /mnt || {
        v "Container upgrade: Failed to mount SquashFS"
        losetup -d $loopdev
        rm -f /tmp/rootfs.img /tmp/partmap.image
        return 1
    }
    
    # Copy new rootfs
    v "Container upgrade: Extracting rootfs to /new_rootfs_pending"
    cp -a /mnt/* /new_rootfs_pending/ || {
        v "Container upgrade: Failed to copy rootfs files"
        umount /mnt
        losetup -d $loopdev
        rm -f /tmp/rootfs.img /tmp/partmap.image
        return 1
    }
    
    umount /mnt
    losetup -d $loopdev
    rm -f /tmp/rootfs.img /tmp/partmap.image
    
    # Create flag for entrypoint to detect upgrade
    mkdir -p /boot
    touch /boot/.do_upgrade
    
    v "Container upgrade: New rootfs extracted to /new_rootfs_pending"
    v "Container upgrade: Upgrade will be applied on next boot"
}

