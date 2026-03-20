# prplOS Raspberry Pi Gateway Implementation Plan

**Document Version**: 1.2  
**Created**: January 7, 2026  
**Last Updated**: January 11, 2026  
**Status**: ✅ **Phase 1-4 Complete** - Testing In Progress

---

## Executive Summary

This document outlines the plan to integrate a physical Raspberry Pi 4 running prplOS as the gateway device in the Boardfarm testbed. This replaces the containerized PrplOS CPE with real hardware, enabling more realistic testing scenarios while maintaining native TR-069/ACS support and access to prplOS containerized applications.

### Key Benefits

1. **Native TR-069/ACS Support** - prplOS includes built-in TR-069 client, eliminating the need for third-party clients (unlike OpenWrt)
2. **Real Hardware Testing** - Test actual routing, NAT, firewall, and network behavior on physical hardware
3. **Containerized Applications** - Access to prplOS container ecosystem for extended functionality
4. **Production Similarity** - Closer to real-world deployment scenarios
5. **TR-181 Data Model** - Full TR-181 support (same as containerized PrplOS)
6. **Existing Device Class Compatibility** - Can leverage existing `PrplDockerCPE` patterns

### Decision Rationale

After evaluating OpenWrt for RPi integration, prplOS was selected because:
- **TR-069 Support**: Native ACS client built-in (no need for easycwmp or other third-party clients)
- **Containerized Apps**: prplOS supports containerized applications for extended functionality
- **Consistency**: Same firmware stack as containerized CPE, ensuring test consistency
- **TR-181 Model**: Full TR-181 data model support for comprehensive ACS testing

---

## Network Topology

**Note**: The network topology is identical to the corrected OpenWrt topology. See [`openwrt_topology_correction_migration.md`](./openwrt_topology_correction_migration.md) for complete topology details.

### Correct Architecture

```
Internet
    │
    ▼
Host NAT (rtr-uplink)
    │
    ▼
Router Container (ISP Edge Router) ← Sits BETWEEN CPE and ISP Services
    │
    ├─── eth1 (172.25.1.1) → rtr-wan → ISP Services (DHCP, ACS, WAN)
    │
    └─── cpe (10.1.1.1) → cpe-rtr → prplOS RPi (Home Gateway)
```

**Key Architecture Points:**

1. **Router Container (ISP Edge Router)** sits BETWEEN CPE and ISP Services:
   
   - **CPE-facing**: `cpe` interface (10.1.1.1/24) on `cpe-rtr` bridge
   - **ISP-facing**: `eth1` interface (172.25.1.1/24) on `rtr-wan` bridge  
   - **Internet-facing**: `aux0` interface (172.25.2.1/24) on `rtr-uplink` bridge

2. **prplOS RPi (Home Gateway)** replaces CPE container:
   
   - WAN connects to `cpe-rtr` bridge (10.1.1.x network)
   - LAN gateway connects to `lan-cpe` bridge (192.168.10.x network)
   
3. **LAN Container** remains as a client device:
   
   - Test client device (DHCP client, HTTP proxy) on LAN side
   - Connects to `lan-cpe` bridge to test CPE functionality
   - Not part of the home gateway - it's a test tool

**Traffic Flow:**

```
prplOS RPi (10.1.1.100)
    │
    ▼ eth1 (WAN)
cpe-rtr bridge (10.1.1.x)
    │
    ▼ cpe interface
Router Container (ISP Edge Router) ← Sits BETWEEN CPE and ISP Services
    │ Routes & NATs: 10.1.1.x → 172.25.1.1
    ▼ eth1 interface
rtr-wan bridge (172.25.1.x)
    │
    ▼
ISP Services (DHCP .20, ACS .40, WAN .2)
```

**Key Characteristics:**

- CPE is a physical Raspberry Pi 4 with prplOS (replaces CPE container)
- WAN via USB-Ethernet dongle (DHCP client, gets 10.1.1.x from Router DHCP relay)
- LAN gateway via native Ethernet (provides DHCP server for LAN clients)
- Access via serial console only (LAN network is isolated on `lan-cpe` bridge)
- Router container is ISP Edge Router: Routes CPE traffic to ISP services (WAN, ACS, DHCP)
- Internet access via Router → rtr-uplink → Host NAT

