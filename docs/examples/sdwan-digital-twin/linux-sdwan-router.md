# Design: Linux SD-WAN Router (Digital Twin DUT)

| Field | Value |
| :--- | :--- |
| **Status** | Implemented |
| **Date** | 2026-03-20 |
| **Related** | [`architecture.md`](architecture.md), [`testbed-configuration.md`](testbed-configuration.md), [`adr/0001-scope-to-digital-twin-phase-3.5.md`](../../adr/0001-scope-to-digital-twin-phase-3.5.md) |

---

## 1. Context and Scope

The Linux SD-WAN Router is a Linux-based Device Under Test (Digital Twin) for the WAN Edge testing framework. It emulates a commercial SD-WAN appliance using commodity open-source packages — FRR for the control plane, the Linux kernel for the data plane, and StrongSwan for IPsec overlay encryption.

This DUT serves as the reference implementation. Test cases written against the `WANEdgeDevice` template run identically on this Digital Twin and on future commercial DUT drivers, because the template abstracts away vendor-specific mechanics. The project scope is fixed at Phase 3.5; see [ADR-0001](../../adr/0001-scope-to-digital-twin-phase-3.5.md) for rationale.

---

## 2. Non-Goals

The following capabilities are explicitly out of scope for this implementation:

- **DUT-side `tc` QoS shaping** — traffic shaping and prioritization on the DUT itself.
- **DUT-side `iptables` firewall rules** — stateful firewall policy enforcement on the DUT.
- **Commercial DUT vendor API drivers** — REST/NETCONF drivers for Cisco, Fortinet, VMware, or other vendor appliances.

See [ADR-0001](../../adr/0001-scope-to-digital-twin-phase-3.5.md) for the rationale behind scoping the project to the Digital Twin.

---

## 3. Architecture & Components

The Linux SD-WAN Router runs on a standard Linux base (Debian/Alpine) and uses **FRR (Free Range Routing)** for the control plane and standard **Linux Kernel Networking** for the data plane.

### 3.1 Software Stack

| Component | Software Package | Purpose |
| :--- | :--- | :--- |
| **OS** | Alpine Linux (latest) | Lightweight, secure base image. |
| **Routing** | FRRouting (FRR) 8.x+ | BGP/OSPF control plane, Nexthop Tracking (NHT). |
| **Data Plane** | Linux Kernel 5.15+ | Packet forwarding, Policy Based Routing (PBR). |
| **Management** | OpenSSH Server | Console access for Boardfarm. |
| **Telemetry** | `iproute2`, `procps` | Interface stats, routing table inspection. |
| **VPN** | StrongSwan | IPsec/IKEv2 overlay encryption. |

### 3.2 Interface Topology

The container/VM exposes three primary network interfaces:

*   **eth0 (Mgmt):** Management/Console access (Boardfarm SSH).
*   **eth1 (LAN):** Connected to LAN-side clients (South-bound).
*   **eth2 (WAN1):** Connected to WAN1 TrafficController (North-bound).
*   **eth3 (WAN2):** Connected to WAN2 TrafficController (North-bound).

> **SD-WAN Docker/Raikou deployment:** For the Raikou-based SD-WAN testbed, the device uses `network_mode: none` and Raikou-injected interfaces: `eth-lan`, `eth-wan1`, `eth-wan2` (no management interface). The `wan_interfaces` inventory maps logical labels to these names, e.g. `{"wan1": "eth-wan1", "wan2": "eth-wan2"}`. The topology above describes the VM/generic layout; see `testbed-configuration.md` for the Raikou-specific setup.

### 3.3 Boardfarm Boot Hooks

`LinuxSDWANRouter` implements `boardfarm_device_boot` and `boardfarm_device_boot_async` so Boardfarm can boot the device without `--skip-boot`. The boot sequence:

1. **Connect** — establish console via `docker exec` (or SSH).
2. **Power cycle** — for `local_cmd` / `docker_exec` only: run `reboot -f`, disconnect, retry connect until success or timeout.
3. **Wait for interfaces** — verify `eth-lan`, `eth-wan1`, `eth-wan2` via `ip -o link show`.

For containers, `restart: always` in docker-compose is required so the container restarts after `reboot`.

---

## 4. Implementation Details

### 4.1 Docker Container Specification

