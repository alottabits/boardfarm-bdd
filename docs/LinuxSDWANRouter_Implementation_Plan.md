# Linux SD-WAN Router Implementation Plan

**Date:** February 24, 2026
**Status:** Design Document
**Related:** `WAN_Edge_Appliance_testing.md`, `Traffic_Management_Components_Architecture.md`

---

## 1. Overview

This document defines the implementation plan for the **Linux SD-WAN Router**, which serves as the Device Under Test (DUT) for the initial phase of the WAN Edge Appliance testing framework.

### Purpose
1.  **Reference Implementation:** Acts as a "Digital Twin" for commercial SD-WAN appliances (Cisco, Fortinet, VMware), validating test logic before expensive hardware is involved.
2.  **Functional Validation:** Proves the testbed's ability to measure path steering, failover convergence, and QoS.
3.  **Portability:** Runs as a standard Docker container or VM, using standard Linux networking packages.

---

## 2. Architecture & Components

The Linux SD-WAN Router is built on a standard Linux base (Debian/Alpine) and uses **FRR (Free Range Routing)** for the control plane and standard **Linux Kernel Networking** for the data plane.

### 2.1 Software Stack

| Component | Software Package | Purpose |
| :--- | :--- | :--- |
| **OS** | Alpine Linux (latest) | Lightweight, secure base image. |
| **Routing** | FRRouting (FRR) 8.x+ | BGP/OSPF control plane, Nexthop Tracking (NHT). |
| **Data Plane** | Linux Kernel 5.15+ | Packet forwarding, Policy Based Routing (PBR). |
| **Management** | OpenSSH Server | Console access for Boardfarm. |
| **Telemetry** | `iproute2`, `procps` | Interface stats, routing table inspection. |
| **VPN (Future)** | StrongSwan | IPsec/IKEv2 for Overlay Encryption pillar. |
| **QoS (Future)** | `tc` + `htb` | Traffic shaping and prioritization. |

### 2.2 Interface Topology

The container/VM exposes three primary network interfaces:

*   **eth0 (Mgmt):** Management/Console access (Boardfarm SSH).
*   **eth1 (LAN):** Connected to LAN-side clients (South-bound).
*   **eth2 (WAN1):** Connected to WAN1 TrafficController (North-bound).
*   **eth3 (WAN2):** Connected to WAN2 TrafficController (North-bound).

---

## 3. Implementation Details

### 3.1 Docker Container Specification

**Dockerfile Strategy:**
*   Start from `frrouting/frr` official image or `alpine`.
*   Install `openssh`, `iproute2`, `tcpdump`, `iptables`, `net-tools`.
*   Configure SSH keys for passwordless access (Boardfarm requirement).
*   Enable IP forwarding (`net.ipv4.ip_forward=1`) via sysctl or entrypoint.

**Capabilities:**
The container requires elevated privileges to manipulate network stack:
*   `NET_ADMIN`: For `ip route`, `tc`, `iptables`.
*   `SYS_ADMIN`: Required for some FRR operations (sysctl).

### 3.2 FRR Configuration (Path Steering & Failover)

To simulate SD-WAN behavior (intelligent path selection), we use FRR's **Nexthop Groups** and **Policy Based Routing (PBR)**.

**Key Mechanism: Recursive Nexthop Resolution**
Instead of static routes, we use BGP or static nexthops with BFD (Bidirectional Forwarding Detection) to detect link failures sub-second.

**Example `frr.conf` snippet:**
```vtysh
!
interface eth2
 description WAN1 - Primary
 ip address 10.1.0.2/24
!
interface eth3
 description WAN2 - Backup
 ip address 10.2.0.2/24
!
! Health check via static route tracking or BFD
ip route 0.0.0.0/0 10.1.0.1 eth2 10
ip route 0.0.0.0/0 10.2.0.1 eth3 20
!
! PBR for application steering (Productivity -> WAN1)
access-list PBR_PROD seq 10 permit ip any 203.0.113.0/24
!
route-map SDWAN_POLICY permit 10
 match ip address PBR_PROD
 set ip next-hop 10.1.0.1
!
```

### 3.3 Driver Implementation (`LinuxSDWANRouter`)

This class implements the `WANEdgeDevice` template.

**Location:** `boardfarm3/devices/linux_sdwan_router.py`