---

## Implementation Phases

### Phase 1: prplOS Image Build for RPi4 (Day 1-2)

#### 1.1 Research prplOS Build System

**Tasks:**
- [x] Identify prplOS build system (OpenWrt-based? Yocto? Custom?) → **OpenWrt-based**
- [x] Locate prplOS source repository and build documentation → **GitLab: https://gitlab.com/prpl-foundation/prplos/prplos**
- [x] Determine RPi4 target configuration (bcm27xx/bcm2711, aarch64) → **BCM27xx, BCM2711 boards (64 bit), RPi 4B/400/CM4**
- [x] Check for existing RPi4 builds or build configurations → **Need to build from source**

**Resources:**
- prplOS GitLab: https://gitlab.com/prpl-foundation/prplos/prplos
- **Detailed Build Guide**: See [`prplos_rpi_phase1_build_guide.md`](./prplos_rpi_phase1_build_guide.md)

#### 1.2 Build prplOS Image for RPi4 ✅ **COMPLETE**

**Tasks:**
- [x] Set up build environment (if needed) → **Build environment configured, pyenv workaround applied**
- [x] Configure build for RPi4 target (bcm27xx/bcm2711, aarch64) → **Rpi4_base.config created and used**
- [x] Build prplOS image (.img file) → **Build completed successfully**
- [ ] Verify image contains required components:
  - TR-069 client (prplOS native) → **To be verified after boot**
  - Network stack (routing, NAT, firewall) → **To be verified after boot**
  - Container runtime support → **To be verified after boot**
  - Serial console support → **To be verified after boot**

**Build Output:**
- ✅ `openwrt-bcm27xx-bcm2711-rpi-4-squashfs-sysupgrade.img.gz` (15M) - **Recommended for upgrade**
- ✅ `openwrt-bcm27xx-bcm2711-rpi-4-ext4-sysupgrade.img.gz` (16M) - Alternative ext4 variant
- ✅ Factory images available for fresh installs
- ✅ Location: `bin/targets/bcm27xx/bcm2711/`

**Build Notes:**
- Build completed successfully on 2026-01-09
- pyenv workaround applied (symlink fix in staging_dir/host/bin/python3)
- Build artifacts verified with SHA256 checksums

**Required Packages Enabled:**
- `CONFIG_PACKAGE_netifd=y` - Network Interface Daemon (UCI-based network management)
- `CONFIG_PACKAGE_luci=y` - LuCI web UI (includes luci-base, luci-mod-admin-full, luci-mod-network, luci-mod-status, luci-mod-system, luci-theme-bootstrap, uhttpd, uhttpd-mod-ubus)
- `CONFIG_PACKAGE_kmod-usb-net-rtl8152=y` - USB Ethernet driver for Realtek RTL8152/RTL8153 dongles
- `CONFIG_PACKAGE_r8152-firmware=y` - Firmware for Realtek RTL8152/RTL8153 devices
- `CONFIG_PACKAGE_icwmp=y` - TR-069 CWMP client daemon (connects to ACS)
- `CONFIG_PACKAGE_obuspa=y` - USP (TR-369) agent
- `CONFIG_PACKAGE_bbfdmd=y` - BBF Data Model daemon (provides TR-181 parameters)
- `CONFIG_BBF_VENDOR_PREFIX="X_PRPL_"` - Vendor prefix for bbfdm (required for build)

**Note**: See [`prplos_rpi_phase1_build_guide.md`](./prplos_rpi_phase1_build_guide.md) for detailed package selection instructions.

#### 1.3 Flash and Boot RPi4 ✅ **COMPLETE**

**Tasks:**
- [x] Flash prplOS image to SD card → **Completed**
- [x] Boot RPi4 and verify basic functionality → **prplOS 4.0.3 booted successfully**
- [x] Access via serial console (115200 baud) → **Serial console working**
- [x] Verify network interfaces:
  - [x] Native Ethernet (LAN) → **eth0: 88:a2:9e:69:ee:1d**
  - [x] USB-Ethernet dongle (WAN) → **eth1: 00:e0:4c:1f:65:b8**
- [x] Note interface names and MAC addresses → **Documented**

