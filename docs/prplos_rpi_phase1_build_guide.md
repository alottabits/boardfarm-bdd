# prplOS RPi4 Build Guide - Phase 1

**Document Version**: 1.1  
**Created**: January 7, 2026  
**Last Updated**: January 9, 2026  
**Status**: ✅ **Complete**

---

## Overview

This guide provides step-by-step instructions for building prplOS for Raspberry Pi 4. prplOS is based on OpenWrt and uses the OpenWrt build system.

**Version Compatibility:**

- **Tested with**: prplOS 4.0.3 (prplware-v4.0.3)
- **Should work with**: prplOS 3.x and 4.x (OpenWrt-based versions)
- **Note**: Package names and menuconfig structure may vary slightly between versions. If you encounter differences, check the prplOS release notes or GitLab repository for version-specific changes.

---

## Prerequisites

### Hardware Requirements

- **Development Machine**: Linux (Ubuntu/Debian recommended)
  - At least 8GB RAM
  - At least 50GB free disk space
  - Multi-core CPU (build is parallelized)

- **Raspberry Pi 4**:
  - 4GB or 8GB RAM recommended
  - SD Card (32GB+ recommended, Class 10 or better)
  - USB-Ethernet dongle (for WAN interface)
  - USB-to-Serial adapter (for console access)

### Software Requirements

```bash
# Install build dependencies
sudo apt update
sudo apt install -y \
    git \
    build-essential \
    libncurses-dev \
    gawk \
    gettext \
    unzip \
    file \
    libssl-dev \
    wget \
    python3 \
    python3-setuptools \
    rsync

# Note: python3-distutils was removed in Ubuntu 23.04+/Debian 12+ (Python 3.12+)
# python3-setuptools provides similar functionality if needed
# If you're on older Ubuntu/Debian, you can use: libncurses5-dev libncursesw5-dev python3-distutils
```

---

## Step 1: Clone prplOS Source Code

```bash
# Create working directory (can be anywhere with sufficient disk space)
# Option 1: In your projects directory
cd ~/projects/req-tst
mkdir -p prplos-build
cd prplos-build

# Option 2: In home directory
# cd ~
# mkdir -p prplos-build
# cd prplos-build

# Clone prplOS repository
git clone https://gitlab.com/prpl-foundation/prplos/prplos.git
cd prplos

# Check available branches/tags
git branch -a
git tag | tail -10

# Checkout latest stable release (or specific version)
# Example for prplOS 4.0.3:
# git checkout prplware-v4.0.3
# Or for other versions:
# git checkout v3.0.3
# git checkout <latest-tag>
```

**Note**: 
- The repository URL might be `https://git.prplfoundation.org/prplos.git` or require authentication. Check the official prplOS documentation for the correct repository URL.
- **Version Selection**: This guide was tested with prplOS 4.0.3. For other versions, the general process is the same, but package names and menuconfig locations may differ slightly. Always check the version's release notes for changes.

---

## Step 2: Update and Install Feeds

prplOS uses OpenWrt's feed system for package management:

```bash
# Update all feeds
./scripts/feeds update -a

# Install all feeds
./scripts/feeds install -a
```

---

## Step 3: Configure Build for Raspberry Pi 4

```bash
# Launch configuration menu
make menuconfig
```

### Configuration Settings:

Navigate through the menu and set:

1. **Target System**: 
   - Select: `Broadcom BCM27xx`

2. **Subtarget**: 
   - Select: `BCM2711 boards (64 bit)`

3. **Target Profile**: 
   - Select: `Raspberry Pi 4B/400/CM4 (64bit)`
   - **Important**: Look for a "prpl" profile option - if available, select it to include prplOS-specific packages

