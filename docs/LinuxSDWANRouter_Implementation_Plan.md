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

> **SD-WAN Docker/Raikou deployment:** For the Raikou-based SD-WAN testbed, the device uses `network_mode: none` and Raikou-injected interfaces: `eth-lan`, `eth-wan1`, `eth-wan2` (no management interface). The `wan_interfaces` inventory maps logical labels to these names, e.g. `{"wan1": "eth-wan1", "wan2": "eth-wan2"}`. The topology above describes the VM/generic layout; see `SDWAN_Testbed_Configuration.md` for the Raikou-specific setup.

### 2.3 Boardfarm Boot Hooks

`LinuxSDWANRouter` implements `boardfarm_device_boot` and `boardfarm_device_boot_async` so Boardfarm can boot the device without `--skip-boot`. The boot sequence:

1. **Connect** — establish console via `docker exec` (or SSH).
2. **Power cycle** — for `local_cmd` / `docker_exec` only: run `reboot -f`, disconnect, retry connect until success or timeout.
3. **Wait for interfaces** — verify `eth-lan`, `eth-wan1`, `eth-wan2` via `ip -o link show`.

For containers, `restart: always` in docker-compose is required so the container restarts after `reboot`.

---

## 3. Implementation Details

### 3.1 Docker Container Specification

**Dockerfile Strategy:**
*   Start from `frrouting/frr` official image or `alpine`.
*   Install `openssh`, `iproute2`, `tcpdump`, `iptables`, `net-tools`.
*   Configure SSH keys for passwordless access (Boardfarm requirement).
*   Enable IP forwarding (`net.ipv4.ip_forward=1`) via sysctl or entrypoint.

**Container restart:** For `boardfarm_device_boot` (power cycle via `reboot -f`), the container must have `restart: always` in docker-compose so Docker restarts it after the reboot.

**Capabilities:**
The container requires elevated privileges to manipulate network stack:
*   `NET_ADMIN`: For `ip route`, `tc`, `iptables`.
*   `SYS_ADMIN`: Required for some FRR operations (sysctl).

### 3.2 FRR Configuration (Path Steering & Failover)

To simulate SD-WAN behaviour (intelligent path selection), the Linux Router uses FRR's **BFD echo mode** for sub-second failure detection combined with **metric-based static routes** for path selection, and **Policy Based Routing (PBR) via route-maps** for application steering.

#### 3.2.1 Failure Detection: BFD Single-Hop Echo Mode

**Mechanism:** FRR's `bfdd` daemon on the DUT sends BFD echo packets to each WAN gateway address (the TC container's south-facing IP). The TC container's Linux IP stack reflects these packets back without requiring a BFD daemon on the TC side — this is standard BFD echo mode behaviour (RFC 5880 §6.3). When the TC applies `netem loss 100%`, echo packets are dropped; after `detect-multiplier` consecutive misses the BFD session is declared down, FRR zebra's nexthop tracking marks the gateway unreachable, and the static route is automatically withdrawn.

**Timer configuration:**

| Parameter | Value | Effect |
| :--- | :--- | :--- |
| `echo-receive-interval` | 100 ms | How often DUT expects an echo back |
| `detect-multiplier` | 3 | Failures before session declared down |
| **Detection time** | **300 ms** | `100ms × 3` — comfortably within 1000ms SLO |
| `receive-interval` (control) | 1000 ms | Control packet rate (maintenance only in echo mode) |
| `transmit-interval` (control) | 1000 ms | Control packet rate (maintenance only in echo mode) |

> **Deviation from hardware SD-WAN appliances:** Commercial SD-WAN devices (FortiGate, VeloCloud, Cisco) use **SLA probe-based monitoring** — ICMP or HTTP probes directed at remote servers through the WAN path. BFD echo mode is used here for its implementation simplicity (zero changes to TC container, pure FRR configuration). Both mechanisms achieve sub-second detection of packet loss; the difference is an implementation detail hidden behind the `WANEdgeDevice` template. **Test case portability is maintained** — `measure_failover_convergence()` and `assert_path_steers_on_impairment()` call `get_active_wan_interface()` and have no knowledge of the detection mechanism.

