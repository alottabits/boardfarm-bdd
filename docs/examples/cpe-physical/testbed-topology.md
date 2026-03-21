# Network Topology Reference: Physical RPi + Raikou Testbed

## Overview

The physical CPE testbed replaces the containerized CPE with a real Raspberry Pi
running prplOS. All other components (router, WAN, ACS, DHCP, SIP, phones) remain
dockerized and orchestrated by Raikou. The RPi connects to the Raikou OVS bridges
via two USB-Ethernet dongles on the host machine.

The testbed operates on two distinct network layers:

- **Docker Management Network** (`192.168.55.0/24`): Provides SSH access to containerized components
- **Serial Console**: The RPi is accessed via `picocom` over a USB serial connection (`/dev/ttyUSB0`)
- **Simulated Network** (`172.25.1.0/24`, `10.1.1.0/24`): The testbed topology created by Raikou using OVS bridges, with USB-Ethernet dongles bridging the physical RPi

## Network Architecture

### Customer Premises Equipment (CPE)

| Component | Description | Hardware |
| --------- | ---------------------------------- | ------------------------------------ |
| **RPi** | Physical home gateway (prplOS) | Raspberry Pi 4, USB-Ethernet dongles |

### Infrastructure Services (ISP Simulation)

| Component | Description | Image |
| -------------- | ------------------------------------------------------------------ | --------------- |
| **Router** | ISP edge gateway with FRR routing and NAT | `router:v1.2.0` |
| **WAN** | Network services container (HTTP/TFTP/FTP/DNS/proxy/testing tools) | `wan:v1.2.0` |
| **ACS** | TR-069 management server | `acs:v1.2.0` |
| **DHCP** | Network provisioning server | `dhcp:v1.2.0` |
| **SIP Center** | Voice services | `sip:v1.2.0` |

### Client Devices

| Component | Description | Image |
| --------------- | ----------------------------------------------------------- | -------------- |
| **LAN** | Test client device on LAN network (DHCP client, HTTP proxy) | `lan:v1.2.0` |
| **LAN Phone** | Phone device on LAN network (number 1000) | `phone:v1.2.0` |
| **WAN Phone** | Phone device on WAN network (number 2000) | `phone:v1.2.0` |
| **WAN Phone 2** | Second phone device on WAN network (number 3000) | `phone:v1.2.0` |

## Network Topology Diagrams

### Management Connectivity

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'fontSize': '12px', 'fontFamily': 'arial' }}}%%
flowchart LR
    MGMT[Boardfarm / Host<br/>192.168.55.1<br/>Management & Testing]

    WAN_MGMT[WAN Container eth0<br/>192.168.55.x<br/>SSH:4001 HTTP:8001]
    ROUTER_MGMT[Router Container eth0<br/>192.168.55.x<br/>SSH:4000]
    LAN_MGMT[LAN Container eth0<br/>192.168.55.x<br/>SSH:4002 HTTP:8002]
    DHCP_MGMT[DHCP Container eth0<br/>192.168.55.x<br/>SSH:4003]
    ACS_MGMT[ACS Container eth0<br/>192.168.55.x<br/>SSH:4503 TR-069:7547 UI:3000]
    CPE_MGMT[Raspberry Pi<br/>Serial Console<br/>picocom /dev/ttyUSB0]
    SIP_MGMT[SIP Center eth0<br/>192.168.55.x<br/>SSH:4005]
    LAN_PHONE_MGMT[LAN Phone eth0<br/>192.168.55.x<br/>SSH:4006]
    WAN_PHONE_MGMT[WAN Phone eth0<br/>192.168.55.x<br/>SSH:4007]
    WAN_PHONE2_MGMT[WAN Phone 2 eth0<br/>192.168.55.x<br/>SSH:4008]

    %% Management Connections
    MGMT -.->|SSH/Management| WAN_MGMT
    MGMT -.->|SSH/Management| ROUTER_MGMT
    MGMT -.->|SSH/Management| LAN_MGMT
    MGMT -.->|SSH/Management| DHCP_MGMT
    MGMT -.->|SSH/Management| ACS_MGMT
    MGMT -.->|serial console| CPE_MGMT
    MGMT -.->|SSH/Management| SIP_MGMT
    MGMT -.->|SSH/Management| LAN_PHONE_MGMT
    MGMT -.->|SSH/Management| WAN_PHONE_MGMT
    MGMT -.->|SSH/Management| WAN_PHONE2_MGMT

    classDef mgmt stroke-width:3px
    classDef management stroke-width:2px

    class MGMT mgmt
    class WAN_MGMT,ROUTER_MGMT,LAN_MGMT,DHCP_MGMT,ACS_MGMT,CPE_MGMT,SIP_MGMT,LAN_PHONE_MGMT,WAN_PHONE_MGMT,WAN_PHONE2_MGMT management