**Dockerfile strategy:**

*   Starts from `frrouting/frr` official image or `alpine`.
*   Installs `openssh`, `iproute2`, `tcpdump`, `iptables`, `net-tools`, `strongswan`, `strongswan-pki`, `easy-rsa`, `libcharon-extra-plugins`.
*   Configures SSH keys for passwordless access (Boardfarm requirement).
*   Enables IP forwarding (`net.ipv4.ip_forward=1`) via sysctl or entrypoint.

**Container restart:** For `boardfarm_device_boot` (power cycle via `reboot -f`), the container has `restart: always` in docker-compose so Docker restarts it after the reboot.

**Capabilities:**
The container requires elevated privileges to manipulate the network stack:

*   `NET_ADMIN`: For `ip route`, `tc`, `iptables`.
*   `SYS_ADMIN`: Required for some FRR operations (sysctl).

### 4.2 FRR Configuration (Path Steering & Failover)

The Linux Router uses FRR's **BFD echo mode** for sub-second failure detection, **metric-based static routes** for path selection, and **Policy Based Routing (PBR) via FRR pbr-maps** for application steering. Together these simulate the intelligent path selection behaviour of a commercial SD-WAN appliance.

#### 4.2.1 Failure Detection: BFD Single-Hop Echo Mode

FRR's `bfdd` daemon on the DUT sends BFD echo packets to each WAN gateway address (the TC container's south-facing IP). The TC container's Linux IP stack reflects these packets back without requiring a BFD daemon on the TC side — this is standard BFD echo mode behaviour (RFC 5880 §6.3). When the TC applies `netem loss 100%`, echo packets are dropped; after `detect-multiplier` consecutive misses the BFD session is declared down, FRR zebra's nexthop tracking marks the gateway unreachable, and the static route is automatically withdrawn.

**Timer configuration:**

| Parameter | Value | Effect |
| :--- | :--- | :--- |
| `echo-receive-interval` | 100 ms | How often DUT expects an echo back |
| `detect-multiplier` | 3 | Failures before session declared down |
| **Detection time** | **300 ms** | `100ms × 3` — within 1000 ms SLO |
| `receive-interval` (control) | 1000 ms | Control packet rate (maintenance only in echo mode) |
| `transmit-interval` (control) | 1000 ms | Control packet rate (maintenance only in echo mode) |

> **Deviation from hardware SD-WAN appliances:** Commercial SD-WAN devices (FortiGate, VeloCloud, Cisco) use SLA probe-based monitoring — ICMP or HTTP probes directed at remote servers through the WAN path. BFD echo mode is used here for its implementation simplicity (zero changes to TC container, pure FRR configuration). Both mechanisms achieve sub-second detection of packet loss; the difference is an implementation detail hidden behind the `WANEdgeDevice` template. Test case portability is maintained — `measure_failover_convergence()` and `assert_path_steers_on_impairment()` call `get_active_wan_interface()` and have no knowledge of the detection mechanism.

**`/etc/frr/daemons` — enable `bfdd`:**

```bash
zebra=yes
staticd=yes
bfdd=yes       # required for BFD echo mode
```

