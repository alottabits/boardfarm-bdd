# prplOS Console API for Boardfarm Device Class Development

> Reference documentation mapping prplOS console capabilities (UCI, ubus, system commands) to Boardfarm CPE template requirements.

## Purpose

This document provides the console API details needed to develop a Boardfarm CPE device class for prplOS-based devices. It maps each **Boardfarm template requirement** to the corresponding **prplOS console command** that fulfills it.

**Target Audience**: Developers implementing Boardfarm device classes for prplOS/OpenWrt-based CPE devices.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     Boardfarm CPE Template Requirements                  │
├─────────────────────────────────────────────────────────────────────────┤
│  CPE                                                                    │
│  ├── hw: CPEHW (Hardware abstraction)                                   │
│  │   ├── mac_address, serial_number, wan_iface                          │
│  │   ├── connect_to_consoles(), power_cycle(), wait_for_hw_boot()       │
│  │   └── get_console(), disconnect_from_consoles()                      │
│  └── sw: CPESW (Software operations)                                    │
│      ├── version, cpe_id, erouter_iface, lan_iface                      │
│      ├── is_online(), get_interface_ipv4addr(), get_seconds_uptime()    │
│      ├── reset(), factory_reset(), wait_for_boot()                      │
│      └── configure_management_server(), wait_for_acs_connection()       │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     prplOS Console API Layer                             │
├─────────────────────────────────────────────────────────────────────────┤
│  UCI Commands          │  ubus/bbfdm Commands    │  System Commands      │
│  ├── uci show          │  ├── ubus call bbfdm    │  ├── cat, grep, awk   │
│  ├── uci get           │  │   get/set            │  ├── ip, ifconfig     │
│  ├── uci set           │  └── ubus list          │  ├── reboot, ps       │
│  └── uci commit        │                         │  └── logread, free    │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Console Access

### Shell Prompt

```
root@prplOS:~#
```

**Regex Pattern**: `r"root@prplOS:.*#"`

### Command Execution

prplOS uses BusyBox ash shell. Commands are executed via the Boardfarm `execute_command()` method or `sendline()`/`expect()` for complex commands.

```python
# Simple command
output = console.execute_command("cat /etc/openwrt_version")

# Complex command with JSON (use sendline/expect to avoid escaping issues)
console.sendline('ubus call bbfdm get \'{"path": "Device.DeviceInfo."}\'')
console.expect(r"root@prplOS:.*#", timeout=10)
output = console.before
```

---

## Hardware Template (CPEHW) Requirements

### `mac_address` → System File Read

**Requirement**: Get CPE MAC address (typically WAN interface)

| prplOS Source | Command | Example Output |
|---------------|---------|----------------|
| eth1 interface | `cat /sys/class/net/eth1/address` | `00:e0:4c:1f:65:b8` |
| Environment file | `grep HWMACADDRESS /var/etc/environment` | `HWMACADDRESS="00:e0:4c:1f:65:b8"` |

```bash
# Primary: Read from interface directly
cat /sys/class/net/eth1/address

# Fallback: Read from prplOS environment (set by set-mac-address.sh)
grep HWMACADDRESS /var/etc/environment | tr -d '"' | cut -d= -f2
```

---

### `serial_number` → /proc/cpuinfo

**Requirement**: Get device serial number

| prplOS Source | Command | Example Output |
|---------------|---------|----------------|
| CPU info | `grep Serial /proc/cpuinfo \| awk '{print $3}'` | `1000000045048244` |

```bash
grep Serial /proc/cpuinfo | awk '{print $3}'
```

**Note**: This is RPi-specific. Other prplOS devices may use different sources.

---

### `wan_iface` → Static/UCI

**Requirement**: WAN interface name

| prplOS Value | Source |
|--------------|--------|
| `eth1` | USB-Ethernet dongle on RPi |

```bash
# Verify interface exists
ip link show eth1

# Get from UCI network config
uci get network.wan.device
```

---

### `power_cycle()` → reboot command

**Requirement**: Reboot the device

```bash
reboot
```

**Post-reboot**: Wait ~20 seconds, then reconnect to console.

---

### `wait_for_hw_boot()` → Interface IP check

**Requirement**: Wait for WAN interface to have IP address

```bash
# Check interface has IP
ip addr show dev eth1 | grep "inet "

# Alternative using ifconfig
ifconfig eth1 | grep "inet addr"
```

