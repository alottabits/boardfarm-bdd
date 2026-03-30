# Network Topology Reference: Raikou + Boardfarm Testbed

## Overview

The Raikou + Boardfarm testbed simulates a complete home gateway environment using containerized components. The testbed operates on two distinct network layers:

- **OVS Management Bridge** (`192.168.55.0/24`): All containers use `network_mode: none`; SSH access is provided via a dedicated OVS `mgmt` bridge managed by Raikou. See [Management Network Isolation](../../architecture/management-network-isolation.md).
- **Simulated Network** (`172.25.1.0/24`, `10.1.1.0/24`): The testbed topology created by Raikou using OVS bridges

## Network Architecture

### Customer Premises Equipment (CPE)

| Component | Description                           | Image        |
| --------- | ------------------------------------- | ------------ |
| **CPE**   | Home gateway device (PrplOS firmware) | `cpe:v1.2.0` |

### Infrastructure Services (ISP Simulation)

| Component      | Description                                                        | Image           |
| -------------- | ------------------------------------------------------------------ | --------------- |
| **Router**     | ISP edge gateway with FRR routing and NAT                          | `router:v1.2.0` |
| **WAN**        | Network services container (HTTP/TFTP/FTP/DNS/proxy/testing tools) | `wan:v1.2.0`    |
| **ACS**        | TR-069 management server                                           | `acs:v1.2.0`    |
| **DHCP**       | Network provisioning server                                        | `dhcp:v1.2.0`   |
| **SIP Center** | Voice services                                                     | `sip:v1.2.0`    |

### Client Devices

| Component       | Description                                                 | Image          |
| --------------- | ----------------------------------------------------------- | -------------- |
| **LAN**         | Test client device on LAN network (DHCP client, HTTP proxy) | `lan:v1.2.0`   |
| **LAN Phone**   | Phone device on LAN network (number 1000)                   | `phone:v1.2.0` |
| **WAN Phone**   | Phone device on WAN network (number 2000)                   | `phone:v1.2.0` |
| **WAN Phone 2** | Second phone device on WAN network (number 3000)            | `phone:v1.2.0` |

## Network Topology Diagrams

### OVS Management Bridge

All containers use `network_mode: none`. Management access is via the OVS `mgmt` bridge (`192.168.55.0/24`), not Docker port mappings.

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'fontSize': '12px', 'fontFamily': 'arial' }}}%%
flowchart LR
    MGMT[Boardfarm / Host<br/>192.168.55.1<br/>OVS mgmt bridge]

    WAN_MGMT[WAN eth0<br/>192.168.55.10]
    ROUTER_MGMT[Router eth0<br/>192.168.55.7]
    LAN_MGMT[LAN eth0<br/>192.168.55.8]
    DHCP_MGMT[DHCP eth0<br/>192.168.55.6]
    ACS_MGMT[ACS eth0<br/>192.168.55.11<br/>TR-069:7547 UI:3000]
    CPE_MGMT[CPE Container<br/>No mgmt interface<br/>docker exec only]
    SIP_MGMT[SIP Center eth0<br/>192.168.55.5]
    LAN_PHONE_MGMT[LAN Phone eth0<br/>192.168.55.12]
    WAN_PHONE_MGMT[WAN Phone eth0<br/>192.168.55.13]
    WAN_PHONE2_MGMT[WAN Phone 2 eth0<br/>192.168.55.14]

    MGMT -.->|SSH| WAN_MGMT
    MGMT -.->|SSH| ROUTER_MGMT
    MGMT -.->|SSH| LAN_MGMT
    MGMT -.->|SSH| DHCP_MGMT
    MGMT -.->|SSH| ACS_MGMT
    MGMT -.->|docker exec| CPE_MGMT
    MGMT -.->|SSH| SIP_MGMT
    MGMT -.->|SSH| LAN_PHONE_MGMT
    MGMT -.->|SSH| WAN_PHONE_MGMT
    MGMT -.->|SSH| WAN_PHONE2_MGMT

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
    %% 1. Infrastructure Nodes
    ROUTER[Router Container<br/>ISP Edge Gateway]
    WAN[WAN Container<br/>Network Services]
    ACS[ACS Container<br/>TR-069 Management]
    DHCP[DHCP Container<br/>Network Provisioning]
    SIP[SIP Center<br/>Voice Services]

    %% 2. CPE Nodes
    CPE[CPE Container<br/>PrplOS Firmware]

    %% 3. Client Nodes
    LAN[LAN Container<br/>Test Client Device]
    LAN_PHONE[LAN Phone]
    WAN_PHONE[WAN Phone]
    WAN_PHONE2[WAN Phone 2]

    %% 4. Bridge Nodes
    BRIDGE_CPE_RTR[cpe-rtr bridge]
    BRIDGE_LAN_CPE[lan-cpe bridge]
    BRIDGE_RTR_WAN[rtr-wan bridge]
    BRIDGE_RTR_UPLINK[rtr-uplink bridge]

    %% --- VISIBLE CONNECTIONS (Indices 0-12) ---
    CPE <-->|eth1| BRIDGE_CPE_RTR
    ROUTER <-->|cpe| BRIDGE_CPE_RTR
    CPE <-->|eth0| BRIDGE_LAN_CPE
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



    %% Tighter Styling
    %% font: Make text smaller (default is usually 16px)
    %% padding: Reduce internal whitespace (default is usually higher)
    classDef infra fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:black;
    classDef cpe fill:#fff9c4,stroke:#fbc02d,stroke-width:2px,color:black;
    classDef client fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:black;
    classDef bridge fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,color:black;

    %% Apply classes
    class WAN,ACS,DHCP,SIP,ROUTER infra
    class CPE cpe
    class LAN,LAN_PHONE,WAN_PHONE,WAN_PHONE2 client
    class BRIDGE_CPE_RTR,BRIDGE_LAN_CPE,BRIDGE_RTR_WAN,BRIDGE_RTR_UPLINK bridge