4. **Additional Packages** (required for testbed setup):
   
   **Required Packages for Testbed:**
   
   - **Network Management**:
     - `netifd` - Network Interface Daemon (required for UCI-based network management)
     - Navigate to: `Base system → netifd` → Enable
   
   - **Web UI**:
     - `luci` - LuCI web interface (full collection)
     - Navigate to: `LuCI → Collections → luci` → Enable
     - This automatically enables: `luci-base`, `luci-mod-admin-full`, `luci-mod-network`, `luci-mod-status`, `luci-mod-system`, `luci-theme-bootstrap`, `uhttpd`, `uhttpd-mod-ubus`
   
   - **USB Ethernet Driver** (for USB-Ethernet dongle):
     - `kmod-usb-net-rtl8152` - Kernel module for Realtek RTL8152/RTL8153 USB Ethernet adapters
     - Navigate to: `Kernel modules → USB Support → kmod-usb-net-rtl8152` → Enable
     - `r8152-firmware` - Firmware for Realtek RTL8152/RTL8153 devices
     - Navigate to: `Firmware → r8152-firmware` → Enable
   
   **Note**: prplOS includes TR-069 client (`obuspa`), network stack, serial console, and container runtime (`lxc`) by default via the prpl profile. The packages listed above are additional requirements for the testbed setup.
   
   **Alternative**: Enable packages via `.config` file:
   
   ```bash
   # Add to .config file or Rpi4_base.config
   CONFIG_PACKAGE_netifd=y
   CONFIG_PACKAGE_luci=y
   CONFIG_PACKAGE_kmod-usb-net-rtl8152=y
   CONFIG_PACKAGE_r8152-firmware=y
   ```
   
   **Version-Specific Notes**:
   - Package names are generally consistent across prplOS versions
   - If a package is not found in menuconfig, check if it's included by default in your version
   - Some packages may have been renamed or moved between versions (e.g., `luci` collection structure)
   - USB Ethernet driver names may vary - check `dmesg` output on your RPi to identify the correct driver

**Quick Check**: After selecting Target Profile, look for any "prpl" or "prplOS" profile option in the menu. If you see it, select it to ensure all prplOS-specific packages are included.

5. **Save Configuration**:
   - Press `F6` to save configuration
   - Save as `.config` (default)
   - Press `F9` to exit

**Alternative**: If you have a known-good `.config` file, you can copy it:

```bash
# Copy existing config (if available)
cp <path-to-config> .config

# Or use defconfig
make defconfig
```

---

## Step 4: Build prplOS

```bash
# Clean previous builds (optional, but recommended for first build)
make clean

# Start build process
# Use -j$(nproc) to use all CPU cores for faster builds
make -j$(nproc) V=s

# Or for less verbose output:
make -j$(nproc)
```

**Important**: If you're using `pyenv` and encounter "Argument list too long" errors during the build, temporarily bypass pyenv:

**Option 1: Fix the Python symlink (Quick fix)**
```bash
# Remove pyenv from PATH and use system Python directly
export PATH=$(echo $PATH | tr ':' '\n' | grep -v pyenv | tr '\n' ':' | sed 's/:$//')
export PYTHON=/usr/bin/python3

# Fix the symlink in staging_dir (build artifact only, won't affect your Python dev environment)
rm staging_dir/host/bin/python3
ln -s /usr/bin/python3 staging_dir/host/bin/python3

# Then rebuild
make -j$(nproc) V=s
```

**Option 2: Clean and rebuild host tools (Cleaner, takes longer)**
```bash
# Remove pyenv from PATH and use system Python directly
export PATH=$(echo $PATH | tr ':' '\n' | grep -v pyenv | tr '\n' ':' | sed 's/:$//')
export PYTHON=/usr/bin/python3

# Clean the problematic host tools
rm -rf staging_dir/host/bin/python3 build_dir/host/ninja-1.11.1

# Rebuild host tools with correct Python
make -j$(nproc) tools/ninja/compile

# Then continue with full build
make -j$(nproc) V=s
```

**Note**: These changes only affect the prplOS build directory and won't interfere with pyenv, uv, or any Python development tools outside this directory.

**Build Time**: Depending on your system, this can take 1-4 hours.