**`/etc/frr/daemons` — enable `bfdd`:**

```bash
zebra=yes
staticd=yes
bfdd=yes       # required for BFD echo mode
```

**`frr.conf` — complete configuration (using SDWAN testbed IPs from `SDWAN_Testbed_Configuration.md`):**

```vtysh
!
! == Interfaces ==
!
interface eth-lan
 ip address 192.168.10.1/24
!
interface eth-wan1
 description WAN1 - Primary (MPLS/Fiber)
 ip address 10.10.1.1/30
!
interface eth-wan2
 description WAN2 - Backup (Internet/Cable)
 ip address 10.10.2.1/30
!
! == BFD: Echo mode for sub-second WAN failure detection ==
!
! Echo packets are sent to the WAN gateway MAC; the TC container's IP stack
! reflects them back without a BFD daemon. When netem drops packets, echoes
! fail after detect-multiplier attempts → nexthop declared unreachable →
! static route withdrawn automatically by FRR zebra NHT.
!
bfd
 !
 peer 10.10.1.2 local-address 10.10.1.1 interface eth-wan1
  receive-interval 1000
  transmit-interval 1000
  detect-multiplier 3
  echo-mode
  echo-receive-interval 100
 !
 peer 10.10.2.2 local-address 10.10.2.1 interface eth-wan2
  receive-interval 1000
  transmit-interval 1000
  detect-multiplier 3
  echo-mode
  echo-receive-interval 100
 !
!
! == Static routes — metric-based failover ==
!
! WAN1: primary (metric 10 — lower metric = preferred)
! Withdrawn automatically when BFD peer 10.10.1.2 goes down (FRR NHT)
ip route 0.0.0.0/0 10.10.1.2 10
!
! WAN2: backup (metric 20 — installed when WAN1 route is withdrawn)
ip route 0.0.0.0/0 10.10.2.2 20
!
! == PBR for application steering (see apply_policy() in §3.3) ==
!
! Example: steer video traffic (AF41 DSCP=34) via WAN2
! Applied dynamically via vtysh by LinuxSDWANRouter.apply_policy()
!
```