**Implementation**: Poll every 5 seconds until IP appears or timeout.

---

## Software Template (CPESW) Requirements

### `version` → Build version file

**Requirement**: Get firmware/software version

| prplOS Source | Command | Example Output |
|---------------|---------|----------------|
| Build version | `cat /etc/build.prplos.version` | `prplOS-4.0.3` |
| OpenWrt version | `cat /etc/openwrt_version` | `r0+25295-f0797dde19` |
| Release info | `cat /etc/openwrt_release` | Full release details |

```bash
# prplOS specific
cat /etc/build.prplos.version

# OpenWrt base version
cat /etc/openwrt_version
```

---

### `cpe_id` / `tr69_cpe_id` → Composite from multiple sources

**Requirement**: TR-069 CPE identifier in format `OUI-ProductClass-SerialNumber`

| Component | Source | Command | Example |
|-----------|--------|---------|---------|
| OUI | eth1 MAC (first 3 octets) | `cat /sys/class/net/eth1/address` | `00E04C` |
| ProductClass | Fixed or UCI | `uci get cwmp.cpe.product_class` | `RPi4prplOS` |
| SerialNumber | /proc/cpuinfo | `grep Serial /proc/cpuinfo` | `1000000045048244` |

```bash
# Get OUI from MAC (first 3 octets, no colons, uppercase)
MAC=$(cat /sys/class/net/eth1/address)
OUI=$(echo $MAC | cut -c1-8 | tr -d ':' | tr 'a-f' 'A-F')

# Get Serial
SERIAL=$(grep Serial /proc/cpuinfo | awk '{print $3}')

# Combine
echo "${OUI}-RPi4prplOS-${SERIAL}"
# Result: 00E04C-RPi4prplOS-1000000045048244
```

---

### `erouter_iface` / `lan_iface` / `guest_iface` → Static values

**Requirement**: Interface names

| Interface | prplOS Value | UCI Source |
|-----------|--------------|------------|
| erouter (WAN) | `eth1` | `uci get network.wan.device` |
| lan | `br-lan` | `uci get network.lan.device` |
| guest | `br-guest` | `uci get network.guest.device` |

```bash
# Verify bridge exists
ip link show br-lan
brctl show br-lan
```

---

### `is_online()` → Interface IP check

**Requirement**: Check if device has WAN connectivity

```bash
# Check WAN interface has IPv4
ifconfig eth1 | grep "inet addr"

# Or using ip command
ip addr show eth1 | grep "inet "

# IPv6 check
ip addr show eth1 | grep "inet6.*global"
```

---

### `get_interface_ipv4addr(interface)` → ifconfig/ip

**Requirement**: Get IPv4 address of interface

```bash
# Using ifconfig (BusyBox)
ifconfig eth1 | grep "inet addr" | awk -F: '{print $2}' | awk '{print $1}'

# Using ip command
ip -4 addr show eth1 | grep inet | awk '{print $2}' | cut -d/ -f1
```

---

### `get_interface_ipv6addr(interface)` → ifconfig/ip

**Requirement**: Get global IPv6 address of interface

```bash
# Global IPv6 address
ip -6 addr show eth1 | grep "inet6.*global" | awk '{print $2}' | cut -d/ -f1
```

---

### `get_interface_mac_addr(interface)` → sysfs

**Requirement**: Get MAC address of interface

```bash
cat /sys/class/net/eth1/address
```

---

### `is_link_up(interface)` → ip link

**Requirement**: Check if interface link is up

```bash
ip link show eth1 | grep "state UP"

# Or check for specific flags
ip link show eth1 | grep "BROADCAST,MULTICAST,UP"
```

---

### `get_seconds_uptime()` → /proc/uptime

**Requirement**: Get device uptime in seconds

```bash
cat /proc/uptime | awk '{print $1}'
# Output: 3847.23
```

---

### `get_load_avg()` → /proc/loadavg

**Requirement**: Get 1-minute load average

```bash
cat /proc/loadavg | cut -d' ' -f1
# Output: 0.42
```

---

### `get_memory_utilization()` → free command

**Requirement**: Get memory usage statistics

```bash
free -m
```

**Output format**:
```
              total        used        free      shared  buff/cache   available
Mem:           1024         256         512          32         128         768
```

---

### `read_event_logs()` → logread

**Requirement**: Get system logs

```bash
logread
```

