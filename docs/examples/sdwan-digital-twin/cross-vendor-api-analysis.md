# Cross-Vendor SD-WAN API Analysis

> **Purpose:** Evaluate the APIs of major SD-WAN platforms to derive a
> **harmonized** set of abstract methods for the `WANEdgeDevice` template —
> one that is portable across vendors yet aligned with real L7-capable
> appliances.
>
> **Date:** 2026-03-12

---

## 1. Vendors Evaluated

| Vendor | Product | API Reference |
|--------|---------|---------------|
| Cisco | Catalyst SD-WAN (vManage) | [DevNet — vManage REST API 20.18](https://developer.cisco.com/docs/sdwan/20-18) |
| Fortinet | FortiGate SD-WAN | [FortiOS 7.6 REST API](https://docs.fortinet.com/document/fortigate/7.6.4/administration-guide/584396/sd-wan-performance-sla) |
| VMware / Broadcom | VeloCloud SD-WAN | [Orchestrator API v2](https://developer.broadcom.com/xapis/vmware-sd-wan-orchestration-api-v2/latest/) |
| Palo Alto Networks | Prisma SD-WAN | [pan.dev SD-WAN APIs](https://pan.dev/sdwan/docs/) |
| Cisco | Meraki MX | [Dashboard API v1](https://developer.cisco.com/meraki/api-v1/) — local library at `meraki-dashboard-api/` |
| (Reference impl.) | LinuxSDWANRouter | FRR + Linux ip-route + iptables — `boardfarm3/devices/linux_sdwan_router.py` |

---

## 2. Capability Matrix

The table below maps each operational capability to the specific API
endpoint or mechanism exposed by each vendor.  Capabilities present in **all
five commercial platforms** are strong candidates for the harmonized
template.

### 2.1 Monitoring Capabilities

| Capability | Cisco Catalyst SD-WAN | Fortinet FortiGate | VMware VeloCloud | Palo Alto Prisma | Meraki MX | LinuxSDWAN |
|---|---|---|---|---|---|---|
| **WAN interface status** | `GET /device/interface/stats` | `GET /monitor/system/interface` | Edge health metrics | Interface API | `getOrganizationUplinksStatuses` | `ip link show` |
| **Path metrics: latency** | `/device/app-route/statistics` — per-tunnel latency | `sd-wan-sla-log` RTM — latency per health-check | Link metrics — `latencyMs` | Path quality profiles | Uplink loss/latency + VPN stats | ping probe |
| **Path metrics: jitter** | `/device/app-route/statistics` — per-tunnel jitter | `sd-wan-sla-log` RTM — jitter per health-check | Link metrics — `jitterMs` | Path quality — jitter sensitivity (low/med/high) | VPN stats only (not uplink API) | ping probe (computed) |
| **Path metrics: loss** | `/device/app-route/statistics` — per-tunnel loss | `sd-wan-sla-log` RTM — packet loss % | Link metrics — `lossPercent` | Path quality — loss % threshold | Uplink loss/latency + VPN stats | ping probe |
| **MOS (Mean Opinion Score)** | Not directly exposed | Not directly exposed | Link metrics — MOS score | Not directly exposed | VPN stats — MOS per peer | Not available |
| **Routing table** | `/device/ip/routetable`, `/device/bgp/routes` | `GET /router/policy` | Limited route visibility | Routing API | **Not available** | `ip route show` |
| **Device telemetry (CPU/mem)** | `/device/system/status` | `/system/resource/usage` | Edge health — CPU%, mem%, temp | System resources API | `getDeviceAppliancePerformance` (score only) | `/proc/stat`, `/proc/meminfo` |

### 2.2 Application-Layer (L7) Capabilities

| Capability | Cisco Catalyst SD-WAN | Fortinet FortiGate | VMware VeloCloud | Palo Alto Prisma | Meraki MX | LinuxSDWAN |
|---|---|---|---|---|---|---|
| **DPI / app identification** | `/device/dpi/applications` — NBAR2 engine | App control DB — FortiGuard categories | Application map — DPI classification | App-ID engine | L7 application categories | **None** |
| **Application flow visibility** | `/device/dpi/flows` — per-flow app data | App control logs + flow logs | Flow stats with app classification | App-ID flow logs | **Limited** (security events only) | **None** |
| **Application category taxonomy** | `/device/dpi/supported-applications` | FortiGuard app control DB | Application map endpoint | App-ID database | `getNetworkApplianceFirewallL7FirewallRulesApplicationCategories` | **None** |
| **App-aware traffic steering** | App-Route policy + SLA class via vSmart | SD-WAN rules with `internet-service-id` (app category match) | Business policy with app map | Path policy with App-ID match | `vpnTrafficUplinkPreferences` with `applicationCategory` filter | **None** (DSCP only) |
| **L7 firewall / app control** | UTD/Snort IPS policy | App control profile + IPS | DPI-based firewall rules | App-ID NGFW rules | L7 firewall rules (`meraki:layer7/application/X`) | **None** (iptables L3/L4 only) |
| **Content / URL filtering** | URL filtering policy | Web filter profile | URL category filtering | URL filtering profile | Content filtering rules | **None** |

### 2.3 Security Capabilities

| Capability | Cisco Catalyst SD-WAN | Fortinet FortiGate | VMware VeloCloud | Palo Alto Prisma | Meraki MX | LinuxSDWAN |
|---|---|---|---|---|---|---|
| **L3 firewall rules** | ACL policy | `firewall/policy` | Firewall rules | Security policy | L3 firewall rules | iptables |
| **Security event logs** | Security logs + UTD events | IPS/AV/web filter logs | Events API (alerts, security) | Threat logs | `getNetworkApplianceSecurityEvents` | iptables LOG |
| **IDS/IPS** | UTD with Snort signatures | FortiGuard IPS engine | IDS/IPS | Threat Prevention | `updateNetworkApplianceSecurityIntrusion` | **None** |
| **IPS mode** | off / IDS / IPS (feature template) | disable / monitor / block (IPS sensor) | off / detect / protect (edge setting) | off / alert / block (Threat Prevention profile) | `disabled` / `detection` / `prevention` | **None** |
| **IPS ruleset/sensitivity** | connectivity / balanced / security (signature set) | low / medium / high / critical (IPS filter) | detection profile level | best-practice / strict (profile) | `connectivity` / `balanced` / `security` | **None** |
| **Malware / AMP** | AMP feature template (on/off) | AV profile (enable/disable per policy) | **Limited** | WildFire integration (on/off) | `updateNetworkApplianceSecurityMalware` (`enabled`/`disabled`) | **None** |
| **Content / URL filtering** | URL filtering policy | Web filter profile (category + URL lists) | URL category filtering | URL filtering profile | Content filtering rules | **None** |
| **Syslog forwarding** | `logging` feature template (server, facility, severity) | `PUT /api/v2/cmdb/log.syslogd/setting` + filter | Edge/profile syslog export (server, port, categories) | Syslog server profile + log forwarding profile | `updateNetworkSyslogServers(servers=[{host, port, roles}])` | rsyslog remote forward (`/etc/rsyslog.d/`) |
| **Per-rule firewall logging** | Per-ACL logging action | `set logtraffic all\|utm\|disable` per policy | Per-rule log toggle | Log forwarding profile per rule | `syslogEnabled: true` per L3 rule | iptables `-j LOG` prefix |
| **Firewall rule read-back** | ACL / policy read-back | `GET /api/v2/cmdb/firewall/policy` | Orchestrator API firewall rules | `GET /sdwan/v2.0/api/securitypolicyrules` | `getNetworkApplianceFirewallL3FirewallRules` + `L7` | `iptables -S` parse |

### 2.4 Configuration & SLA

| Capability | Cisco Catalyst SD-WAN | Fortinet FortiGate | VMware VeloCloud | Palo Alto Prisma | Meraki MX | LinuxSDWAN |
|---|---|---|---|---|---|---|
| **SLA / performance class** | SLA-class list (latency, jitter, loss thresholds) | `performance-sla` health-check (latency, jitter, loss, probe type) | QoS profiles (bandwidth, latency, loss) | Path quality profiles (loss, jitter, latency) | Custom performance class (latency, jitter, loss) | Custom Python probe daemon |
| **SLA lifecycle** | Declarative — define = active | Declarative — define = active | Declarative — define = active | Declarative — define = active | Declarative — define = active | **Imperative — start/stop daemon** |
| **SLA probe interval** | Configurable per health-check | Configurable (`interval`, `failtime`) | Cloud-managed | Cloud-managed | Cloud-managed | Configurable |
| **Device reboot** | `/system/device/action/reboot` | `POST /system/reboot` | Edge action | Device action | `rebootDevice(serial)` | `reboot` via console |

### 2.5 VPN / Overlay

| Capability | Cisco Catalyst SD-WAN | Fortinet FortiGate | VMware VeloCloud | Palo Alto Prisma | Meraki MX | LinuxSDWAN |
|---|---|---|---|---|---|---|
| **VPN tunnel status** | BFD sessions + TLOC summary | IPsec tunnel monitor | VPN tunnel metrics | IPsec tunnel status | AutoVPN peer status (`getOrganizationApplianceVpnStatuses`) | N/A |
| **VPN tunnel metrics** | BFD latency/jitter/loss per tunnel | IPsec SA stats | Tunnel bandwidth/latency/loss | Tunnel metrics | VPN stats (latency, jitter, loss, MOS per peer) | N/A |
| **BGP** | Full BGP monitoring + config | BGP neighbor config + monitoring | BGP support | BGP config | BGP on hub (AutoVPN only) | FRR BGP |

---

## 3. Key Findings

### 3.1 Application-Layer Visibility Is Universal

Every commercial SD-WAN platform provides Deep Packet Inspection (DPI) and
application identification.  This is the defining characteristic that
distinguishes an SD-WAN appliance from a traditional router.

- **Cisco:** NBAR2 engine, `/device/dpi/applications`, `/device/dpi/flows`
- **Fortinet:** FortiGuard app control database, app control logs
- **VeloCloud:** Application map with DPI classification, flow stats
- **Prisma:** App-ID engine, flow logs
- **Meraki:** L7 application categories, application-based firewall rules

**Implication:** The `WANEdgeDevice` template **must** include methods for
querying application visibility.  The current template has none.

### 3.2 Application-Aware Steering Is the Norm

All commercial platforms steer traffic primarily by **application identity
or category**, not by DSCP marking.  DSCP-based PBR is the Linux router's
mechanism and is not the primary steering method on any commercial platform.

| Vendor | Primary steering match | Secondary matches |
|--------|----------------------|-------------------|
| Cisco Catalyst | App-Route policy (application + SLA class) | Prefix, DSCP |
| FortiGate | SD-WAN rules with `internet-service-id` (app category) | Prefix, protocol, DSCP |
| VeloCloud | Business policy with application map | Prefix, DSCP |
| Prisma | Path policy with App-ID | Prefix, protocol |
| Meraki | Uplink preferences with `applicationCategory` filter | CIDR, protocol, port |

**Implication:** The policy dict for `apply_policy()` must support
`application` and `application_category` as first-class match criteria.
DSCP remains as a fallback but should not be the primary mechanism.

### 3.3 SLA Monitoring Is Declarative

On all commercial platforms, SLA monitoring is **declarative**: you define
the performance thresholds and the platform immediately begins probing.
There is no explicit `start` / `stop` lifecycle.

| Vendor | Define SLA | Activate | Deactivate |
|--------|-----------|----------|------------|
| Cisco | Create SLA-class list | Immediately active when referenced by policy | Delete SLA-class |
| FortiGate | Define `performance-sla` health-check | Immediately active | Remove health-check |
| VeloCloud | Define QoS profile | Immediately active when assigned to edge/profile | Remove profile |
| Prisma | Create path-quality-profile | Immediately active when referenced by path policy | Delete profile |
| Meraki | Create custom performance class | Immediately active when bound to uplink preference | Delete class |

**Implication:** The `start_sla_monitoring()` / `stop_sla_monitoring()`
/ `apply_sla_monitoring()` methods are LinuxSDWANRouter-specific.  The
harmonized template should use a declarative model:
`configure_sla_policy()` activates monitoring, `remove_sla_policy()`
deactivates it.

### 3.4 Routing Table Access Is Not Universal

Meraki MX has no routing table API.  VeloCloud provides limited route
visibility.  The `get_routing_table()` method is too L3-centric for
the SD-WAN category.

**Implication:** Demote from abstract requirement to optional concrete
method with a default implementation returning an empty list.

### 3.5 Firewall Rules Are Distinct from Steering Policies

All vendors maintain a clear separation between:

- **Traffic steering policies** (which WAN link to use for a flow)
- **Firewall rules** (allow/deny/alert for a flow)

The current template conflates both under `apply_policy()`.  These should
be separate methods.

### 3.6 VPN/Overlay Status Is Universally Available

Every vendor exposes tunnel status and health metrics between sites.
For multi-site testbeds, this is essential.  However, not all testbed
configurations use multi-site VPN, so this should be optional (concrete
method with a default, not abstract).

### 3.7 Security Services Are Universal but Not Mandatory

All five commercial SD-WAN platforms offer IDS/IPS, malware protection,
and content/URL filtering.  However:

- **LinuxSDWANRouter** has none of these — it is a pure L3/L4 device.
- Not every testbed or test scenario requires security services.
- The configuration model varies significantly across vendors (e.g.
  FortiGate has per-policy security profiles; Meraki has network-level
  toggles; Cisco uses feature templates).

Despite the variation, the **test-relevant surface** is small and
consistent: enable/disable the service and choose a sensitivity level.
Fine-grained tuning (per-signature, per-policy) is a vendor-specific
concern that test automation rarely exercises.

| Service | Mode abstraction | Sensitivity abstraction | Commercially universal |
|---------|-----------------|------------------------|----------------------|
| **IPS** | disabled / detection / prevention | connectivity / balanced / security | 5/5 vendors |
| **Malware** | enabled / disabled | N/A (binary toggle) | 4/5 vendors (VeloCloud limited) |
| **Content filter** | enabled / disabled | category + URL lists | 5/5 vendors |

**Implication:** These belong as **concrete methods with no-op defaults**
(Option 3), following the same pattern as `get_routing_table()` and
`get_vpn_peer_status()`.  LinuxSDWANRouter inherits the defaults; vendors
with the capability override.

### 3.8 Syslog and Firewall Rule Read-Back Are Universally Supported

All six platforms provide mechanisms to:

1. **Configure a remote syslog destination** — server, port, and event
   categories to forward (e.g. firewall events, flows, IPS alerts).
2. **Enable per-rule firewall logging** — already handled by
   `FirewallRule.log` in the template.
3. **Read back active firewall rules** — essential for test verification
   ("is the rule I applied actually in effect?").

The test pattern "apply L3 firewall rule + enable syslog + verify rule
in logs" requires all three.  The `apply_firewall_rule` method and
`FirewallRule.log` field already cover items 1–2 on the rule side.
The gap is on the **infrastructure side** (configuring where syslog
messages go) and the **verification side** (reading back active rules).

| Capability | Commercial vendors | LinuxSDWAN |
|---|---|---|
| Syslog config | All 5 have API-driven syslog server config | rsyslog |
| Per-rule log | All 5 support per-rule logging toggle | iptables LOG |
| Rule read-back | All 5 expose current firewall rules via API | `iptables -S` |

**Implication:** Add `configure_syslog()`, `get_syslog_settings()`, and
`get_firewall_rules()` as **concrete methods with no-op / empty defaults**,
following the same pattern as the security service methods.

---

## 4. Harmonized Method Set

Based on the cross-vendor analysis, the following is the harmonized set
of methods for the `WANEdgeDevice` template.  Methods are categorized as:

- **Abstract** — must be implemented by every device class
- **Concrete with default** — has a sensible default; override when supported
- **Removed** — dropped from the template (implementations may still offer them)

### 4.1 Properties

| Method | Type | Rationale |
|--------|------|-----------|
| `nbi -> Any` | Abstract | All vendors have an orchestrator/API interface |
| `gui -> Any` | Abstract | All vendors have a web dashboard |
| `console -> BoardfarmPexpect \| None` | Abstract | API-only devices (Meraki) return `None` |

**Change:** `console` return type becomes `BoardfarmPexpect | None`.

### 4.2 Monitoring — Abstract

| Method | Signature | Rationale |
|--------|-----------|-----------|
| `get_active_wan_interface` | `(flow_dst: str \| None, via: str) -> str` | Universal — all vendors expose active uplink |
| `get_wan_path_metrics` | `(via: str) -> dict[str, PathMetrics]` | Universal — latency + loss everywhere; jitter on most |
| `get_wan_interface_status` | `(via: str) -> dict[str, LinkStatus]` | Universal — all vendors expose interface state |
| `get_link_health` | `(wan_label: str) -> LinkHealthReport` | Universal — all vendors expose link health relative to SLA |
| `get_telemetry` | `(via: str) -> dict` | Universal — all vendors expose device resource metrics |
| `get_security_log_events` | `(since_s: int) -> list[dict]` | Universal — all vendors have security event logs |

### 4.3 Monitoring — New Abstract (L7)

| Method | Signature | Rationale |
|--------|-----------|-----------|
| `get_application_categories` | `() -> list[dict]` | 5/5 commercial vendors expose their app taxonomy |
| `get_application_flows` | `(since_s: int, app_filter: str \| None) -> list[AppFlow]` | 5/5 commercial vendors expose DPI flow data |

**LinuxSDWANRouter** (no DPI) returns `[]` from both.

### 4.4 Monitoring — Concrete with Default (Optional)

| Method | Signature | Default | Rationale |
|--------|-----------|---------|-----------|
| `get_routing_table` | `(via: str) -> list[RouteEntry]` | `return []` | Not available on Meraki; limited on VeloCloud |
| `get_vpn_peer_status` | `() -> list[VPNPeerStatus]` | `return []` | Only relevant for multi-site testbeds |
| `get_traffic_shaping_rules` | `() -> list[TrafficShapingRule]` | `return []` | Read-back for DSCP marking / QoS rules applied via `apply_policy()` |
| `get_firewall_rules` | `() -> list[FirewallRule]` | `return []` | Read-back for rules applied via `apply_firewall_rule()` (see §3.8) |

### 4.5 Configuration — Abstract

| Method | Signature | Rationale |
|--------|-----------|-----------|
| `apply_policy` | `(policy: dict, via: str) -> None` | Universal — all vendors support traffic steering policies |
| `remove_policy` | `(name: str, via: str) -> None` | Universal — teardown requirement |
| `configure_sla_policy` | `(policy: SLAPolicy) -> None` | Universal — declarative: define = activate |
| `remove_sla_policy` | `(name: str) -> None` | Universal — teardown counterpart (NEW) |
| `apply_firewall_rule` | `(rule: FirewallRule, via: str) -> None` | Universal — all vendors have firewall config (NEW) |
| `remove_firewall_rule` | `(name: str, via: str) -> None` | Universal — teardown counterpart (NEW) |

### 4.6 Security Services — Concrete with Default (Optional)

| Method | Signature | Default | Rationale |
|--------|-----------|---------|-----------|
| `configure_ips` | `(mode: str, ruleset: str) -> None` | no-op | 5/5 commercial vendors; LinuxSDWAN has none (see §3.7) |
| `get_ips_settings` | `() -> dict` | `return {}` | Read back current IPS config |
| `configure_malware_protection` | `(enabled: bool) -> None` | no-op | 4/5 commercial vendors; binary toggle |
| `get_malware_settings` | `() -> dict` | `return {}` | Read back current malware config |
| `configure_content_filter` | `(enabled, blocked_categories, allowed_urls, blocked_urls) -> None` | no-op | 5/5 commercial vendors |
| `get_content_filter_settings` | `() -> dict` | `return {}` | Read back current content filter config |

**Vendor-neutral mode vocabulary:**

| Service | Values | Mapping |
|---------|--------|---------|
| IPS `mode` | `"disabled"`, `"detection"`, `"prevention"` | See §3.7 for per-vendor mapping |
| IPS `ruleset` | `"connectivity"`, `"balanced"`, `"security"` | Permissive → strict sensitivity |
| Malware `enabled` | `True` / `False` | Binary toggle |
| Content filter `enabled` | `True` / `False` | Binary toggle + category/URL lists |

### 4.7 Logging / Syslog — Concrete with Default (Optional)

| Method | Signature | Default | Rationale |
|--------|-----------|---------|-----------|
| `configure_syslog` | `(server: str, port: int, roles: list[str] \| None) -> None` | no-op | All commercial vendors + Linux (rsyslog) support remote syslog (see §3.8) |
| `get_syslog_settings` | `() -> dict` | `return {}` | Read back current syslog server config |

**Vendor-neutral role vocabulary:**

| Role | Meraki | Cisco Catalyst | FortiGate | VeloCloud | Prisma | Linux |
|------|--------|---------------|-----------|-----------|--------|-------|
| `"firewall"` | `"Firewall"` | ACL logging | Per-policy logtraffic | Firewall events | Security rule log | iptables LOG |
| `"flows"` | `"Flows"` | Flow export | Flow/session log | Flow stats | — | conntrack |
| `"security"` | `"Security events"` | UTD events | UTM log | Security events | Threat logs | — |
| `"urls"` | `"URLs"` | URL filter log | Web filter log | URL events | URL filter log | — |
| `"event_log"` | `"Appliance event log"` | System log | System event log | Edge events | System events | syslog |

### 4.8 Interface Control — Abstract

| Method | Signature | Rationale |
|--------|-----------|-----------|
| `bring_wan_down` | `(label: str, via: str) -> None` | Universal |
| `bring_wan_up` | `(label: str, via: str) -> None` | Universal |
| `power_cycle` | `() -> None` | Universal |

### 4.9 Removed Methods

| Method | Reason |
|--------|--------|
| `start_sla_monitoring()` | LinuxSDWANRouter-specific lifecycle; commercial platforms are declarative |
| `stop_sla_monitoring()` | Same as above |
| `apply_sla_monitoring(wan_label, policy_name)` | Binding is expressed through the policy dict in `apply_policy()` |

### 4.10 Summary of Changes

| Change | Method | Action |
|--------|--------|--------|
| NEW | `get_application_categories()` | Add as abstract |
| NEW | `get_application_flows()` | Add as abstract |
| NEW | `get_vpn_peer_status()` | Add as concrete with default |
| NEW | `remove_sla_policy()` | Add as abstract |
| NEW | `apply_firewall_rule()` | Add as abstract |
| NEW | `remove_firewall_rule()` | Add as abstract |
| NEW | `configure_ips()` | Add as concrete with no-op default |
| NEW | `get_ips_settings()` | Add as concrete returning `{}` |
| NEW | `configure_malware_protection()` | Add as concrete with no-op default |
| NEW | `get_malware_settings()` | Add as concrete returning `{}` |
| NEW | `configure_content_filter()` | Add as concrete with no-op default |
| NEW | `get_content_filter_settings()` | Add as concrete returning `{}` |
| NEW | `get_traffic_shaping_rules()` | Add as concrete returning `[]` — read-back for DSCP marking |
| NEW | `get_firewall_rules()` | Add as concrete returning `[]` — read-back for firewall rules |
| NEW | `configure_syslog()` | Add as concrete with no-op default — syslog server config (see §3.8) |
| NEW | `get_syslog_settings()` | Add as concrete returning `{}` — syslog config read-back |
| CHANGED | `FirewallRule` dataclass | Add `application_category: str \| None` field for L7 category-based rules |
| CHANGED | `apply_policy()` action dict | Add `set_dscp` field for DSCP marking |
| CHANGED | `get_routing_table()` | Demote from abstract to concrete with default |
| CHANGED | `console` property | Return type becomes `BoardfarmPexpect \| None` |
| CHANGED | `SLAPolicy` dataclass | Remove `probe_interval_ms`, `failover_threshold`, `recovery_threshold` |
| CHANGED | `PathMetrics` dataclass | Add `mos: float \| None` |
| CHANGED | `LinkHealthReport` dataclass | Add `mos: float \| None` |
| CHANGED | `apply_policy()` | Policy dict schema extended for L7 matching |
| REMOVED | `start_sla_monitoring()` | Declarative model replaces imperative lifecycle |
| REMOVED | `stop_sla_monitoring()` | Same |
| REMOVED | `apply_sla_monitoring()` | Folded into policy dict |

---

## 5. New Dataclasses

### 5.1 `AppFlow`

```python
@dataclass
class AppFlow:
    """A single application-level traffic flow as identified by the device's DPI engine."""

    application: str       # e.g. "Zoom", "Office 365 Sharepoint"
    category: str          # e.g. "Video Conferencing", "Productivity"
    src_ip: str
    dst_ip: str
    wan_interface: str     # logical WAN label that carried this flow
    bytes_sent: int
    bytes_received: int
```

### 5.2 `FirewallRule`

```python
@dataclass
class FirewallRule:
    """A vendor-neutral firewall rule definition.

    Supports L3/L4 (protocol/cidr/port) and L7 rules.
    Set both application and application_category to None for L3/L4-only.
    """

    name: str
    action: str                          # "allow" | "deny" | "alert"
    protocol: str                        # "tcp" | "udp" | "icmp" | "any"
    src_cidr: str                        # CIDR notation or "any"
    dst_cidr: str                        # CIDR notation or "any"
    dst_port: str                        # "any", "443", "1-1024"
    application: str | None = None       # L7 specific app (e.g. "BitTorrent")
    application_category: str | None = None  # L7 category (e.g. "Sports")
    log: bool = True
```

**L7 vendor mapping:**

| Field | Meraki | Cisco Catalyst | FortiGate | VeloCloud | Prisma |
|-------|--------|---------------|-----------|-----------|--------|
| `application` | `type: "application"` | NBAR2 app name | `internet-service-id` | Specific app | App-ID |
| `application_category` | `type: "applicationCategory"` | NBAR2 app-family | `internet-service-group` | App category | App-ID group |

### 5.3 `VPNPeerStatus`

```python
@dataclass
class VPNPeerStatus:
    """Status of a VPN/overlay tunnel to a peer site."""

    peer_id: str           # network ID, site name, or peer IP
    peer_name: str
    reachability: str      # "reachable" | "unreachable"
    uplink: str            # WAN interface used for the tunnel
```

### 5.4 Revised `SLAPolicy`

```python
@dataclass
class SLAPolicy:
    """Quality thresholds for WAN link health monitoring.

    Declarative model: defining the policy activates monitoring.
    Removing the policy deactivates it.
    """

    name: str
    max_latency_ms: float = 150.0
    max_jitter_ms: float = 30.0
    max_loss_percent: float = 10.0
```

Fields removed: `probe_interval_ms`, `failover_threshold`,
`recovery_threshold` — these are implementation details not exposed
uniformly across vendors.

### 5.5 Revised `PathMetrics`

```python
@dataclass
class PathMetrics:
    """Per-link quality metrics as measured by the device."""

    latency_ms: float
    jitter_ms: float
    loss_percent: float
    link_name: str
    mos: float | None = None  # Mean Opinion Score (VeloCloud, Meraki VPN stats)
```

### 5.6 Revised `LinkHealthReport`

```python
@dataclass
class LinkHealthReport:
    """Current health metrics for a WAN link."""

    state: str               # "up" | "down" | "degraded"
    route_installed: bool
    avg_rtt_ms: float | None
    jitter_ms: float | None
    loss_percent: float
    sla_compliant: bool
    mos: float | None = None
```

### 5.7 `TrafficShapingRule`

```python
@dataclass
class TrafficShapingRule:
    """A traffic shaping / QoS marking rule as read back from the device."""

    name: str
    match: dict
    dscp_tag: int | None = None
    bandwidth_limit_kbps: int | None = None
    priority: str | None = None  # "low" | "normal" | "high"
```

---

## 6. Revised Policy Dict Schema

The vendor-neutral policy dict passed to `apply_policy()` is extended
to support L7 application matching as the primary mechanism.

### 6.1 Application-Based Steering (Primary)

```python
{
    "name": "video-to-wan2",
    "match": {
        "application_category": "Video Conferencing",
    },
    "action": {
        "prefer_wan": "wan2",
    },
    "sla_policy": "voice-sla",
    "failover": "on_sla_violation",
}
```

### 6.2 Specific Application Steering

```python
{
    "name": "zoom-to-wan1",
    "match": {
        "application": "Zoom",
    },
    "action": {
        "prefer_wan": "wan1",
    },
}
```

### 6.3 L3 Prefix-Based Steering (All Vendors)

```python
{
    "name": "datacenter-to-wan1",
    "match": {
        "dst_prefix": "10.0.0.0/8",
        "protocol": "tcp",
    },
    "action": {
        "prefer_wan": "wan1",
    },
}
```

### 6.4 DSCP-Based Steering (LinuxSDWANRouter Fallback)

```python
{
    "name": "dscp-af41",
    "match": {
        "dscp": 34,
    },
    "action": {
        "prefer_wan": "wan2",
    },
}
```

### 6.5 Load Balancing

```python
{
    "name": "balance-all",
    "match": {
        "dst_prefix": "0.0.0.0/0",
    },
    "action": {
        "load_balance": True,
    },
}
```

### 6.6 Match Field Reference

| Field | Type | Supported by | Description |
|-------|------|-------------|-------------|
| `application` | string | Cisco, FortiGate, VeloCloud, Prisma, Meraki | Specific application name |
| `application_category` | string | Cisco, FortiGate, VeloCloud, Prisma, Meraki | Application category |
| `dst_prefix` | string | All | Destination CIDR |
| `src_prefix` | string | All | Source CIDR |
| `protocol` | string | All | `"tcp"`, `"udp"`, `"icmp"`, `"any"` |
| `dst_port` | string | All | `"any"`, `"443"`, `"1-1024"` |
| `src_port` | string | All | Same format as `dst_port` |
| `dscp` | int | LinuxSDWAN, FortiGate, Cisco, VeloCloud | DSCP value (0-63) |

### 6.7 Action Field Reference

| Field | Type | Description |
|-------|------|-------------|
| `prefer_wan` | string | Logical WAN label (`"wan1"`, `"wan2"`) |
| `load_balance` | bool | Distribute across available WANs |
| `set_dscp` | int | Mark matching packets with DSCP value (0-63) |

**`set_dscp` vendor mapping:**

| Vendor | Mechanism |
|--------|-----------|
| Cisco Catalyst | QoS policy-map `set dscp` |
| FortiGate | SD-WAN rule `set dscp-tag` |
| VeloCloud | Business policy QoS class DSCP marking |
| Prisma | QoS policy DSCP remark |
| Meraki | `updateNetworkApplianceTrafficShapingRules` with `dscpTagValue` |
| LinuxSDWAN | `iptables -t mangle -j DSCP --set-dscp` |

### 6.8 Top-Level Field Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | **Yes** | Policy name (used for `remove_policy()`) |
| `match` | dict | **Yes** | Traffic matching criteria |
| `action` | dict | **Yes** | Steering action |
| `sla_policy` | string | No | Reference to a configured SLA policy name |
| `failover` | string | No | `"on_sla_violation"` or `"on_link_down"` |

---

## 7. Vendor Translation Notes

### 7.1 Cisco Catalyst SD-WAN

- `application` / `application_category` → NBAR2 application name in App-Route policy
- `sla_policy` → SLA-class list reference in vSmart centralized policy
- `prefer_wan` → preferred-color in App-Route policy
- `failover: "on_sla_violation"` → SLA-class fallback action

### 7.2 Fortinet FortiGate

- `application_category` → `internet-service-id` in SD-WAN rule
- `sla_policy` → `performance-sla` health-check reference
- `prefer_wan` → `set priority` on SD-WAN member
- `failover: "on_sla_violation"` → SLA target in SD-WAN rule strategy `best-quality`

### 7.3 VMware VeloCloud

- `application_category` → Application map classification in business policy
- `sla_policy` → QoS profile threshold
- `prefer_wan` → Link steering in business policy rule
- `failover` → Link steering failover behavior

### 7.4 Palo Alto Prisma SD-WAN

- `application` → App-ID match in path policy
- `sla_policy` → Path quality profile reference
- `prefer_wan` → Traffic distribution profile (Best Available Path)
- `failover: "on_sla_violation"` → Path replacement trigger

### 7.5 Meraki MX

- `application_category` → `trafficFilter.type: "applicationCategory"` + `value.id` in uplink selection
- `sla_policy` → `performanceClass.customPerformanceClassId`
- `prefer_wan` → `preferredUplink` in `wanTrafficUplinkPreferences` / `vpnTrafficUplinkPreferences`
- `failover: "on_sla_violation"` → `failOverCriterion: "poorPerformance"`

### 7.6 LinuxSDWANRouter

- `application` / `application_category` → **Not supported** (no DPI); raise warning or skip
- `dscp` → FRR PBR route-map `match ip dscp`
- `dst_prefix` → FRR PBR route-map `match ip address prefix-list`
- `prefer_wan` → `set ip next-hop` pointing to WAN gateway
- `sla_policy` → Internal probe daemon threshold configuration

---

## 8. Security Service Vendor Translation

### 8.1 IPS Mode Translation

| Template mode | Cisco Catalyst | FortiGate | VeloCloud | Prisma | Meraki |
|---------------|---------------|-----------|-----------|--------|--------|
| `"disabled"` | UTD policy detached | IPS sensor disabled | IDS/IPS off | Threat Prevention profile detached | `mode: "disabled"` |
| `"detection"` | UTD IDS-only mode | IPS sensor: monitor | IDS mode (detect) | Threat Prevention: alert | `mode: "detection"` |
| `"prevention"` | UTD IPS mode (block) | IPS sensor: block | IPS mode (protect) | Threat Prevention: block | `mode: "prevention"` |

### 8.2 IPS Ruleset/Sensitivity Translation

| Template ruleset | Cisco Catalyst | FortiGate | VeloCloud | Prisma | Meraki |
|------------------|---------------|-----------|-----------|--------|--------|
| `"connectivity"` | Signature set: connectivity | Filter: low severity | Minimal detection profile | Best-practice profile | `idsRulesets: "connectivity"` |
| `"balanced"` | Signature set: balanced | Filter: medium severity | Standard detection profile | Balanced profile | `idsRulesets: "balanced"` |
| `"security"` | Signature set: security | Filter: high + critical | Aggressive detection profile | Strict profile | `idsRulesets: "security"` |

### 8.3 Malware Protection Translation

| Template param | Cisco Catalyst | FortiGate | VeloCloud | Prisma | Meraki |
|---------------|---------------|-----------|-----------|--------|--------|
| `enabled=True` | AMP feature template attached | AV profile enabled per policy | N/A (limited) | WildFire enabled | `updateNetworkApplianceSecurityMalware(mode="enabled")` |
| `enabled=False` | AMP feature template detached | AV profile disabled | N/A | WildFire disabled | `updateNetworkApplianceSecurityMalware(mode="disabled")` |

### 8.4 Content Filter Translation

| Template param | Cisco Catalyst | FortiGate | VeloCloud | Prisma | Meraki |
|---------------|---------------|-----------|-----------|--------|--------|
| `enabled` | URL filter policy attached/detached | Web filter profile enabled/disabled | URL filter on/off | URL filter profile attached/detached | Content filter settings update |
| `blocked_categories` | URL category list in filter | FortiGuard web filter category block | URL category list | URL category list | `blockedUrlCategories` list |
| `allowed_urls` | URL whitelist | Web filter URL rating override (allow) | URL allow list | URL allow list | `allowedUrlPatterns` list |
| `blocked_urls` | URL blacklist | Web filter URL rating override (block) | URL block list | URL block list | `blockedUrlPatterns` list |

### 8.5 LinuxSDWANRouter

All security service methods inherit the concrete no-op defaults.
LinuxSDWANRouter has no IPS, malware protection, or content filtering.
`get_ips_settings()`, `get_malware_settings()`, and
`get_content_filter_settings()` all return `{}`.

---

## 9. Syslog / Firewall Read-Back Vendor Translation

### 9.1 `configure_syslog(server, port, roles)` Translation

| Vendor | API | Role mapping |
|--------|-----|-------------|
| **Meraki** | `updateNetworkSyslogServers(networkId, servers=[{"host": server, "port": port, "roles": meraki_roles}])` | `"firewall"` → `"Firewall"`, `"flows"` → `"Flows"`, `"security"` → `"Security events"`, `"urls"` → `"URLs"`, `"event_log"` → `"Appliance event log"` |
| **Cisco Catalyst** | Feature template: `logging` section — server, port, source-interface, facility, severity | Per-feature logging (firewall, IPS, etc.) controlled by security policy |
| **FortiGate** | `PUT /api/v2/cmdb/log.syslogd/setting` (`server`, `port`, `status: enable`) + `PUT /api/v2/cmdb/log.syslogd/filter` | Per-policy: `set logtraffic all\|utm\|disable` controls categories |
| **VeloCloud** | Edge/profile syslog export config — server, port, protocol (UDP/TCP), facility | Configurable event categories at edge or profile level |
| **Prisma** | Syslog server profile + log forwarding profile | Log forwarding profiles tied to security rules |
| **LinuxSDWAN** | rsyslog: write `/etc/rsyslog.d/50-boardfarm.conf` with `*.* @server:port` | iptables LOG target sends to local syslog; rsyslog forwards to remote |

### 9.2 `get_syslog_settings()` Translation

| Vendor | API | Returns |
|--------|-----|---------|
| **Meraki** | `getNetworkSyslogServers(networkId)` | `{"servers": [{host, port, roles}]}` |
| **Cisco Catalyst** | Feature template read-back | Server, facility, severity config |
| **FortiGate** | `GET /api/v2/cmdb/log.syslogd/setting` | Server, port, status |
| **VeloCloud** | Orchestrator edge/profile syslog config | Server, port, protocol |
| **Prisma** | Syslog server profile read-back | Server, port, forwarding profile |
| **LinuxSDWAN** | Internal state (`_syslog_server`, `_syslog_port`, `_syslog_roles`) | `{"servers": [{host, port, roles}]}` |

### 9.3 `get_firewall_rules()` Translation

| Vendor | API | Returns |
|--------|-----|---------|
| **Meraki** | `getNetworkApplianceFirewallL3FirewallRules(networkId)` + `getNetworkApplianceFirewallL7FirewallRules(networkId)` | Ordered array: `policy`, `protocol`, `srcCidr`, `destCidr`, `destPort`, `syslogEnabled`, `comment` |
| **Cisco Catalyst** | `GET /device/acl/...` or security-policy template read-back | ACL entries with action, match criteria |
| **FortiGate** | `GET /api/v2/cmdb/firewall/policy` | Full policy objects: action, match, logtraffic, security profiles |
| **VeloCloud** | Edge/profile firewall rules via Orchestrator API | Rule array: action, match, logging |
| **Prisma** | `GET /sdwan/v2.0/api/securitypolicyrules` | Security policy rules: action, match |
| **LinuxSDWAN** | `iptables -S INPUT`, `iptables -S FORWARD` — parse `bf_` comment tags | `FirewallRule` list with name, action, protocol, src/dst CIDR, port, log flag |