#### Logical vs Physical Interface Names

All `WANEdgeDevice` methods that return interface identifiers must return the **logical label** (e.g. `"wan1"`, `"wan2"`) defined in the `wan_interfaces` inventory mapping — never the physical OS name (e.g. `"eth2"`). This ensures test code using `get_active_wan_interface()` is portable across DUT implementations.

The driver loads the mapping at initialisation and uses a reverse-lookup helper:

```python
class LinuxSDWANRouter(LinuxDevice, WANEdgeDevice):

    def __init__(self, config: dict, cmdline_args: Namespace) -> None:
        super().__init__(config, cmdline_args)
        # e.g. {"wan1": "eth2", "wan2": "eth3"} from inventory config
        self._wan_interfaces: dict[str, str] = config["wan_interfaces"]
        # Reversed: {"eth2": "wan1", "eth3": "wan2"} — used by all methods
        self._physical_to_logical: dict[str, str] = {
            v: k for k, v in self._wan_interfaces.items()
        }

    def _to_logical(self, physical: str) -> str:
        """Translate a physical interface name to its logical WAN label."""
        try:
            return self._physical_to_logical[physical]
        except KeyError as exc:
            raise KeyError(
                f"Physical interface {physical!r} not found in wan_interfaces "
                f"config {self._wan_interfaces}"
            ) from exc
```

#### Template Method Implementation Details

The `LinuxSDWANRouter` class translates abstract `WANEdgeDevice` methods into concrete Linux/FRR commands executed via SSH.

1.  **`get_active_wan_interface(flow_dst: str | None = None)`**
    *   **Goal:** Determine which **logical WAN label** handles traffic for a destination and return it.
    *   **Command:** `ip -o route get <dst_ip>` (uses a default destination such as `8.8.8.8` when `flow_dst` is `None`)
    *   **Parsing:** Regex match `dev\s+(\S+)` to extract the physical interface name.
    *   **Translation:** Call `self._to_logical(physical_name)` to convert to the logical label.
    *   **Example:**
        ```
        # OS output:
        10.1.0.1 via 10.1.0.1 dev eth2 src 10.1.0.2 uid 0
        # _to_logical("eth2") → "wan1"
        # Returns: "wan1"
        ```

2.  **`get_wan_path_metrics()`**
    *   **Goal:** Retrieve Latency, Jitter, and Loss for each WAN link, keyed by logical label.
    *   **Logic:**
        *   **Phase 1 (Basic):** Check interface carrier state via `ip -j link show`. Returns placeholder metrics (0ms latency) if Up.
        *   **Phase 2 (Active):** For each physical interface in `self._wan_interfaces.values()`, run `ping -c 5 -i 0.2 <gateway>` and parse:
            *   Latency = `rtt min/avg/max/mdev` avg field
            *   Loss = `packet loss` %
            *   Jitter = `mdev` (mean deviation)
    *   **Translation:** Convert each physical interface key using `self._to_logical()` before inserting into the result dict.
    *   **Return:** `dict[str, PathMetrics]` where key is the **logical label** (e.g. `"wan1"`).

3.  **`get_wan_interface_status()`**
    *   **Goal:** Return UP/DOWN/Degraded state keyed by logical label.
    *   **Command:** `ip -j link show`
    *   **Parsing:** Load JSON output. For each WAN interface (filter using `self._wan_interfaces.values()`):
        *   `operstate`: `"UP"` → `state="up"`
        *   `operstate`: `"DOWN"` → `state="down"`
    *   **Translation:** Convert each physical interface name using `self._to_logical()` before inserting into the result dict.
    *   **Return:** `dict[str, LinkStatus]` where key is the **logical label** (e.g. `"wan1"`).

4.  **`get_routing_table()`**
    *   **Goal:** Return current forwarding table.
    *   **Command:** `ip -j route show`
    *   **Parsing:** Map JSON fields to `RouteEntry`:
        *   `dst` -> `destination`
        *   `gateway` -> `gateway`
        *   `dev` -> `interface`
        *   `metric` -> `metric` (default 0 if missing)
    *   **Return:** `list[RouteEntry]`.