**Filtered logs**:
```bash
# TR-069/icwmp logs
logread | grep -i icwmp

# Network logs
logread | grep -i network
```

---

### `get_running_processes()` → ps command

**Requirement**: List running processes

```bash
ps -A
# Or BusyBox variant
ps
```

---

### `reset()` → reboot

**Requirement**: Reboot device

```bash
reboot
```

---

### `factory_reset()` → firstboot or mtd

**Requirement**: Reset to factory defaults

```bash
# OpenWrt/prplOS factory reset
firstboot -y && reboot

# Alternative: Clear overlay partition
mtd -r erase rootfs_data
```

**Note**: Implementation depends on prplOS configuration.

---

### `get_file_content(fname)` → cat

**Requirement**: Read file contents

```bash
cat /path/to/file
```

---

### `get_date()` / `set_date()` → date command

**Requirement**: Get/set system date

```bash
# Get date
date '+%A, %B %d, %Y %T'

# Set date
date -s "2026-01-15 10:30:00"
```

---

### `kill_process_immediately(pid)` → kill

**Requirement**: Kill process by PID

```bash
kill -9 <pid>
```

---

### `get_interface_mtu_size(interface)` → ifconfig

**Requirement**: Get interface MTU

```bash
ifconfig eth1 | grep MTU | awk -F: '{print $2}' | awk '{print $1}'
```

---

## UCI Configuration API

UCI (Unified Configuration Interface) is the prplOS/OpenWrt configuration system.

### UCI Command Reference

| Operation | Command | Example |
|-----------|---------|---------|
| List all | `uci show` | Shows all configuration |
| Show section | `uci show <config>` | `uci show network` |
| Get value | `uci get <config>.<section>.<option>` | `uci get network.wan.device` |
| Set value | `uci set <config>.<section>.<option>=<value>` | `uci set cwmp.acs.url="http://..."` |
| Add list | `uci add_list <config>.<section>.<option>=<value>` | Add to list option |
| Delete | `uci delete <config>.<section>.<option>` | Remove option |
| Commit | `uci commit <config>` | Save changes |

### Key UCI Configurations for CPE

#### Network Configuration (`network`)

```bash
# WAN interface
uci show network.wan
# network.wan=interface
# network.wan.device='eth1'
# network.wan.proto='dhcp'

# LAN bridge
uci show network.lan
# network.lan=interface
# network.lan.device='br-lan'
# network.lan.proto='static'
# network.lan.ipaddr='192.168.10.1'
# network.lan.netmask='255.255.255.0'
```

#### TR-069 Configuration (`cwmp`)

```bash
# ACS settings
uci show cwmp.acs
# cwmp.acs.url='http://172.25.1.40:7547'
# cwmp.acs.periodic_inform_enable='1'
# cwmp.acs.periodic_inform_interval='300'

# Device identity (CRITICAL for TR-069)
uci show cwmp.cpe
# cwmp.cpe.manufacturer='prpl Foundation'
# cwmp.cpe.manufacturer_oui='00E04C'
# cwmp.cpe.product_class='RPi4prplOS'
# cwmp.cpe.serial_number='1000000045048244'
# cwmp.cpe.interface='eth1'  # MUST be device name, not netifd interface!
```

#### Firewall Configuration (`firewall`)

```bash
uci show firewall
```

### UCI Configuration for Device Class

**Setting up TR-069 device identity**:

```bash
# Configure device identity in cwmp.cpe section
uci set cwmp.cpe.manufacturer="prpl Foundation"
uci set cwmp.cpe.manufacturer_oui="00E04C"
uci set cwmp.cpe.product_class="RPi4prplOS"
uci set cwmp.cpe.serial_number="1000000045048244"
uci set cwmp.cpe.interface="eth1"
uci commit cwmp

# Restart sysmngr to reload identity
/etc/init.d/sysmngr restart
```

---

## ubus/bbfdm API (TR-181 Data Model)

The `bbfdm` (Broadband Forum Data Model) service provides TR-181 parameter access via ubus.

### ubus Command Reference

| Operation | Command |
|-----------|---------|
| List services | `ubus list` |
| List bbfdm methods | `ubus -v list bbfdm` |
| Get parameter | `ubus call bbfdm get '{"path": "<path>"}'` |
| Set parameter | `ubus call bbfdm set '{"path": "<path>", "value": "<value>"}'` |

### TR-181 Parameters for CPE Device Class

#### Device Information