**Boot Script Configuration:**
- Created `/etc/init.d/network-setup` script for automatic network configuration
- Created `/usr/share/udhcpc/default.script` for DHCP IP configuration
- Scripts verified working after reboot ✅

**Verification Results:**
- prplOS version: OpenWrt 4.0.3 r0+25295-f0797dde19
- Kernel: Linux 5.15.167
- Interfaces verified: eth0 (LAN), eth1 (WAN), wlan0 (WiFi), br-lan (bridge)

**Verification Commands:**

```bash
# Access via serial console
picocom -b 115200 /dev/ttyUSB0

# Once connected, verify prplOS version
cat /etc/prplos_release  # or similar

# Check network interfaces
ip link show

# Check TR-069 client status
ps aux | grep -i tr069  # or check for prplOS ACS client process
```

---

### Phase 2: Network Configuration (Day 2-3)

#### 2.1 Configure WAN Interface ✅ **COMPLETE**

**Tasks:**
- [x] Configure WAN interface (USB dongle) for DHCP client → **Configured via UCI, manual setup script created**
- [x] Verify WAN interface gets IP from Router DHCP relay (10.1.1.100+) → **IP: 10.1.1.100/24**
- [x] Configure default route via Router (10.1.1.1) → **Default route configured**

**Configuration Details:**
- WAN interface: eth1 (USB-Ethernet dongle)
- WAN IP: 10.1.1.100/24 (from Router DHCP relay via DHCP container at 172.25.1.20)
- Default route: via 10.1.1.1 dev eth1 (configured automatically by DHCP)
- DHCP client: udhcpc with custom script at `/usr/share/udhcpc/default.script`
- Boot script: `/etc/init.d/network-setup` (START=20, runs automatically at boot)
- **No fallback IP**: Script relies entirely on DHCP - if DHCP fails, interface will have no IP (clear failure indication)

**prplOS Configuration:**

prplOS uses TR-181 data model. Configuration via:
- TR-069 ACS (preferred)
- UCI-like commands (if available)
- Direct TR-181 parameter access

**Expected Configuration:**

```bash
# WAN Interface Configuration
# Device.IP.Interface.1 (WAN)
# - Enable: true
# - Type: IP
# - IPv4Enable: true
# - IPv4AddressingType: DHCP
# - LowerLayers: USB Ethernet dongle interface

# Default Route
# Device.Routing.Router.1.IPv4Forwarding.1
# - Interface: WAN interface
# - GatewayIPAddress: 10.1.1.1
```

#### 2.2 Configure LAN Interface ✅ **COMPLETE**

**Tasks:**
- [x] Configure LAN interface (native Ethernet) as gateway → **br-lan bridge configured**
- [x] Set LAN IP address (192.168.10.1/24) → **IP configured**
- [ ] Enable DHCP server for LAN clients → **To be verified (dnsmasq running)**
- [x] Configure LAN bridge if needed → **br-lan bridge with eth0 as member**

**Configuration Details:**
- LAN bridge: br-lan
- LAN IP: 192.168.10.1/24
- Bridge members: eth0 (native Ethernet)
- DHCP server: dnsmasq (running, needs verification)
- Boot script: Automatically brings up br-lan at boot

**Expected Configuration:**

```bash
# LAN Interface Configuration
# Device.IP.Interface.2 (LAN)
# - Enable: true
# - Type: IP
# - IPv4Enable: true
# - IPv4AddressingType: Static
# - IPv4Address: 192.168.10.1/24
# - LowerLayers: Native Ethernet interface

# DHCP Server
# Device.DHCPv4.Server.Pool.1
# - Interface: LAN interface
# - MinAddress: 192.168.10.100
# - MaxAddress: 192.168.10.200
```

#### 2.3 Verify Network Connectivity ✅ **COMPLETE**

**Tasks:**
- [x] Verify WAN IP assignment (10.1.1.100+) → **10.1.1.100/24 confirmed**
- [x] Verify default route (via 10.1.1.1) → **Default route via 10.1.1.1 confirmed**
- [x] Test connectivity to Router (ping 10.1.1.1) → **✅ Working**
- [x] Test connectivity to ISP services (ping 172.25.1.2) → **✅ Working**
- [x] Test internet connectivity (ping 8.8.8.8) → **✅ Working (TTL=115, ~17-20ms avg)**
- [ ] Verify LAN clients can get IP addresses → **To be tested**

