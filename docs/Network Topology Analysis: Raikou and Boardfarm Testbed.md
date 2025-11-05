# Network Topology Analysis: Raikou + Boardfarm Testbed

## Executive Summary

This document captures the comprehensive analysis of the Raikou + Boardfarm testbed network topology, focusing on how the containerized home gateway components interact to enable firmware upgrades and realistic network simulation.

## Key Findings

### 1. **Home Gateway Architecture**
The complete home gateway functionality is represented by **three core containers**:
- **CPE Container**: The actual home gateway device (PrplOS firmware)
- **Router Container**: Network gateway with routing and NAT functionality  
- **LAN Container**: Local network services and home network simulation

### 2. **Network Interface Configuration Issue Resolved**
**Critical Discovery**: The router's NAT configuration was incorrectly set to `ENABLE_NAT_ON=eth0`, but the actual CPE interface was named `cpe`. 

**Initial Solution**: Changed to `ENABLE_NAT_ON=cpe` to enable NAT on the interface connecting to the CPE.

**Corrected Solution**: Should be `ENABLE_NAT_ON=eth1` to enable NAT on the WAN interface, which is the correct direction for masquerading traffic going out to the internet/WAN services.

### 3. **Dual Network Architecture**
The testbed operates on **two distinct network layers**:
- **Docker Management Network** (`192.168.56.0/24`): **ALL containers** have SSH access via port forwarding for Boardfarm configuration and management
- **Simulated Network** (`172.25.1.0/24`, `10.1.1.0/24`): The actual testbed topology created by Raikou

### 4. **Network Service Access**
The CPE accesses services on the **simulated network** (`172.25.1.2`), not the Docker management network (`192.168.56.6`).

## Network Topology Diagrams

### Docker Management Network

```mermaid
graph TB
    subgraph "Docker Management Network (192.168.56.0/24)"
        HOST[Host Machine<br/>192.168.56.1]
        
        subgraph "Container Management Interfaces"
            WAN_MGMT[WAN Container eth0<br/>192.168.56.6<br/>SSH:4001 HTTP:8001]
            ROUTER_MGMT[Router Container eth0<br/>192.168.56.8<br/>SSH:4000]
            LAN_MGMT[LAN Container eth0<br/>192.168.56.x<br/>SSH:4002 HTTP:8002]
            DHCP_MGMT[DHCP Container eth0<br/>192.168.56.x<br/>SSH:4003]
            ACS_MGMT[ACS Container eth0<br/>192.168.56.x<br/>SSH:4503 TR-069:7547 UI:3000]
            CPE_MGMT[CPE Container eth0<br/>192.168.56.x<br/>SSH:4004]
            SIP_MGMT[SIP Center eth0<br/>192.168.56.x<br/>SSH:4005]
            LAN_PHONE_MGMT[LAN Phone eth0<br/>192.168.56.x<br/>SSH:4006]
            WAN_PHONE_MGMT[WAN Phone eth0<br/>192.168.56.x<br/>SSH:4007]
        end
        
        subgraph "Boardfarm Access"
            BOARDFARM[Boardfarm Test Framework<br/>Configuration & Testing]
        end
    end
    
    %% Management Connections
    HOST -.->|SSH/Management| WAN_MGMT
    HOST -.->|SSH/Management| ROUTER_MGMT
    HOST -.->|SSH/Management| LAN_MGMT
    HOST -.->|SSH/Management| DHCP_MGMT
    HOST -.->|SSH/Management| ACS_MGMT
    HOST -.->|SSH/Management| CPE_MGMT
    HOST -.->|SSH/Management| SIP_MGMT
    HOST -.->|SSH/Management| LAN_PHONE_MGMT
    HOST -.->|SSH/Management| WAN_PHONE_MGMT
    
    BOARDFARM -.->|SSH/Config| WAN_MGMT
    BOARDFARM -.->|SSH/Config| ROUTER_MGMT
    BOARDFARM -.->|SSH/Config| LAN_MGMT
    BOARDFARM -.->|SSH/Config| DHCP_MGMT
    BOARDFARM -.->|SSH/Config| ACS_MGMT
    BOARDFARM -.->|docker exec| CPE_MGMT
    BOARDFARM -.->|SSH/Config| SIP_MGMT
    BOARDFARM -.->|SSH/Config| LAN_PHONE_MGMT
    BOARDFARM -.->|SSH/Config| WAN_PHONE_MGMT
    
    %% Styling
    classDef host fill:#fff3e0,stroke:#e65100,stroke-width:3px
    classDef management fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef boardfarm fill:#e8f5e8,stroke:#1b5e20,stroke-width:2px
    
    class HOST host
    class WAN_MGMT,ROUTER_MGMT,LAN_MGMT,DHCP_MGMT,ACS_MGMT,CPE_MGMT,SIP_MGMT,LAN_PHONE_MGMT,WAN_PHONE_MGMT management
    class BOARDFARM boardfarm
```