| Parameter | Purpose | Command |
|-----------|---------|---------|
| `Device.DeviceInfo.Manufacturer` | Manufacturer name | `ubus call bbfdm get '{"path": "Device.DeviceInfo.Manufacturer"}'` |
| `Device.DeviceInfo.ManufacturerOUI` | OUI for CPE ID | `ubus call bbfdm get '{"path": "Device.DeviceInfo.ManufacturerOUI"}'` |
| `Device.DeviceInfo.ProductClass` | Product class | `ubus call bbfdm get '{"path": "Device.DeviceInfo.ProductClass"}'` |
| `Device.DeviceInfo.SerialNumber` | Serial number | `ubus call bbfdm get '{"path": "Device.DeviceInfo.SerialNumber"}'` |
| `Device.DeviceInfo.SoftwareVersion` | Firmware version | `ubus call bbfdm get '{"path": "Device.DeviceInfo.SoftwareVersion"}'` |
| `Device.DeviceInfo.UpTime` | Uptime in seconds | `ubus call bbfdm get '{"path": "Device.DeviceInfo.UpTime"}'` |

#### Management Server (TR-069)

| Parameter | Purpose | Command |
|-----------|---------|---------|
| `Device.ManagementServer.URL` | ACS URL | `ubus call bbfdm get '{"path": "Device.ManagementServer.URL"}'` |
| `Device.ManagementServer.ConnectionRequestURL` | CPE callback URL | `ubus call bbfdm get '{"path": "Device.ManagementServer.ConnectionRequestURL"}'` |
| `Device.ManagementServer.PeriodicInformEnable` | Enable periodic inform | `ubus call bbfdm set '{"path": "...", "value": "true"}'` |
| `Device.ManagementServer.PeriodicInformInterval` | Inform interval | `ubus call bbfdm set '{"path": "...", "value": "300"}'` |

#### Network Interfaces

| Parameter | Purpose | Command |
|-----------|---------|---------|
| `Device.IP.Interface.` | List IP interfaces | `ubus call bbfdm get '{"path": "Device.IP.Interface."}'` |
| `Device.Ethernet.Interface.` | List Ethernet interfaces | `ubus call bbfdm get '{"path": "Device.Ethernet.Interface."}'` |

### bbfdm Usage Examples

```bash
# Get all device info parameters
ubus call bbfdm get '{"path": "Device.DeviceInfo."}'

# Set ACS URL
ubus call bbfdm set '{"path": "Device.ManagementServer.URL", "value": "http://172.25.1.40:7547"}'

# Check if TR-181 is ready (use for wait_device_online)
ubus call bbfdm get '{"path": "Device.DeviceInfo.Manufacturer"}'
# If returns valid response, TR-181 is ready
# If returns "Command failed", services still starting
```

---

## Service Management

### Key prplOS Services

| Service | Purpose | Init Script |
|---------|---------|-------------|
| `icwmpd` | TR-069 CWMP client | `/etc/init.d/icwmpd` |
| `sysmngr` | Device info provider (dm_sysmngr) | `/etc/init.d/sysmngr` |
| `bbfdmd` | TR-181 data model daemon | `/etc/init.d/bbfdmd` |
| `uhttpd` | LuCI web server | `/etc/init.d/uhttpd` |
| `dnsmasq` | DHCP server | `/etc/init.d/dnsmasq` |
| `network` | Network management | `/etc/init.d/network` |

### Service Commands

```bash
# Start/stop/restart service
/etc/init.d/<service> start
/etc/init.d/<service> stop
/etc/init.d/<service> restart

# Enable/disable at boot
/etc/init.d/<service> enable
/etc/init.d/<service> disable

# Check if running
ps | grep <service>
```

### TR-069 Service Restart Sequence

When configuring TR-069, services must be restarted in order:

```bash
# 1. Configure UCI
uci set cwmp.cpe.manufacturer_oui="00E04C"
uci set cwmp.cpe.serial_number="1000000045048244"
uci set cwmp.cpe.interface="eth1"
uci commit cwmp

# 2. Restart sysmngr (provides Device.DeviceInfo.* to bbfdm)
/etc/init.d/sysmngr restart
sleep 3

# 3. Restart icwmpd (TR-069 client)
/etc/init.d/icwmpd restart
```

---

## Mapping Summary: Template → Console API

### CPEHW Template