**Connectivity Test Results:**
- Router (10.1.1.1): ✅ 0% packet loss
- WAN container (172.25.1.2): ✅ 0% packet loss  
- Internet (8.8.8.8): ✅ 0% packet loss, ~17-20ms average RTT

**Boot Verification:**
- ✅ Network configuration works automatically after reboot
- ✅ DHCP obtains IP from Router DHCP relay (172.25.1.20)
- ✅ All interfaces come up correctly (eth1 WAN, br-lan LAN)
- ✅ Internet connectivity verified after reboot

**Verification Commands:**

```bash
# Check WAN IP
ip addr show <wan_interface>
# Should show: 10.1.1.100+ (from Router DHCP relay)

# Check default route
ip route show default
# Should show: default via 10.1.1.1 dev <wan_interface>

# Test connectivity
ping -c 2 10.1.1.1      # Router
ping -c 2 172.25.1.2    # WAN container
ping -c 2 8.8.8.8       # Internet
```

---

### Phase 3: Device Class Implementation (Day 3-5) ✅ **COMPLETE**

#### 3.1 Create RPiPrplOSCPE Device Class

**File**: `boardfarm/boardfarm3/devices/rpiprplos_cpe.py`

**Tasks:**
- [ ] Create `RPiPrplOSHW` class (hardware abstraction)
  - Inherit from `CPEHW`
  - Implement serial console connection
  - Implement MAC address retrieval
  - Implement serial number retrieval
  - Implement power cycle (if supported)
- [ ] Create `RPiPrplOSSW` class (software operations)
  - Inherit from `CPESwLibraries`
  - Implement TR-181 parameter access
  - Implement TR-069 operations (via ACS)
  - Implement network configuration
  - Implement version retrieval
- [ ] Create `RPiPrplOSCPE` class (main device class)
  - Inherit from `CPE` and `BoardfarmDevice`
  - Compose `RPiPrplOSHW` and `RPiPrplOSSW`
  - Implement boardfarm hooks

**Reference Implementations:**
- `boardfarm/boardfarm3/devices/prplos_cpe.py` - PrplDockerCPE (containerized)
- `boardfarm/boardfarm3/devices/rpirdkb_cpe.py` - RPiRDKBCPE (RPi hardware)

**Key Methods:**

```python
# RPiPrplOSHW
- connect_to_consoles()    # Serial console connection
- power_cycle()            # Soft reboot via serial console
- mac_address              # From WAN interface
- serial_number            # From RPi CPU info

# RPiPrplOSSW  
- version                  # prplOS release version
- get_parameter()          # TR-181 parameter access
- set_parameter()          # TR-181 parameter modification
- reboot()                 # Device reboot
- get_interface_ip()       # Get IP address of interface
```

#### 3.2 Register Device Class

**File**: `boardfarm/boardfarm3/plugins/core.py`

**Tasks:**
- [ ] Add `RPiPrplOSCPE` to device registry
- [ ] Register device type: `bf_rpiprplos_cpe` or `bf_prplos_rpi`

**Example:**

```python
def boardfarm_add_devices() -> dict[str, type[BoardfarmDevice]]:
    return {
        # ... existing devices ...
        "bf_rpiprplos_cpe": RPiPrplOSCPE,
    }
```

#### 3.3 Create Boardfarm Configuration

**File**: `boardfarm-bdd/bf_config/boardfarm_config_prplos_rpi.json`

**Tasks:**
- [ ] Create device configuration entry
- [ ] Configure serial console connection
- [ ] Configure interface names (WAN, LAN)
- [ ] Configure MAC addresses
- [ ] Reference ACS and other devices

**Template:**

```json
{
    "prplos-rpi-1": {
        "devices": [
            {
                "conn_cmd": [
                    "picocom -b 115200 /dev/ttyUSB0"
                ],
                "connection_type": "local_cmd",
                "lan_iface": "<lan_interface_name>",
                "name": "board",
                "type": "bf_rpiprplos_cpe",
                "wan_iface": "<wan_interface_name>",
                "wan_mac": "<usb_dongle_mac_address>"
            },
            {
                "name": "wan",
                "type": "bf_wan",
                // ... existing wan config ...
            },
            {
                "name": "lan",
                "type": "bf_lan",
                // ... existing lan config ...
            },
            {
                "name": "genieacs",
                "type": "bf_acs",
                // ... existing ACS config ...
            }
            // ... other devices unchanged ...
        ]
    }
}
```