```

### Simulated Network Topology

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'fontSize': '12px', 'fontFamily': 'arial' }}}%%
graph LR
    %% --- NODES ---
    ROUTER[Router Container<br/>ISP Edge Gateway]
    WAN[WAN Container<br/>Network Services]
    ACS[ACS Container<br/>TR-069 Management]
    DHCP[DHCP Container<br/>Network Provisioning]
    SIP[SIP Center<br/>Voice Services]

    CPE[Raspberry Pi<br/>prplOS Firmware]

    LAN[LAN Container<br/>Test Client Device]
    LAN_PHONE[LAN Phone]
    WAN_PHONE[WAN Phone]
    WAN_PHONE2[WAN Phone 2]

    BRIDGE_CPE_RTR[cpe-rtr bridge<br/>+ USB dongle enx...7570]
    BRIDGE_LAN_CPE[lan-cpe bridge<br/>+ USB dongle enx...7b58]
    BRIDGE_RTR_WAN[rtr-wan bridge]
    BRIDGE_RTR_UPLINK[rtr-uplink bridge]

    %% --- CONNECTIONS ---
    CPE <-->|eth1 WAN| BRIDGE_CPE_RTR
    ROUTER <-->|cpe| BRIDGE_CPE_RTR
    CPE <-->|br-lan LAN| BRIDGE_LAN_CPE
    LAN <-->|eth1| BRIDGE_LAN_CPE
    LAN_PHONE <-->|eth1| BRIDGE_LAN_CPE
    ROUTER <-->|eth1| BRIDGE_RTR_WAN
    WAN <-->|eth1| BRIDGE_RTR_WAN
    ACS <-->|eth1| BRIDGE_RTR_WAN
    DHCP <-->|eth1| BRIDGE_RTR_WAN
    SIP <-->|eth1| BRIDGE_RTR_WAN
    WAN_PHONE <-->|eth1| BRIDGE_RTR_WAN
    WAN_PHONE2 <-->|eth1| BRIDGE_RTR_WAN
    ROUTER <-->|aux0| BRIDGE_RTR_UPLINK

    classDef infra fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:black;
    classDef cpe fill:#fff9c4,stroke:#fbc02d,stroke-width:2px,color:black;
    classDef client fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:black;
    classDef bridge fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,color:black;

    class WAN,ACS,DHCP,SIP,ROUTER infra
    class CPE cpe
    class LAN,LAN_PHONE,WAN_PHONE,WAN_PHONE2 client
    class BRIDGE_CPE_RTR,BRIDGE_LAN_CPE,BRIDGE_RTR_WAN,BRIDGE_RTR_UPLINK bridge
```

### CPE-Router Segment (`cpe-rtr` bridge)

| Component | Interface | IP Address | Purpose |
| --------------- | --------- | -------------------- | ---------------------------------- |
| RPi (prplOS) | eth1 | `10.1.1.x/24` (DHCP) | WAN connectivity |
| Router | cpe | `10.1.1.1/24` | Gateway |
| USB dongle | enx00e04c5b7570 | — | Bridges RPi WAN port into OVS |

### LAN Segment (`lan-cpe` bridge)

| Component | Interface | Connection | Purpose |
| ------------- | --------------- | --------------------- | -------------------------------------------- |
| RPi (prplOS) | br-lan | Physical LAN port | LAN interface (gateway) |
| USB dongle | enx00e04c327b58 | — | Bridges RPi LAN port into OVS |
| LAN Container | eth1 | Connected to `br-lan` | Test client device (DHCP client, HTTP proxy) |
| LAN Phone | eth1 | Connected to `br-lan` | Client device (SIP phone) |

### WAN Segment (`rtr-wan` bridge)