```

### CPE-Router Segment (`cpe-rtr` bridge)

| Component | Interface | IP Address           | Purpose          |
| --------- | --------- | -------------------- | ---------------- |
| CPE       | eth1      | `10.1.1.x/24` (DHCP) | WAN connectivity |
| Router    | cpe       | `10.1.1.1/24`        | Gateway          |

### LAN Segment (`lan-cpe` bridge)

| Component     | Interface | Connection            | Purpose                                      |
| ------------- | --------- | --------------------- | -------------------------------------------- |
| CPE           | eth0      | Connected to `br-lan` | LAN interface (gateway)                      |
| LAN Container | eth1      | Connected to `br-lan` | Test client device (DHCP client, HTTP proxy) |
| LAN Phone     | eth1      | Connected to `br-lan` | Client device (SIP phone)                    |

### WAN Segment (`rtr-wan` bridge)

| Component      | Interface | IP Address       | Purpose                                            |
| -------------- | --------- | ---------------- | -------------------------------------------------- |
| Router         | eth1      | `172.25.1.1/24`  | Gateway                                            |
| WAN Container  | eth1      | `172.25.1.2/24`  | Network services (HTTP/TFTP/FTP/DNS/proxy/testing) |
| WAN Phone      | eth1      | `172.25.1.3/24`  | Client device (number 2000)                        |
| WAN Phone 2    | eth1      | `172.25.1.4/24`  | Client device (number 3000)                        |
| SIP Center     | eth1      | `172.25.1.5/24`  | Voice services (registers 1000, 2000, 3000)        |
| DHCP Container | eth1      | `172.25.1.20/24` | Network provisioning                               |
| ACS Container  | eth1      | `172.25.1.40/24` | TR-069 management                                  |

### Uplink Segment (`rtr-uplink` bridge)

| Component | Interface | IP Address      | Purpose                          |
| --------- | --------- | --------------- | -------------------------------- |
| Router    | aux0      | `172.25.2.1/24` | External connectivity simulation |

## Container Specifications

### Container Access

All containers use `network_mode: none`. Management access is via the OVS `mgmt` bridge — no Docker port mappings.

| Container  | Management IP    | Services                            | Connection Method                    |
| ---------- | ---------------- | ----------------------------------- | ------------------------------------ |
| router     | `192.168.55.7`   | SSH                                 | `ssh root@192.168.55.7`             |
| wan        | `192.168.55.10`  | SSH, HTTP proxy (:8080)             | `ssh root@192.168.55.10`            |
| lan        | `192.168.55.8`   | SSH, HTTP proxy (:8080)             | `ssh root@192.168.55.8`             |
| dhcp       | `192.168.55.6`   | SSH                                 | `ssh root@192.168.55.6`             |
| acs        | `192.168.55.11`  | SSH, TR-069 (:7547), NBI (:7557), UI (:3000) | `ssh root@192.168.55.11`  |
| cpe        | —                | —                                   | `docker exec -it cpe ash`           |
| mongo      | `192.168.55.9`   | MongoDB (:27017)                    | —                                   |
| sipcenter  | `192.168.55.5`   | SSH, SIP (:5060)                    | `ssh root@192.168.55.5`             |
| lan-phone  | `192.168.55.12`  | SSH                                 | `ssh root@192.168.55.12` (num 1000) |
| wan-phone  | `192.168.55.13`  | SSH                                 | `ssh root@192.168.55.13` (num 2000) |
| wan-phone2 | `192.168.55.14`  | SSH                                 | `ssh root@192.168.55.14` (num 3000) |

**Default Credentials**: `root` / `bigfoot1`

**Note**: All containers use `network_mode: none`. The CPE container has no management bridge interface and is accessed via `docker exec`. It only has interfaces on the simulated network:

- `eth0`: Connected to `lan-cpe` bridge (LAN side, part of `br-lan` bridge inside container)
- `eth1`: Connected to `cpe-rtr` bridge (WAN side, gets IP via DHCP)

## ISP Gateway (Router) Configuration

### Interface Configuration

| Interface | Bridge         | IP Address        | Purpose                             |
| --------- | -------------- | ----------------- | ----------------------------------- |
| cpe       | cpe-rtr        | `10.1.1.1/24`     | CPE-facing (LAN side)               |
| eth1      | rtr-wan        | `172.25.1.1/24`   | WAN-facing (internet-facing)        |
| aux0      | rtr-uplink     | `172.25.2.1/24`   | Auxiliary uplink                    |
| eth0      | OVS mgmt bridge | `192.168.55.7/24` | Management (SSH access) |

### NAT Configuration

```yaml
environment:
    - ENABLE_NAT_ON=eth1