> **Phase alignment:** BFD echo mode is configured from **Phase 1 (Foundation)**. The sub-second failover SLO (`measure_failover_convergence() ≤ 1000ms`) is formally validated in **Phase 2 (Raikou Integration)**, once the full testbed topology with TC containers is available. See [Component Readiness Map](WAN_Edge_Appliance_testing.md#component-readiness-map).

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
    *   **Note:** The `wan_gateway_ip` for the `set ip next-hop` command is the physical gateway address on the WAN link (e.g. `10.10.1.2` for WAN1), derived from the `policy["action"]["prefer_wan"]` logical label via `self._wan_interfaces`. The policy dict follows the vendor-neutral format: `{"match": {...}, "action": {"prefer_wan": "wan2"}}`. See `WAN_Edge_Appliance_testing.md §3.8`.

6.  **`remove_policy(name)`**
    *   **Goal:** Remove a PBR policy by name for teardown.
    *   **Commands (via `vtysh`):**
        ```vtysh
        configure terminal
        !
        ! Remove pbr-policy from LAN interface (if applied)
        interface <lan_interface>
         no pbr-policy <name>
         exit
        !
        no route-map <name>
        no ip access-list <name>
        exit
        ```
    *   **Teardown:** Called by `reset_sdwan_testbed_after_scenario` for each policy in `bf_context["applied_policies"]`. See `WAN_Edge_Appliance_testing.md §3.9`.

7.  **`bring_wan_down(label)`**
    *   **Goal:** Bring a WAN interface down (simulate cable unplug).
    *   **Command:** `ip link set <physical_iface> down`
    *   **Translation:** Map logical label → physical interface via `self._wan_interfaces[label]`.
    *   **Teardown:** Interfaces brought down during a scenario are recorded in `bf_context["downed_interfaces"]`; `bring_wan_up(label)` is called for each during teardown. See `WAN_Edge_Appliance_testing.md §3.9`.

8.  **`bring_wan_up(label)`**
    *   **Goal:** Bring a WAN interface up (restore after bring_wan_down).
    *   **Command:** `ip link set <physical_iface> up`
    *   **Translation:** Map logical label → physical interface via `self._wan_interfaces[label]`.

9.  **`get_telemetry()`**
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
4.  **Phase 3.5: Digital Twin Hardening** *(Project Phase 3.5 — Optional)*
    *   Install StrongSwan; configure IKEv2 tunnel (see §3.4).
    *   Stand up testbed CA; distribute CA cert to Application Services and QoE Client.
    *   Verify IPsec tunnel establishment and ESP traffic on WAN link.

---

### 3.4 StrongSwan Configuration _(Phase 3.5 — Optional)_

> **Purpose:** Add IPsec/IKEv2 overlay encryption to the Linux Router, providing a functional analog to commercial SD-WAN appliances' VPN tunnel capability. A shared testbed CA is established as a side-effect and reused for TLS on application servers (enabling HTTPS/HTTP/3 in Phase 3.5 without a separate PKI setup).

**Container additions (`Dockerfile`):**

```dockerfile
RUN apt-get install -y strongswan strongswan-pki easy-rsa libcharon-extra-plugins
```

**Testbed CA setup (one-time, per testbed deployment):**

> See **[`Testbed_CA_Setup.md`](Testbed_CA_Setup.md)** for the complete, step-by-step procedure covering all certificate consumers (Nginx TLS, WebRTC WSS, StrongSwan IKEv2, Playwright trust store). The commands below are the DUT-specific subset extracted from that document.

```bash
# Run from the project root on the management host
cd testbed-ca
easyrsa gen-req dut-strongswan nopass
EASYRSA_SAN="DNS:dut.sdwan.testbed" easyrsa sign-req server dut-strongswan
# Outputs: pki/issued/dut-strongswan.crt, pki/private/dut-strongswan.key
```

Mount into the DUT container via `docker-compose.yaml` (see `Testbed_CA_Setup.md §6`):

```yaml
volumes:
    - ./testbed-ca/pki/ca.crt:/etc/strongswan/certs/ca.crt:ro
    - ./testbed-ca/pki/issued/dut-strongswan.crt:/etc/strongswan/certs/dut.crt:ro
    - ./testbed-ca/pki/private/dut-strongswan.key:/etc/strongswan/private/dut.key:ro
```

**`/etc/ipsec.conf` — IKEv2 tunnel to a stub peer:**

```ini
config setup
    charondebug="ike 1, knl 1, cfg 0"

conn sdwan-overlay
    keyexchange=ikev2
    left=%defaultroute
    leftid=@dut.testbed.local
    leftcert=dut-cert.pem
    leftsubnet=192.168.10.0/24        # LAN segment (from SDWAN_Testbed_Configuration.md)
    right=10.10.1.2                   # WAN1 TC container south-facing IP
    rightid=@tc-wan1.testbed.local
    rightsubnet=203.0.113.0/24        # North-side services segment
    auto=start
    ike=aes256-sha256-modp2048!
    esp=aes256-sha256!
    dpdaction=restart
    dpddelay=30s
```

**Verification:**

```bash
ipsec statusall                   # → shows ESTABLISHED + INSTALLED
ip xfrm policy                    # → shows inbound/outbound SPD entries
ping -c 3 203.0.113.10            # → LAN→North traffic via encrypted tunnel
```

> **Phase alignment:** StrongSwan is configured in **Phase 3.5 (Digital Twin Hardening)**. If Phase 3.5 is skipped, StrongSwan is added in **Phase 4 (Linux Router Expansion)** as part of the security pillar. The `WANEdgeDevice` template is not affected — VPN tunnel state is not currently exposed as a template method.

---

## 5. VM Migration Note

This implementation plan is fully compatible with a VM-based deployment. To migrate:
1.  Provision a Linux VM (Ubuntu/Debian).
2.  Run the same `apt install` commands as the Dockerfile.
3.  Copy the `frr.conf`.
4.  Update Boardfarm inventory IP.
The `LinuxSDWANRouter` python driver requires **no changes**.