| Component | Interface | IP Address | Purpose |
| -------------- | --------- | ---------------- | -------------------------------------------------- |
| Router | eth1 | `172.25.1.1/24` | Gateway |
| WAN Container | eth1 | `172.25.1.2/24` | Network services (HTTP/TFTP/FTP/DNS/proxy/testing) |
| WAN Phone | eth1 | `172.25.1.3/24` | Client device (number 2000) |
| WAN Phone 2 | eth1 | `172.25.1.4/24` | Client device (number 3000) |
| SIP Center | eth1 | `172.25.1.5/24` | Voice services (registers 1000, 2000, 3000) |
| DHCP Container | eth1 | `172.25.1.20/24` | Network provisioning |
| ACS Container | eth1 | `172.25.1.40/24` | TR-069 management |

### Uplink Segment (`rtr-uplink` bridge)

| Component | Interface | IP Address | Purpose |
| --------- | --------- | --------------- | -------------------------------- |
| Router | aux0 | `172.25.2.1/24` | External connectivity simulation |

## Physical Connectivity

### USB-Ethernet Dongle Mapping

The physical RPi connects to the OVS topology via two USB-Ethernet dongles plugged
into the host machine. Raikou's `config_openwrt.json` adds these host interfaces
as parents of the OVS bridges:

| Host Interface | OVS Bridge | RPi Side | Network |
| ------------------- | ---------- | -------- | ------------ |
| `enx00e04c5b7570` | `cpe-rtr` | WAN port | `10.1.1.0/24` |
| `enx00e04c327b58` | `lan-cpe` | LAN port | DHCP from RPi |

### Serial Console

The RPi is accessed via a USB serial adapter at `/dev/ttyUSB0`:

```bash
picocom -b 115200 /dev/ttyUSB0
```

Boardfarm uses this connection (`connection_type: local_cmd`) to interact with
the prplOS shell during tests.

## Container Specifications

### Container Ports and Access

| Container | SSH Port | Other Ports | Connection Method |
| ---------- | -------- | ------------------------------------ | -------------------------------------------- |
| router | 4000 | - | `ssh -p 4000 root@localhost` |
| wan | 4001 | 8001 (HTTP) | `ssh -p 4001 root@localhost` |
| lan | 4002 | 8002 (HTTP) | `ssh -p 4002 root@localhost` |
| dhcp | 4003 | - | `ssh -p 4003 root@localhost` |
| acs | 4503 | 7547 (TR-069), 7557, 7567, 3000 (UI) | `ssh -p 4503 root@localhost` |
| RPi | - | - | `picocom -b 115200 /dev/ttyUSB0` (serial) |
| sipcenter | 4005 | 5060 (SIP) | `ssh -p 4005 root@localhost` |
| lan-phone | 4006 | - | `ssh -p 4006 root@localhost` (number 1000) |
| wan-phone | 4007 | - | `ssh -p 4007 root@localhost` (number 2000) |
| wan-phone2 | 4008 | - | `ssh -p 4008 root@localhost` (number 3000) |

**Default Credentials (containers)**: `root` / `bigfoot1`

## ISP Gateway (Router) Configuration

### Interface Configuration

| Interface | Bridge | IP Address | Purpose |
| --------- | -------------- | ----------------- | ----------------------------------- |
| cpe | cpe-rtr | `10.1.1.1/24` | CPE-facing (LAN side) |
| eth1 | rtr-wan | `172.25.1.1/24` | WAN-facing (internet-facing) |
| aux0 | rtr-uplink | `172.25.2.1/24` | Auxiliary uplink |
| eth0 | Docker network | `192.168.55.x/24` | Management (isolated) - Router only |

### NAT Configuration

```yaml
environment:
    - ENABLE_NAT_ON=eth1,aux0
```

**NAT Interfaces**: `eth1` (WAN) and `aux0` (uplink)
**NAT Behavior**: Masquerades traffic from `10.1.1.0/24` as `172.25.1.1` when accessing WAN services

### Network Communication Flow

1. RPi (`10.1.1.x`) sends request to `172.25.1.2`
2. Traffic exits the RPi WAN port → USB dongle → `cpe-rtr` OVS bridge
3. Router receives on `cpe` interface, routes to `eth1`
4. Router applies NAT (source: `10.1.1.x` → `172.25.1.1`)
5. WAN Container receives request, processes service
6. Router routes response back through `cpe-rtr` bridge → USB dongle → RPi

## Boardfarm Integration

### Device Mapping