```

**NAT Interface**: `eth1` (WAN interface)  
**NAT Behavior**: Masquerades traffic from `10.1.1.0/24` as `172.25.1.1` when accessing WAN services

### Network Communication Flow

1. CPE (`10.1.1.x`) sends request to `172.25.1.2`
2. Router receives on `cpe` interface, routes to `eth1`
3. Router applies NAT (source: `10.1.1.x` → `172.25.1.1`)
4. WAN Container receives request, processes service
5. Router routes response back to CPE
6. CPE receives service response

## Boardfarm Integration

### Device Mapping

| Boardfarm Device | Container                        | Connection Method                   |
| ---------------- | -------------------------------- | ----------------------------------- |
| `bf_cpe`         | cpe                              | `docker exec -it cpe ash`           |
| `bf_wan`         | wan                              | SSH `192.168.55.10`                 |
| `bf_lan`         | lan                              | SSH `192.168.55.8`                  |
| `bf_acs`         | acs                              | SSH `192.168.55.11`                 |
| `bf_dhcp`        | dhcp                             | SSH `192.168.55.6`                  |
| `bf_phone`       | lan-phone, wan-phone, wan-phone2 | SSH `192.168.55.12`, `.13`, `.14`   |

### Boot Process

1. **Raikou**: Creates network topology and starts containers
2. **Boardfarm**: Connects to containers via Docker management network (SSH) or `docker exec` (CPE) and provisions devices
3. **CPE**: Obtains IP via DHCP on eth1 and registers with ACS
4. **Testing**: Network validation and service access

## Troubleshooting Reference

### Common Issues

#### CPE Cannot Reach WAN

**Checks:**

- CPE has IP on eth1 (`10.1.1.x/24`)
- Router NAT enabled on `eth1` interface
- Router has routes between `10.1.1.0/24` and `172.25.1.0/24`

**Verification:**

```bash
docker exec -it cpe ash -c "ping -c 3 10.1.1.1"    # Router gateway
docker exec -it cpe ash -c "ping -c 3 172.25.1.2"  # WAN container
docker exec -it router bash -c "ip route show"
```

#### Wrong IP Address for Testing

**Use**: `172.25.1.2` for WAN services (simulated network)  
**Do NOT use**: management bridge IPs (`192.168.55.x`) for service testing

#### NAT Not Working

**Check Configuration:**

- Verify `ENABLE_NAT_ON=eth1` in docker-compose.yaml
- Check iptables rules: `docker exec -it router bash -c "iptables -t nat -L"`

### Verification Commands

```bash
# Check CPE connectivity
docker exec -it cpe ash -c "ping -c 3 10.1.1.1"    # Router gateway
docker exec -it cpe ash -c "ping -c 3 172.25.1.2"  # WAN container

# Check router NAT
docker exec -it router bash -c "iptables -t nat -L"

# Check network topology
docker exec -it router bash -c "ip route show"

# Check container status
docker compose ps

# Check SSH service
./validate-ssh.sh
```

## Quick Reference Tables

### Network Addresses Summary

| Network           | Subnet            | Purpose                                                         |
| ----------------- | ----------------- | --------------------------------------------------------------- |
| OVS Management Bridge | `192.168.55.0/24` | Container SSH access (all containers use `network_mode: none`) |
| CPE-Router        | `10.1.1.0/24`     | CPE WAN connectivity                                            |
| WAN Services      | `172.25.1.0/24`   | Infrastructure services                                         |
| Uplink            | `172.25.2.0/24`   | External connectivity                                           |

### Service IP Addresses

| Service        | IP Address    | Ports                                    |
| -------------- | ------------- | ---------------------------------------- |
| Router Gateway | `172.25.1.1`  | -                                        |
| WAN Server     | `172.25.1.2`  | 80 (HTTP), 69 (TFTP), 21 (FTP), 53 (DNS) |
| WAN Phone      | `172.25.1.3`  | - (number 2000)                          |
| WAN Phone 2    | `172.25.1.4`  | - (number 3000)                          |
| SIP Server     | `172.25.1.5`  | 5060 (SIP)                               |
| DHCP Server    | `172.25.1.20` | 67, 547                                  |
| ACS Server     | `172.25.1.40` | 7547 (TR-069)                            |

### OVS Bridges

| Bridge     | Connected Components                                     | Purpose               |
| ---------- | -------------------------------------------------------- | --------------------- |
| cpe-rtr    | CPE eth1, Router cpe                                     | CPE WAN connectivity  |
| lan-cpe    | CPE eth0, LAN eth1, LAN Phone                            | Home network          |
| rtr-wan    | Router eth1, WAN, WAN Phone, WAN Phone 2, SIP, DHCP, ACS | WAN services          |
| rtr-uplink | Router aux0                                              | External connectivity |