**Build Output**: The built image will be located at:
```
bin/targets/bcm27xx/bcm2711/openwrt-bcm27xx-bcm2711-rpi-4-squashfs-sysupgrade.img
```

Or check the `bin/targets/bcm27xx/bcm2711/` directory for all build artifacts.

---

## Step 5: Verify Build Output

```bash
# List build artifacts
ls -lh bin/targets/bcm27xx/bcm2711/

# Expected files:
# - openwrt-bcm27xx-bcm2711-rpi-4-squashfs-sysupgrade.img (sysupgrade image)
# - openwrt-bcm27xx-bcm2711-rpi-4-ext4-sysupgrade.img (ext4 sysupgrade image)
# - openwrt-bcm27xx-bcm2711-rpi-4-squashfs-factory.img (factory image)
# - openwrt-bcm27xx-bcm2711-rpi-4-ext4-factory.img (ext4 factory image)
# - kernel, rootfs, and other artifacts

# Check image size (should be reasonable, not too large)
du -h bin/targets/bcm27xx/bcm2711/*.img
```

**Note**: For initial flashing, use the `factory.img` file. For upgrades, use `sysupgrade.img`.

---

## Step 6: Flash prplOS to SD Card

### 6.1 Identify SD Card Device

```bash
# List block devices
lsblk

# Or check dmesg after inserting SD card
dmesg | tail -20

# SD card will typically be /dev/sdX or /dev/mmcblkX
# WARNING: Make sure you identify the correct device!
```

### 6.2 Flash Image to SD Card

**Method 1: Using `dd` (Linux)**

```bash
# Unmount any mounted partitions
sudo umount /dev/sdX*  # Replace X with your SD card device

# Flash factory image
sudo dd if=bin/targets/bcm27xx/bcm2711/openwrt-bcm27xx-bcm2711-rpi-4-squashfs-factory.img \
        of=/dev/sdX \
        bs=4M \
        status=progress \
        conv=fsync

# Wait for completion
sync
```

**Method 2: Using `balena-etcher` (GUI, cross-platform)**

1. Download balena-etcher from https://www.balena.io/etcher/
2. Launch balena-etcher
3. Select the factory image file
4. Select the SD card
5. Click "Flash!"

**Method 3: Using `rpi-imager` (Raspberry Pi official tool)**

```bash
# Install rpi-imager
sudo apt install rpi-imager

# Launch and use GUI to flash image
rpi-imager
```

---

## Step 7: Boot and Verify RPi4

### 7.1 Initial Boot

1. **Insert SD card** into RPi4
2. **Connect USB-to-Serial adapter** to RPi4 GPIO pins:
   - GND → GND
   - TX → GPIO 14 (UART0 TX)
   - RX → GPIO 15 (UART0 RX)
3. **Connect USB-Ethernet dongle** to RPi4 USB port
4. **Power on** RPi4

### 7.2 Access Serial Console

```bash
# Connect via serial console
picocom -b 115200 /dev/ttyUSB0

# Or using screen
screen /dev/ttyUSB0 115200

# Or using minicom
minicom -D /dev/ttyUSB0 -b 115200
```

**Note**: Adjust `/dev/ttyUSB0` to match your serial adapter device.

### 7.3 Verify Boot and prplOS

Once connected via serial console, you should see boot messages. After boot completes:

```bash
# Check prplOS version
cat /etc/openwrt_release
# or
cat /etc/prplos_release  # if prplOS-specific file exists

# Check kernel version
uname -a

# Check network interfaces
ip link show

# Expected interfaces:
# - lo (loopback)
# - eth0 (native Ethernet - LAN)
# - eth1 (USB-Ethernet dongle - WAN, if connected)
# - br-lan (LAN bridge, if configured)

# Check TR-069 client (prplOS native)
ps aux | grep -i tr069
# or
ps aux | grep -i acs
# or check for prplOS-specific TR-069 process names

# Check if container runtime is available
which docker
# or
which podman
# or check for prplOS container runtime
```