| Boardfarm Device | Component | Connection Method |
| ------------------- | -------------------------------- | --------------------------------- |
| `bf_rpiprplos_cpe` | Raspberry Pi | `picocom -b 115200 /dev/ttyUSB0` |
| `bf_wan` | wan | SSH port 4001 |
| `bf_lan` | lan | SSH port 4002 |
| `bf_acs` | acs | SSH port 4503 |
| `bf_dhcp` | dhcp | SSH port 4003 |
| `bf_kamailio` | sipcenter | SSH port 4005 |
| `bf_phone` | lan-phone, wan-phone, wan-phone2 | SSH ports 4006, 4007, 4008 |

### Boot Process

1. **Raikou**: Creates OVS bridges and attaches USB-Ethernet dongles as bridge parents
2. **Boardfarm**: Connects to containers via SSH and to the RPi via serial console
3. **RPi**: Obtains IP via DHCP on eth1 (`10.1.1.x`) and registers with ACS (`172.25.1.40`)
4. **Testing**: Network validation and service access — same use cases as the dockerized CPE

## Troubleshooting Reference

### Common Issues

#### RPi Cannot Reach WAN

**Checks:**

- RPi has IP on eth1 (`10.1.1.x/24`)
- USB-Ethernet dongles are plugged in and recognized by the host (`ip link show | grep enx`)
- Raikou OVS bridges have the dongles as parents (`ovs-vsctl show`)
- Router NAT enabled on `eth1` interface

**Verification:**

```bash
# On the RPi (via serial console)
ping -c 3 10.1.1.1        # Router gateway
ping -c 3 172.25.1.2      # WAN container

# On the host
ovs-vsctl show             # Check bridge parents include USB dongles
docker exec -it router bash -c "ip route show"
```

#### USB-Ethernet Dongles Not Detected

```bash
# List USB devices
lsusb

# Check network interfaces
ip link show | grep enx

# Verify dongle names match config_openwrt.json
cat raikou/config_openwrt.json | grep enx
```

#### Serial Console Not Connecting

```bash
# Check USB serial device
ls -la /dev/ttyUSB*

# Verify no other process is using the port
fuser /dev/ttyUSB0

# Connect manually
picocom -b 115200 /dev/ttyUSB0
```

#### Wrong IP Address for Testing

**Use**: `172.25.1.2` for WAN services (simulated network)
**Do NOT use**: `192.168.55.x` (Docker management network)

### Verification Commands

```bash
# Check RPi connectivity (via serial console)
ping -c 3 10.1.1.1        # Router gateway
ping -c 3 172.25.1.2      # WAN container

# Check router NAT
docker exec -it router bash -c "iptables -t nat -L"

# Check OVS topology (USB dongles as bridge parents)
ovs-vsctl show

# Check container status
docker compose -f docker-compose-openwrt.yaml ps

# Check Kamailio is running
docker exec -it sipcenter service kamailio status
```

## Quick Reference Tables

### Network Addresses Summary

| Network | Subnet | Purpose |
| ----------------- | ----------------- | --------------------------------------------------- |
| Docker Management | `192.168.55.0/24` | Container SSH access (RPi uses serial console) |
| CPE-Router | `10.1.1.0/24` | RPi WAN connectivity (via USB dongle → OVS bridge) |
| WAN Services | `172.25.1.0/24` | Infrastructure services |
| Uplink | `172.25.2.0/24` | External connectivity |

### Service IP Addresses

| Service | IP Address | Ports |
| -------------- | ------------- | ----------------------------------------- |
| Router Gateway | `172.25.1.1` | - |
| WAN Server | `172.25.1.2` | 80 (HTTP), 69 (TFTP), 21 (FTP), 53 (DNS) |
| WAN Phone | `172.25.1.3` | - (number 2000) |
| WAN Phone 2 | `172.25.1.4` | - (number 3000) |
| SIP Server | `172.25.1.5` | 5060 (SIP) |
| DHCP Server | `172.25.1.20` | 67, 547 |
| ACS Server | `172.25.1.40` | 7547 (TR-069) |

### OVS Bridges

| Bridge | Connected Components | Purpose |
| ---------- | -------------------------------------------------------- | ----------------------------------- |
| cpe-rtr | RPi WAN (via USB dongle), Router cpe | RPi WAN connectivity |
| lan-cpe | RPi LAN (via USB dongle), LAN eth1, LAN Phone | Home network |
| rtr-wan | Router eth1, WAN, WAN Phone, WAN Phone 2, SIP, DHCP, ACS | WAN services |
| rtr-uplink | Router aux0 | External connectivity |