### Simulated Network Topology

```mermaid
graph TB
    subgraph "Raikou OVS Bridges"
        BRIDGE_CPE_RTR[cpe-rtr bridge]
        BRIDGE_LAN_CPE[lan-cpe bridge]
        BRIDGE_RTR_WAN[rtr-wan bridge]
        BRIDGE_RTR_UPLINK[rtr-uplink bridge]
    end
    
    subgraph "Home Gateway Components"
        CPE[CPE Container<br/>PrplOS Firmware<br/>eth1: 10.1.1.x/24 WAN<br/>eth0: Connected to br-lan LAN]
        ROUTER[Router Container<br/>FRR Routing + NAT<br/>cpe: 10.1.1.1/24<br/>eth1: 172.25.1.1/24<br/>aux0: 172.25.2.1/24]
        LAN[LAN Container<br/>Home Network Services<br/>eth1: Connected to br-lan]
    end
    
    subgraph "Infrastructure Services"
        WAN[WAN Container<br/>HTTP/TFTP Server<br/>eth1: 172.25.1.2/24<br/>Service Hosting]
        ACS[ACS Container<br/>TR-069 Management<br/>eth1: 172.25.1.40/24]
        DHCP[DHCP Container<br/>Network Provisioning<br/>eth1: 172.25.1.20/24]
        SIP[SIP Center<br/>Voice Services<br/>eth1: 172.25.1.5/24]
    end
    
    subgraph "Client Devices"
        LAN_PHONE[LAN Phone<br/>eth1: Connected to br-lan]
        WAN_PHONE[WAN Phone<br/>eth1: 172.25.1.3/24]
    end
    
    %% Raikou Bridge Connections
    CPE <-->|eth1| BRIDGE_CPE_RTR
    ROUTER <-->|cpe| BRIDGE_CPE_RTR
    
    CPE <-->|eth0| BRIDGE_LAN_CPE
    LAN <-->|eth1| BRIDGE_LAN_CPE
    LAN_PHONE <-->|eth1| LAN
    
    ROUTER <-->|eth1| BRIDGE_RTR_WAN
    WAN <-->|eth1| BRIDGE_RTR_WAN
    ACS <-->|eth1| BRIDGE_RTR_WAN
    DHCP <-->|eth1| BRIDGE_RTR_WAN
    SIP <-->|eth1| BRIDGE_RTR_WAN
    WAN_PHONE <-->|eth1| SIP
    
    ROUTER <-->|aux0| BRIDGE_RTR_UPLINK
    
    %% Styling
    classDef gateway fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef infrastructure fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef client fill:#e8f5e8,stroke:#1b5e20,stroke-width:2px
    classDef bridge fill:#fce4ec,stroke:#880e4f,stroke-width:2px
    
    class CPE,ROUTER,LAN gateway
    class WAN,ACS,DHCP,SIP infrastructure
    class LAN_PHONE,WAN_PHONE client
    class BRIDGE_CPE_RTR,BRIDGE_LAN_CPE,BRIDGE_RTR_WAN,BRIDGE_RTR_UPLINK bridge
```

## Detailed Network Analysis

### Network Segments

#### 1. **CPE-Router Segment** (`cpe-rtr` bridge)
- **CPE eth1**: `10.1.1.x/24` (DHCP assigned)
- **Router cpe**: `10.1.1.1/24` (Gateway)
- **Purpose**: WAN connectivity for CPE

#### 2. **LAN Segment** (`lan-cpe` bridge)
- **CPE eth0**: Connected to `br-lan` bridge
- **LAN Container**: Provides home network services
- **LAN Phone**: Connected to home network
- **Purpose**: Local network simulation

#### 3. **WAN Segment** (`rtr-wan` bridge)
- **Router eth1**: `172.25.1.1/24` (Gateway)
- **WAN Container**: `172.25.1.2/24` (Firmware server)
- **ACS**: `172.25.1.40/24` (TR-069 management)
- **DHCP**: `172.25.1.20/24` (Provisioning)
- **SIP Center**: `172.25.1.5/24` (Voice services)
- **Purpose**: Internet/cloud simulation

#### 4. **Uplink Segment** (`rtr-uplink` bridge)
- **Router aux0**: `172.25.2.1/24`
- **Purpose**: External connectivity simulation