| Template Method | prplOS Console API |
|-----------------|-------------------|
| `mac_address` | `cat /sys/class/net/eth1/address` |
| `serial_number` | `grep Serial /proc/cpuinfo \| awk '{print $3}'` |
| `wan_iface` | Static: `eth1` |
| `connect_to_consoles()` | Serial: picocom -b 115200 /dev/ttyUSB0 |
| `power_cycle()` | `reboot` |
| `wait_for_hw_boot()` | `ip addr show eth1 \| grep "inet "` (poll) |
| `get_console()` | Return BoardfarmPexpect instance |

### CPESW Template

| Template Method | prplOS Console API |
|-----------------|-------------------|
| `version` | `cat /etc/build.prplos.version` |
| `cpe_id` | Composite: OUI + ProductClass + Serial |
| `erouter_iface` | Static: `eth1` |
| `lan_iface` | Static: `br-lan` |
| `is_online()` | `ifconfig eth1 \| grep "inet addr"` |
| `get_interface_ipv4addr()` | `ifconfig <iface> \| grep "inet addr"` |
| `get_interface_ipv6addr()` | `ip -6 addr show <iface> \| grep global` |
| `get_interface_mac_addr()` | `cat /sys/class/net/<iface>/address` |
| `is_link_up()` | `ip link show <iface> \| grep "state UP"` |
| `get_seconds_uptime()` | `cat /proc/uptime \| awk '{print $1}'` |
| `get_load_avg()` | `cat /proc/loadavg \| cut -d' ' -f1` |
| `get_memory_utilization()` | `free -m` |
| `read_event_logs()` | `logread` |
| `get_running_processes()` | `ps -A` |
| `reset()` | `reboot` |
| `factory_reset()` | `firstboot -y && reboot` |
| `get_file_content()` | `cat <file>` |
| `get_date()` | `date '+%A, %B %d, %Y %T'` |
| `set_date()` | `date -s "<date>"` |
| `kill_process_immediately()` | `kill -9 <pid>` |
| `json_values` | `uci show` (parse all config) |
| `configure_management_server()` | UCI + ubus bbfdm set |
| `wait_for_acs_connection()` | Poll ACS API for device registration |

### TR-069 Specific

| Requirement | prplOS Console API |
|-------------|-------------------|
| Configure ACS URL | `ubus call bbfdm set '{"path": "Device.ManagementServer.URL", "value": "..."}'` |
| Set device identity | `uci set cwmp.cpe.<option>=<value>` + restart sysmngr |
| Check TR-181 ready | `ubus call bbfdm get '{"path": "Device.DeviceInfo.Manufacturer"}'` |
| Restart TR-069 | `/etc/init.d/icwmpd restart` |
| Get TR-069 logs | `logread \| grep -i icwmp` |

---

## Implementation Notes

### Critical Configuration Points

1. **`cwmp.cpe.interface` must be device name (`eth1`), not netifd interface (`wan`)**
   - icwmpd uses this to build ConnectionRequestURL
   - Wrong value = empty ConnectionRequestURL = ACS can't reach CPE

2. **Restart order matters: sysmngr → icwmpd**
   - sysmngr provides Device.DeviceInfo.* to bbfdm
   - icwmpd reads from bbfdm when sending Inform

3. **UCI commit is required before service restart**
   - Changes aren't applied until `uci commit`

4. **TR-181 readiness check before ACS configuration**
   - bbfdm may take 30-60 seconds to be ready after boot
   - Poll `ubus call bbfdm get` until it responds

### Error Handling

```python
# Check if TR-181 is ready
try:
    console.sendline('ubus call bbfdm get \'{"path":"Device.DeviceInfo.Manufacturer"}\'')
    console.expect(prompt, timeout=10)
    output = console.before
    if "Command failed" in output or "Not found" in output:
        return False  # TR-181 not ready
    return True
except pexpect.TIMEOUT:
    return False
```

---

## References

- **Device Class Implementation**: `boardfarm/boardfarm3/devices/rpiprplos_cpe.py`
- **CPE Templates**: `boardfarm/boardfarm3/templates/cpe/`
- **CPE Libraries**: `boardfarm/boardfarm3/lib/cpe_sw.py`
- **prplOS UCI Documentation**: https://openwrt.org/docs/guide-user/base-system/uci

---

**Document Version**: 1.1  
**Last Updated**: January 15, 2026  
**Purpose**: Developer reference for Boardfarm device class implementation