5.  **`apply_policy(policy)`**
    *   **Goal:** Apply PBR (Policy Based Routing) to steer traffic via FRR's control plane.
    *   **Why FRR vtysh, not kernel `ip rule`:** FRR is the active routing daemon and owns the kernel routing table. Writing kernel `ip rule` / `ip route` entries directly bypasses FRR and risks being overwritten by it. Configuring PBR through `vtysh` ensures FRR installs the corresponding kernel rules itself, keeping the control plane and forwarding plane consistent. This is also the correct structural analog for commercial DUTs, where `apply_policy()` targets the vendor's management interface (REST/NETCONF) rather than the device's kernel.
    *   **Mechanism:** FRR's PBR uses **route-maps** applied to a LAN ingress interface (`pbr-policy`). The driver translates the abstract policy dict into FRR route-map configuration and applies it via `vtysh`.
    *   **Commands (via `vtysh`):**
        ```vtysh
        configure terminal
        !
        ! 1. Define traffic match criteria
        ip access-list <policy_name> seq 10 permit ip any <dst_prefix>
        !
        ! 2. Define the steering action (next-hop is the physical WAN gateway IP)
        route-map <policy_name> permit 10
         match ip address <policy_name>
         set ip next-hop <wan_gateway_ip>
         exit
        !
        ! 3. Apply the policy to the LAN ingress interface
        interface <lan_interface>
         pbr-policy <policy_name>
         exit
        !
        exit
        ```
    *   **Clean up:** Before applying a new policy, remove any existing route-map and access-list with the same name via `vtysh`: `no route-map <name>` and `no ip access-list <name>`. This ensures determinism without leaving stale kernel rules.
    *   **Note:** The `wan_gateway_ip` for the `set ip next-hop` command is the physical gateway address on the WAN link (e.g. `10.1.0.1` for WAN1), derived from the `policy["via_wan"]` logical label via `self._wan_interfaces`.

6.  **`get_telemetry()`**
    *   **Goal:** Device health stats.
    *   **Commands:**
        *   **CPU:** Read `/proc/stat` or run `top -bn1`.
        *   **Memory:** Read `/proc/meminfo`.
        *   **Uptime:** Read `/proc/uptime`.
    *   **Return:** Dict with `cpu_load_percent`, `mem_used_percent`, `uptime_seconds`.

---

## 4. Integration Plan

### 4.1 Boardfarm Inventory

```json
"dut_router": {
  "type": "linux_sdwan_router",
  "connection_type": "ssh",
  "ipaddr": "172.20.0.10",
  "username": "root",
  "password": "password",
  "wan_interfaces": {
    "wan1": "eth2",
    "wan2": "eth3"
  }
}
```

> **`wan_interfaces` is a required field** for all `WANEdgeDevice` implementations. It maps logical labels (used by test code and use-case functions) to the physical OS interface names on that specific DUT. The driver builds a reverse map at `__init__` time and uses it in every method that returns an interface identifier. Without this key the driver will raise `KeyError` on first use.
>
> For commercial DUT implementations the same key is used with vendor-specific physical names, e.g.:
> ```json
> "wan_interfaces": {"wan1": "GigabitEthernet0/0/0", "wan2": "GigabitEthernet0/0/1"}
> ```

### 4.2 Development Phases

> See the [Component Readiness Map](WAN_Edge_Appliance_testing.md#component-readiness-map) in `WAN_Edge_Appliance_testing.md §5` for how these phases map to project-level gates.

1.  **Phase 1: Base Container** *(Project Phase 1 — Foundation)*
    *   Build Dockerfile with SSH + FRR.
    *   Verify manual `ip route` manipulation.
2.  **Phase 2: Driver Development** *(Project Phase 1 — Foundation)*
    *   Implement `LinuxSDWANRouter` class.
    *   Unit test `get_active_wan_interface` logic against mock outputs.
3.  **Phase 3: Integration** *(Project Phase 2 — Raikou Integration)*
    *   Deploy in Raikou (Dual WAN topology).
    *   Verify `WANEdgeDevice` template compliance.

---

## 5. VM Migration Note

This implementation plan is fully compatible with a VM-based deployment. To migrate:
1.  Provision a Linux VM (Ubuntu/Debian).
2.  Run the same `apt install` commands as the Dockerfile.
3.  Copy the `frr.conf`.
4.  Update Boardfarm inventory IP.
The `LinuxSDWANRouter` python driver requires **no changes**.