### Network Communication Flow

1. **CPE** (`10.1.1.x`) sends network request to `172.25.1.2`
2. **Router** receives on `cpe` interface, routes to `eth1`
3. **Router** applies NAT (source: `10.1.1.x` → `172.25.1.1`)
4. **WAN Container** receives request, processes service
5. **Router** routes response back to CPE
6. **CPE** receives service response

### Critical Configuration Details

#### Router NAT Configuration
```yaml
environment:
    - ENABLE_NAT_ON=eth1  # ✅ Correct: NAT on WAN interface
    # NOT eth0 (Docker management) or cpe (LAN interface)
```

#### Interface Naming Convention
- **`cpe`**: Interface connecting to CPE (LAN side)
- **`eth1`**: Interface connecting to WAN services (internet-facing)
- **`aux0`**: Auxiliary uplink interface
- **`eth0`**: Docker management interface (not part of simulation)

#### NAT Interface Rationale
**Why `ENABLE_NAT_ON=eth1` is correct:**
- **Traffic Direction**: NAT masquerades traffic going OUT to the WAN/internet
- **Real-world Behavior**: Matches actual home gateway NAT configuration on WAN interface
- **Network Semantics**: `eth1` is the internet-facing side of the router
- **Traffic Flow**: CPE (`10.1.1.x`) → Router `cpe` → Router `eth1` → WAN (`172.25.1.2`)
- **NAT Purpose**: Masquerade private IPs (`10.1.1.x`) as router's WAN IP (`172.25.1.1`) when accessing internet services

#### Network Isolation
- **Docker Management** (`192.168.56.0/24`): **ALL containers** accessible via SSH for Boardfarm configuration, testing, and management
- **Simulated Network**: Complete testbed topology for realistic network behavior
- **No cross-communication** between management and simulated networks

## Troubleshooting Guide

### Common Issues

1. **CPE Cannot Reach WAN**
   - Check: CPE has IP on eth1 (`10.1.1.x/24`)
   - Check: Router NAT enabled on `eth1` interface
   - Check: Router has routes between `10.1.1.0/24` and `172.25.1.0/24`

2. **Wrong IP Address for Testing**
   - Use `172.25.1.2` for WAN services (simulated network)
   - NOT `192.168.56.6` (Docker management)

3. **NAT Not Working**
   - Verify `ENABLE_NAT_ON=eth1` (not `eth0` or `cpe`)
   - Check iptables rules: `iptables -t nat -L`

### Verification Commands

```bash
# Check CPE connectivity
docker exec -it cpe ash -c "ping -c 3 10.1.1.1"    # Router gateway
docker exec -it cpe ash -c "ping -c 3 172.25.1.2"  # WAN container

# Check router NAT
docker exec -it router bash -c "iptables -t nat -L"

# Check network topology
docker exec -it router bash -c "ip route show"
```

## Integration with Boardfarm

### Device Mapping
- **`bf_cpe`**: Maps to CPE container (via `docker exec`)
- **`bf_wan`**: Maps to WAN container (via SSH port 4001)
- **`bf_lan`**: Maps to LAN container (via SSH port 4002)
- **`bf_acs`**: Maps to ACS container (via SSH port 4503)
- **`bf_dhcp`**: Maps to DHCP container (via SSH port 4003)
- **`bf_phone`**: Maps to phone containers (via SSH ports 4006/4007)

### Boardfarm Connection Methods
- **CPE**: Uses `docker exec -it cpe ash` (direct container access)
- **All Other Devices**: Use SSH connections via Docker management network:
  - `localhost:4001` → WAN container
  - `localhost:4002` → LAN container  
  - `localhost:4003` → DHCP container
  - `localhost:4503` → ACS container
  - `localhost:4004` → CPE container
  - `localhost:4005` → SIP Center
  - `localhost:4006` → LAN Phone
  - `localhost:4007` → WAN Phone

### Boot Process
1. **Raikou**: Creates network topology and starts containers
2. **Boardfarm**: Connects to containers via Docker management network and provisions devices
3. **CPE**: Obtains IP via DHCP and registers with ACS
4. **Testing**: Network validation and service access

## Conclusion

The testbed successfully simulates a complete home gateway environment with:
- ✅ Realistic network topology using OVS bridges
- ✅ Proper NAT configuration for internet access simulation
- ✅ Complete network service access via HTTP/TFTP
- ✅ TR-069 management and provisioning
- ✅ Voice services and client device simulation

The key insight is understanding the **dual network architecture** where Docker management networks are separate from the simulated testbed topology, ensuring realistic network behavior for testing home gateway functionality.