---

### Phase 4: TR-069/ACS Integration (Day 4-5) ✅ **COMPLETE**

#### 4.1 Configure TR-069 Client

**Tasks:**
- [x] Configure ACS URL (http://172.25.1.40:7547)
- [x] Configure ACS credentials (if required)
- [x] Enable TR-069 client
- [x] Verify ACS registration

**prplOS TR-069 Architecture:**

prplOS uses `icwmpd` as the TR-069 CWMP client, which interacts with the `bbfdm` (Broadband Forum Data Model) service via ubus. The key components are:

- **`icwmpd`** - TR-069 CWMP client daemon
- **`bbfdmd`** - BBF Data Model daemon (provides TR-181 parameters)
- **`sysmngr`** - System manager (provides Device.DeviceInfo.* parameters to bbfdm)
- **`obuspa`** - USP (TR-369) agent (optional, for USP support)

**⚠️ CRITICAL Configuration Requirements:**

The TR-069 connection requires specific UCI configuration. The `sysmngr` service reads device identity from UCI `cwmp.cpe.*` options first, NOT from `/etc/device_info` or `/var/etc/environment`.

**Required UCI Configuration:**

```bash
# 1. Device Identity (read by sysmngr for Device.DeviceInfo.* parameters)
uci set cwmp.cpe.manufacturer='prpl Foundation'
uci set cwmp.cpe.manufacturer_oui='00E04C'         # OUI from WAN MAC address
uci set cwmp.cpe.product_class='RPi4prplOS'        # No special chars (avoids URL encoding)
uci set cwmp.cpe.serial_number='1000000045048244'  # RPi serial from /proc/cpuinfo
uci set cwmp.cpe.model_name='RPi4prplOS'           # Model name
uci set cwmp.cpe.software_version='r0+25295-f0797dde19'  # From /etc/openwrt_version

# 2. WAN Interface Configuration (CRITICAL!)
# This must be the ACTUAL DEVICE NAME (e.g., 'eth1'), NOT the netifd interface name (e.g., 'wan')
# icwmpd uses this to determine the IP address for ConnectionRequestURL
uci set cwmp.cpe.interface='eth1'

# 3. Commit changes
uci commit cwmp

# 4. Restart services to apply changes
/etc/init.d/sysmngr restart   # Reloads device identity from UCI
sleep 3
/etc/init.d/icwmpd restart    # Reconnects to ACS with new identity
```

**ACS URL Configuration via bbfdm:**

```bash
# Set ACS URL via TR-181 data model
ubus call bbfdm set '{"path": "Device.ManagementServer.URL", "value": "http://172.25.1.40:7547"}'

# Enable periodic inform
ubus call bbfdm set '{"path": "Device.ManagementServer.PeriodicInformEnable", "value": "true"}'
ubus call bbfdm set '{"path": "Device.ManagementServer.PeriodicInformInterval", "value": "300"}'
```

**Verification Commands:**

```bash
# Check icwmpd is running
ps | grep icwmpd

# Check bbfdm service
ubus list | grep bbfdm

# Verify device identity in bbfdm
ubus call bbfdm get '{"path": "Device.DeviceInfo.ManufacturerOUI"}'
ubus call bbfdm get '{"path": "Device.DeviceInfo.ProductClass"}'
ubus call bbfdm get '{"path": "Device.DeviceInfo.SerialNumber"}'

# Verify ConnectionRequestURL (must have IP address, not empty!)
ubus call bbfdm get '{"path": "Device.ManagementServer.ConnectionRequestURL"}'

# Check ACS for device registration (from testbed host)
curl -s http://localhost:7557/devices | python3 -m json.tool
# Or via GenieACS UI at http://localhost:3000
```

**CPE ID Format:**

The CPE ID in GenieACS is formatted as: `{OUI}-{ProductClass}-{SerialNumber}`

Example: `00E04C-RPi4prplOS-1000000045048244`

> **Note**: The CPE ID uses format `OUI-ProductClass-SerialNumber` to match what icwmpd
> reports to the ACS. ProductClass uses no special characters (`RPi4prplOS` not `RPi4-prplOS`)
> to avoid URL encoding issues in GenieACS device `_id`.

**Troubleshooting TR-069 Connection:**

1. **Check icwmpd logs:**
   ```bash
   logread | grep -i icwmp
   ```

2. **Common Issues:**
   
   - **Empty ConnectionRequestURL**: Verify `cwmp.cpe.interface` is set to actual device name (`eth1`), not netifd interface (`wan`)
   
   - **"failed to get value of Device.DeviceInfo.*"**: Device identity not configured in UCI. Set `cwmp.cpe.*` options and restart `sysmngr`
   
   - **CPE not appearing in ACS**: Check network connectivity to ACS, verify ACS URL is correct

3. **Verify network connectivity:**
   ```bash
   # From RPi, ping the ACS
   ping -c 2 172.25.1.40
   
   # Check WAN interface has IP
   ip addr show eth1
   ```

#### 4.2 Test TR-069 Operations

**Tasks:**
- [x] Test GetParameterValues
- [x] Test SetParameterValues
- [x] Test GetParameterNames
- [ ] Test Reboot RPC
- [ ] Test FactoryReset RPC (if needed)

**Test via ACS:**

```python
# Using Boardfarm ACS device
acs.GPV("Device.DeviceInfo.ModelName")
acs.SPV([("Device.IP.Interface.1.IPv4Address", "10.1.1.100")])
acs.Reboot(CommandKey="test-reboot")
```

**Test via ubus (local):**

```bash
# Get parameter values
ubus call bbfdm get '{"path": "Device.DeviceInfo."}'
ubus call bbfdm get '{"path": "Device.ManagementServer."}'

# Set parameter values
ubus call bbfdm set '{"path": "Device.ManagementServer.PeriodicInformInterval", "value": "600"}'
```

---

### Phase 5: Raikou Configuration (Day 5)

#### 5.1 Update Raikou Config

**File**: `boardfarm-bdd/raikou/config_prplos_rpi.json`

**Tasks:**
- [ ] Create new config file (or reuse `config_openwrt.json` structure)
- [ ] Configure `cpe-rtr` bridge with USB dongle
- [ ] Configure `lan-cpe` bridge with USB dongle
- [ ] Configure Router container with `cpe` interface
- [ ] Configure DHCP relay on Router

**Note**: Configuration is identical to OpenWrt setup since topology is the same.

#### 5.2 Update Docker Compose

**File**: `boardfarm-bdd/raikou/docker-compose-prplos-rpi.yaml`

**Tasks:**
- [ ] Create new compose file (or reuse `docker-compose-openwrt.yaml` structure)
- [ ] Configure Router with NAT on both `eth1` and `aux0`
- [ ] Configure Router DHCP relay
- [ ] Remove CPE container service (using physical RPi)

**Note**: Configuration is identical to OpenWrt setup.

#### 5.3 Router Container FRR Configuration

**Important**: The Router container uses FRR (Free Range Routing) for routing. The default route configuration is in `components/router/resources/staticd.conf`:

```
ip route 0.0.0.0/0 172.25.2.254
```

**Configuration Management**:

1. **After modifying FRR config files**, rebuild the Router container:
   ```bash
   cd ~/projects/req-tst/boardfarm-bdd/raikou
   docker compose -f docker-compose-openwrt.yaml build --no-cache router
   docker compose -f docker-compose-openwrt.yaml up -d router
   ```

2. **If Router loses internet access**, check for saved FRR configuration:
   ```bash
   # Check if saved config exists and contains incorrect routes
   docker exec router cat /etc/frr/frr.conf.sav | grep "ip route"
   
   # If incorrect route found (e.g., 8.8.8.8/32 via wrong gateway), remove saved config
   docker exec router rm -f /etc/frr/frr.conf.sav
   docker exec router service frr restart
   ```

3. **Saved configurations are preserved**: The init scripts do not automatically remove `/etc/frr/frr.conf.sav`. If someone manually saves a configuration (via `vtysh` → `write memory`), it will persist across container restarts. This is intentional - manual configurations are respected.

**Troubleshooting Router Internet Access**:

```bash
# Verify default route
docker exec router ip route show default
# Should show: default via 172.25.2.254 dev aux0

# Verify FRR routing table
docker exec router vtysh -c "show ip route" | grep "0.0.0.0/0"
# Should show: S>* 0.0.0.0/0 [1/0] via 172.25.2.254, aux0

# Test connectivity
docker exec router ping -c 2 172.25.2.254  # Host gateway
docker exec router ping -c 2 8.8.8.8       # Internet

# If failing, check for saved config with incorrect routes
docker exec router ls -la /etc/frr/frr.conf.sav
docker exec router cat /etc/frr/frr.conf.sav | grep -E "ip route|8.8.8.8"
```

---

### Phase 6: Testing and Validation (Day 6-7)

#### 6.1 Basic Connectivity Tests

**Tasks:**
- [ ] Verify WAN connectivity
- [ ] Verify LAN connectivity
- [ ] Verify internet connectivity
- [ ] Verify DHCP server on LAN
- [ ] Verify NAT functionality

#### 6.2 TR-069/ACS Tests

**Tasks:**
- [ ] Run existing ACS test scenarios
- [ ] Verify TR-069 parameter access
- [ ] Verify TR-069 RPC operations
- [ ] Verify ACS provisioning workflows

#### 6.3 Integration Tests

**Tasks:**
- [ ] Run existing BDD scenarios
- [ ] Verify device class integration
- [ ] Verify GUI testing (if applicable)
- [ ] Document any differences from containerized setup

---

## Build Requirements

### Hardware Requirements

- **Raspberry Pi 4** (4GB or 8GB RAM recommended)
- **SD Card** (32GB+ recommended, Class 10 or better)
- **USB-Ethernet Dongle** (for WAN interface)
- **USB-to-Serial Adapter** (for console access)
- **Power Supply** (official RPi4 power supply recommended)

### Software Requirements

- **prplOS Build System** (to be determined)
- **SD Card Flashing Tool** (e.g., `dd`, `balena-etcher`, `rpi-imager`)
- **Serial Console Access** (`picocom`, `screen`, or `minicom`)

### Network Requirements

- **USB-Ethernet Dongle** connected to host's `cpe-rtr` bridge
- **Native Ethernet** connected to host's `lan-cpe` bridge
- **Serial Console** access via USB-to-Serial adapter

---

## Device Class Architecture

### Class Hierarchy

```
CPE (Template)
├── CPEHW (Template)
│   └── RPiPrplOSHW
├── CPESwLibraries (Template)
│   └── RPiPrplOSSW
└── RPiPrplOSCPE (Main Class)
    ├── hw: RPiPrplOSHW
    └── sw: RPiPrplOSSW
```

### Key Differences from PrplDockerCPE

| Aspect | PrplDockerCPE | RPiPrplOSCPE |
|--------|---------------|--------------|
| Connection | `docker exec` | Serial console |
| Hardware | Container | Physical RPi4 |
| MAC Address | From config or container | From RPi hardware |
| Serial Number | From config or container | From RPi CPU info |
| Power Cycle | Container restart | Soft reboot via console |
| Network Access | Docker network | Physical interfaces |

### Key Similarities

- **TR-181 Data Model**: Same parameter structure
- **TR-069 Operations**: Same ACS client interface
- **Software Operations**: Same TR-181 parameter access methods
- **Containerized Apps**: Same container runtime support

---

## Success Criteria

### Phase 1 Complete ✅
- [x] prplOS image built for RPi4
- [x] RPi4 boots successfully with prplOS
- [x] Serial console access working
- [x] Network interfaces identified

### Phase 2 Complete ✅
- [x] WAN interface configured and gets IP (10.1.1.100+)
- [x] LAN interface configured as gateway (192.168.10.1)
- [x] Connectivity verified (Router, ISP services, Internet)
- [ ] DHCP server working on LAN (to be verified)

### Phase 3 Complete ✅
- [x] RPiPrplOSCPE device class implemented
- [x] Device class registered in Boardfarm
- [x] Boardfarm configuration created
- [x] Basic device operations working (connect, version, etc.)

### Phase 4 Complete ✅
- [x] TR-069 client configured and connected to ACS
- [x] ACS registration successful
- [x] TR-069 RPC operations working (via bbfdm)
- [ ] ACS provisioning workflows functional (testing in progress)

### Phase 5 Complete ✅
- [ ] Raikou configuration updated
- [ ] Docker Compose updated
- [ ] Network topology verified
- [ ] All containers running correctly

### Phase 6 Complete ✅
- [ ] All basic connectivity tests passing
- [ ] TR-069/ACS tests passing
- [ ] Integration tests passing
- [ ] Documentation complete

---

## Timeline Estimate

| Phase | Tasks | Estimated Time |
|-------|-------|---------------|
| Phase 1 | Build prplOS image, flash RPi4 | 1-2 days |
| Phase 2 | Network configuration | 1 day |
| Phase 3 | Device class implementation | 2-3 days |
| Phase 4 | TR-069/ACS integration | 1-2 days |
| Phase 5 | Raikou configuration | 1 day |
| Phase 6 | Testing and validation | 1-2 days |
| **Total** | | **7-11 days** |

---

## Notes

1. **Topology Reuse**: The corrected topology from OpenWrt implementation is reused. See [`openwrt_topology_correction_migration.md`](./openwrt_topology_correction_migration.md) for details.

2. **TR-069 Native Support**: prplOS includes native TR-069 client, eliminating the need for third-party clients (unlike OpenWrt which requires easycwmp).

3. **Containerized Applications**: prplOS supports containerized applications, providing extended functionality beyond basic gateway features.

4. **Device Class Reuse**: Can leverage patterns from both `PrplDockerCPE` (TR-181 operations) and `RPiRDKBCPE` (RPi hardware access).

5. **Serial Console Access**: LAN network (192.168.10.x) is isolated on `lan-cpe` bridge and not accessible from Docker host. Access to prplOS RPi is via serial console only.

6. **Internet Access**: Requires host NAT configuration (same as OpenWrt setup). Run `./enable_internet_access.sh eno1` after starting containers.

7. **FRR Configuration Management**: The Router container uses FRR (Free Range Routing) for routing. FRR can save its running configuration to `/etc/frr/frr.conf.sav`. If a saved configuration exists, FRR will load it on startup, which can override the intended configuration from `frr.conf` + `staticd.conf`. 
   
   **Key Points**:
   - **Saved configurations are intentional**: If someone manually saves a configuration (via `vtysh` → `write memory`), it's done for a specific reason and should be respected.
   - **Manual cleanup when needed**: If a saved configuration causes issues (e.g., incorrect routes), remove it manually: `docker exec router rm -f /etc/frr/frr.conf.sav`
   - **Rebuild containers after config changes**: When updating `staticd.conf` or other FRR configuration files, rebuild containers with `--no-cache` to ensure changes are picked up: `docker compose -f docker-compose-openwrt.yaml build --no-cache router`
   - **No automatic cleanup**: The init scripts do not automatically remove saved configurations - they respect user intent and allow manual configuration persistence.

   **Example Issue**: If Router container loses internet access, check for incorrect routes:
   ```bash
   # Check for problematic saved configuration
   docker exec router cat /etc/frr/frr.conf.sav | grep "8.8.8.8"
   
   # If incorrect route found, remove saved config
   docker exec router rm -f /etc/frr/frr.conf.sav
   
   # Restart FRR or container to reload from source files
   docker exec router service frr restart
   # Or rebuild container if source files were updated
   docker compose -f docker-compose-openwrt.yaml build --no-cache router
   docker compose -f docker-compose-openwrt.yaml up -d router
   ```

---

## References

- [OpenWrt Topology Correction Migration](./openwrt_topology_correction_migration.md) - Corrected network topology
- [Testbed Network Topology](./Testbed%20Network%20Topology.md) - Complete network architecture
- [Raikou Physical Interface Integration](./Raikou_Physical_Interface_Integration.md) - Physical device integration guide
- prplOS GitLab: https://gitlab.com/prpl-foundation/prplos/prplos
- Boardfarm Device Classes: `boardfarm/boardfarm3/devices/prplos_cpe.py`, `boardfarm/boardfarm3/devices/rpirdkb_cpe.py`

---

**Document End**