### 7.4 Note Interface Names and MAC Addresses

```bash
# Get MAC addresses
ip link show | grep -A 1 "eth"

# Or more detailed
for iface in $(ip link show | grep -E "^[0-9]+:" | awk -F: '{print $2}' | tr -d ' '); do
    echo "Interface: $iface"
    ip link show $iface | grep "link/ether"
done

# Note down:
# - Native Ethernet MAC (LAN interface)
# - USB-Ethernet dongle MAC (WAN interface)
# - Interface names (eth0, eth1, etc.)
```

**Document these values** - they'll be needed for Boardfarm configuration!

---

## Step 8: Verify Required Components

### 8.1 Check TR-069 Client

```bash
# Check if TR-069 client is running
ps aux | grep -i "tr069\|cwmp\|acs"

# Check TR-069 configuration (if accessible)
# prplOS uses TR-181 data model
# Check Device.ManagementServer parameters
```

### 8.2 Check Network Stack

```bash
# Verify routing
ip route show

# Verify NAT (if configured)
iptables -t nat -L -n -v

# Verify firewall
iptables -L -n -v
```

### 8.3 Check Container Runtime

```bash
# Check if container runtime is available
which docker || which podman || which containerd

# Check container runtime version
docker --version || podman --version || containerd --version
```

---

## Troubleshooting

### Build Issues

**Issue**: Build fails with dependency errors
```bash
# Solution: Install missing dependencies
sudo apt install -y <missing-package>

# Or update feeds and retry
./scripts/feeds update -a
./scripts/feeds install -a
```

**Issue**: Build runs out of disk space
```bash
# Solution: Clean build directory
make clean
# Or increase disk space
```

**Issue**: Build is very slow
```bash
# Solution: Use more CPU cores
make -j$(nproc)
# Or reduce parallelism if system is unstable
make -j4
```

### Boot Issues

**Issue**: RPi4 doesn't boot
- Check SD card is properly flashed
- Verify image is for correct RPi model (RPi4, not RPi3)
- Check power supply is adequate (official RPi4 power supply recommended)
- Check serial console connection

**Issue**: No serial console output
- Verify serial adapter connections (TX/RX might be swapped)
- Check baud rate (115200)
- Try different serial adapter
- Check `/dev/ttyUSB0` device permissions: `sudo chmod 666 /dev/ttyUSB0`

**Issue**: Network interfaces not detected
- Check USB-Ethernet dongle is compatible with Linux
- Verify dongle is connected before boot
- Check `dmesg` for USB device detection
- Try different USB port on RPi4

**Issue**: Package not found in menuconfig (version-specific)
- Package may be included by default in your prplOS version
- Package may have been renamed or moved (check prplOS release notes)
- Package may not be available in your version's feeds
- Try searching for alternative package names or check if functionality is built-in

**Issue**: Build fails with "package not found" errors
- Update feeds: `./scripts/feeds update -a && ./scripts/feeds install -a`
- Check if package exists in feeds: `./scripts/feeds list | grep <package-name>`
- Verify you're using a compatible prplOS version (check GitLab tags/branches)

---

## Next Steps

After successfully completing Phase 1:

1. ✅ prplOS image built for RPi4
2. ✅ RPi4 boots successfully
3. ✅ Serial console access working
4. ✅ Network interfaces identified
5. ✅ MAC addresses documented

**Proceed to Phase 2**: Network Configuration
- See [`prplos_rpi_implementation_plan.md`](./prplos_rpi_implementation_plan.md) for Phase 2 details

---

## References

- prplOS GitLab: https://gitlab.com/prpl-foundation/prplos/prplos
- prplOS Documentation: https://prplfoundation.org/working-groups/prplos/
- OpenWrt Build System: https://openwrt.org/docs/guide-developer/build-system/start
- Raspberry Pi 4 Documentation: https://www.raspberrypi.com/documentation/

---

**Document End**