**`frr.conf` — complete configuration (using SDWAN testbed IPs from `testbed-configuration.md`):**

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
! == PBR for application steering (see apply_policy() in §4.3) ==
!
! Example: steer video traffic (AF41 DSCP=34) via WAN2
! Applied dynamically via vtysh by LinuxSDWANRouter.apply_policy()
!
```

### 4.3 Driver Implementation (`LinuxSDWANRouter`)

This class implements the `WANEdgeDevice` template.

**Location:** `boardfarm3/devices/linux_sdwan_router.py`

#### Logical vs Physical Interface Names

All `WANEdgeDevice` methods that return interface identifiers return the **logical label** (e.g. `"wan1"`, `"wan2"`) defined in the `wan_interfaces` inventory mapping — never the physical OS name (e.g. `"eth2"`). This ensures test code using `get_active_wan_interface()` is portable across DUT implementations.

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
    *   Determines which **logical WAN label** handles traffic for a destination.
    *   **Command:** `ip -o route get <dst_ip>` (uses a default destination such as `8.8.8.8` when `flow_dst` is `None`).
    *   **Parsing:** Regex match `dev\s+(\S+)` extracts the physical interface name.
    *   **Translation:** `self._to_logical(physical_name)` converts to the logical label.
    *   **Example:**
        ```
        # OS output:
        10.1.0.1 via 10.1.0.1 dev eth2 src 10.1.0.2 uid 0
        # _to_logical("eth2") → "wan1"
        # Returns: "wan1"
        ```

2.  **`get_wan_path_metrics()`**
    *   Retrieves latency, jitter, and loss for each WAN link, keyed by logical label.
    *   For each physical interface in `self._wan_interfaces.values()`, runs `ping -c 5 -i 0.2 <gateway>` using the configured `wan_gateways` and parses:
        *   Latency = `rtt min/avg/max/mdev` avg field
        *   Loss = `packet loss` %
        *   Jitter = `mdev` (mean deviation)
    *   Converts each physical interface key using `self._to_logical()` before inserting into the result dict.
    *   **Return:** `dict[str, PathMetrics]` where key is the **logical label** (e.g. `"wan1"`).

3.  **`get_wan_interface_status()`**
    *   Returns UP/DOWN/Degraded state keyed by logical label.
    *   **Command:** `ip -j link show`
    *   Loads JSON output. For each WAN interface (filtered using `self._wan_interfaces.values()`):
        *   `operstate`: `"UP"` → `state="up"`
        *   `operstate`: `"DOWN"` → `state="down"`
    *   Converts each physical interface name using `self._to_logical()` before inserting into the result dict.
    *   **Return:** `dict[str, LinkStatus]` where key is the **logical label** (e.g. `"wan1"`).

4.  **`get_routing_table()`**
    *   Returns the current forwarding table.
    *   **Command:** `ip -j route show`
    *   Maps JSON fields to `RouteEntry`:
        *   `dst` → `destination`
        *   `gateway` → `gateway`
        *   `dev` → `interface`
        *   `metric` → `metric` (default 0 if missing)
    *   **Return:** `list[RouteEntry]`.

5.  **`apply_policy(policy)`**
    *   Applies PBR (Policy Based Routing) to steer traffic via FRR's control plane.
    *   FRR is the active routing daemon and owns the kernel routing table. Writing kernel `ip rule` / `ip route` entries directly would bypass FRR and risk being overwritten. Configuring PBR through `vtysh` ensures FRR installs the corresponding kernel rules itself, keeping the control plane and forwarding plane consistent. This is also the correct structural analog for commercial DUTs, where `apply_policy()` targets the vendor's management interface (REST/NETCONF) rather than the device's kernel.
    *   FRR's PBR uses **pbr-maps** applied to a LAN ingress interface (`pbr-policy`). The driver translates the abstract policy dict into FRR pbr-map configuration and applies it via `vtysh`. The `name` field identifies the pbr-map (default: `"pbr-policy"`); `match.dst_prefix` specifies the destination prefix (default: `"0.0.0.0/0"` for all traffic); `action.prefer_wan` (required) is the logical WAN label resolved to a gateway IP via `wan_gateways`.
    *   **Commands (via `vtysh`):**
        ```vtysh
        configure terminal
        !
        ! 1. Clear any existing pbr-map with this name (idempotent re-application)
        no pbr-map <policy_name>
        !
        ! 2. Define the pbr-map with destination match and nexthop action
        pbr-map <policy_name> seq 10
         match dst-ip <dst_prefix>
         set nexthop <wan_gateway_ip>
         exit
        !
        ! 3. Apply (or re-apply) the pbr-policy to the LAN ingress interface
        interface <lan_interface>
         no pbr-policy
         pbr-policy <policy_name>
         exit
        !
        exit
        ```
    *   The `wan_gateway_ip` for `set nexthop` is the physical gateway address on the WAN link (e.g. `10.10.1.2` for WAN1), looked up from `self._wan_gateways[prefer_wan]`. The policy dict follows the vendor-neutral format: `{"name": "pbr-policy", "match": {"dst_prefix": "0.0.0.0/0"}, "action": {"prefer_wan": "wan2"}}`. See `architecture.md`.

6.  **`remove_policy(name)`**
    *   Removes a PBR policy by name for teardown.
    *   **Commands (via `vtysh`):**
        ```vtysh
        configure terminal
        !
        interface <lan_interface>
         no pbr-policy
         exit
        !
        no pbr-map <name>
        exit
        ```
    *   Called by `reset_sdwan_testbed_after_scenario` for each policy in `bf_context["applied_policies"]`.

7.  **`bring_wan_down(label)` / `bring_wan_up(label)`**
    *   Bring a WAN interface down or up (simulate cable unplug/restore).
    *   **Command:** `ip link set <physical_iface> down` / `up`
    *   Maps logical label → physical interface via `self._wan_interfaces[label]`.
    *   Interfaces brought down during a scenario are recorded in `bf_context["downed_interfaces"]`; `bring_wan_up(label)` is called for each during teardown.

8.  **`get_telemetry()`**
    *   Returns device health stats.
    *   **Commands:**
        *   **CPU:** Read `/proc/stat` or run `top -bn1`.
        *   **Memory:** Read `/proc/meminfo`.
        *   **Uptime:** Read `/proc/uptime`.
    *   **Return:** Dict with `cpu_load_percent`, `mem_used_percent`, `uptime_seconds`.

### 4.4 StrongSwan Configuration (IPsec Overlay Encryption)

StrongSwan provides IPsec/IKEv2 overlay encryption on the Linux Router, giving a functional analog to commercial SD-WAN appliances' VPN tunnel capability. A shared testbed CA is established as a side-effect and reused for TLS on application servers (enabling HTTPS/HTTP/3 without a separate PKI setup).

**Testbed CA setup (one-time, per testbed deployment):**

> See **[`testbed-ca-setup.md`](testbed-ca-setup.md)** for the complete procedure covering all certificate consumers (Nginx TLS, WebRTC WSS, StrongSwan IKEv2, Playwright trust store). The commands below are the DUT-specific subset.

```bash
# Run from the project root on the management host
cd testbed-ca
easyrsa gen-req dut-strongswan nopass
EASYRSA_SAN="DNS:dut.sdwan.testbed" easyrsa sign-req server dut-strongswan
# Outputs: pki/issued/dut-strongswan.crt, pki/private/dut-strongswan.key
```

Certificates are mounted into the DUT container via `docker-compose.yaml` (see `testbed-ca-setup.md §6`):

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
    leftsubnet=192.168.10.0/24        # LAN segment (from testbed-configuration.md)
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

The `WANEdgeDevice` template does not expose VPN tunnel state as a template method. StrongSwan operates as an infrastructure concern managed through the container configuration, not through the driver API.

---

## 5. Boardfarm Inventory Configuration

```json
"dut_router": {
  "type": "linux_sdwan_router",
  "connection_type": "docker_exec",
  "container_name": "linux-sdwan-router",
  "wan_interfaces": {
    "wan1": "eth-wan1",
    "wan2": "eth-wan2"
  },
  "wan_gateways": {
    "wan1": "10.10.1.2",
    "wan2": "10.10.2.2"
  },
  "lan_interface": "eth-lan"
}
```

> **`wan_interfaces` is a required field** for all `WANEdgeDevice` implementations. It maps logical labels (used by test code and use-case functions) to the physical OS interface names on that specific DUT. The driver builds a reverse map at `__init__` time and uses it in every method that returns an interface identifier. Without this key the driver raises `KeyError` on first use.
>
> For commercial DUT implementations the same key is used with vendor-specific physical names, e.g.:
> ```json
> "wan_interfaces": {"wan1": "GigabitEthernet0/0/0", "wan2": "GigabitEthernet0/0/1"}
> ```

> **`wan_gateways` is required** for `get_wan_path_metrics()` and `apply_policy()`. It maps each logical WAN label to the gateway IP on that WAN link — the address the DUT pings for latency/loss measurement and uses as the `set nexthop` target in pbr-maps. For `LinuxSDWANRouter` this is the TC container's south-facing IP (e.g. `10.10.1.2` for WAN1). If absent, a warning is logged and the two methods that depend on it do not work.

---

## 6. VM Migration Note

This design is fully compatible with a VM-based deployment. To migrate:

1.  Provision a Linux VM (Ubuntu/Debian).
2.  Run the same `apt install` commands as the Dockerfile.
3.  Copy the `frr.conf` and StrongSwan configuration.
4.  Update Boardfarm inventory IP.

The `LinuxSDWANRouter` Python driver requires no changes.
