# App-Router Implementation Plan — Split North-Segment Topology

**Date:** March 7, 2026
**Status:** Approved for implementation
**Related:** `testbed-configuration.md`, `application-services.md`, `traffic-management.md`
**Prerequisite for:** IPsec overlay tunnels (Option B, future)

---

## 1. Problem Statement

### 1.1 Current topology defect

The SD-WAN testbed currently places both traffic controllers (`wan1-tc`, `wan2-tc`) and all application services (`productivity-server`, `streaming-server`, `conf-server`, `ipsec-hub`) on a **single shared L2 segment** (`north-segment`, 172.16.0.0/24).

```
wan1-tc (.1) ──┐
               ├── north-segment (172.16.0.0/24) ── app servers (.10, .11, .12)
wan2-tc (.2) ──┘
```

All app servers have `gateway: 172.16.0.1` (wan1-tc). When the DUT fails traffic from wan1 to wan2, forward-path traffic arrives at the app server via wan2-tc, but the **return path always exits through wan1-tc** because that is the app server's only known gateway. If wan1 is impaired (100% loss), replies are black-holed.

### 1.2 Current workaround

An `iptables MASQUERADE` rule on each TC's `eth-north` rewrites the source IP of LAN-sourced traffic to the TC's own north-segment IP. This forces replies back through the same TC that forwarded the request, avoiding asymmetric routing.

### 1.3 Why this is inadequate

1. **Not production-representative.** In real multi-WAN deployments, WAN links terminate at different ISP/provider edges. Application servers are reachable via the internet's routing fabric; return traffic follows the correct path naturally. No intermediate device performs MASQUERADE.
2. **Masks DUT routing defects.** If the DUT misconfigures source NAT or fails to maintain connection tracking, MASQUERADE on the TC hides the bug.
3. **Prevents future overlay testing.** IPsec/VXLAN tunnels require distinct underlay paths. A shared L2 north-segment provides no meaningful WAN diversity for overlay traffic.
4. **Violates the principle of the Traffic Controller.** The TC's role is WAN impairment emulation (delay, loss, bandwidth), not address translation. Adding NAT to it conflates responsibilities.

---

## 2. Solution: Split North-Segment with App-Router

### 2.1 Design principle

Each WAN path gets its **own dedicated north-side network**. A lightweight router container (`app-router`) connects these per-WAN networks to a shared application services network. The app-router provides multi-path return routing — it knows how to reach the DUT's LAN via either WAN path and selects the correct return path based on which interface the traffic arrived on.

This mirrors production topologies where a datacenter or cloud edge has multiple upstream links from different providers, and the edge router handles return-path selection.

### 2.2 Target topology

```
                    ┌─ dut-wan1 (10.10.1.0/30) ─┐
LAN ── DUT ─────────┤                            ├── wan1-tc ── north-wan1 (172.16.1.0/24) ──┐
                    └─ dut-wan2 (10.10.2.0/30) ─┘                                            │
                                                   wan2-tc ── north-wan2 (172.16.2.0/24) ──┤
                                                                                             │
                                                                                         app-router
                                                                                             │
                                                                                    app-services (172.16.0.0/24)
                                                                                             │
                                                                        ┌────────────────────┼────────────────────┐
                                                                   prod-srv (.10)      stream-srv (.11)     conf-srv (.12)
```

### 2.3 Key properties

| Property | Current (flat) | Target (split) |
| :--- | :--- | :--- |
| North-side L2 domains | 1 (shared) | 3 (per-WAN + app-services) |
| App server gateway | wan1-tc (172.16.0.1) | app-router (172.16.0.254) |
| Return path selection | MASQUERADE (hack) | App-router routing table |
| TC NAT responsibility | MASQUERADE on eth-north | None (pure impairment) |
| IPsec overlay ready | No (shared underlay) | Yes (distinct underlay per WAN) |

---

## 3. Implementation Details

### 3.1 New OVS bridges

Add two new Raikou OVS bridges. The existing `north-segment` bridge is **retained** for the application services network (unchanged IPs).

| Bridge | Subnet | Purpose |
| :--- | :--- | :--- |
| `north-wan1` (new) | `172.16.1.0/24` | wan1-tc north side ↔ app-router wan1 interface |
| `north-wan2` (new) | `172.16.2.0/24` | wan2-tc north side ↔ app-router wan2 interface |
| `north-segment` (existing) | `172.16.0.0/24` | App-router south side ↔ application services |

### 3.2 IP address plan

| Container | Interface | Bridge | IP Address | Notes |
| :--- | :--- | :--- | :--- | :--- |
| wan1-tc | eth-north | north-wan1 | 172.16.1.1/24 | Changed from 172.16.0.1 |
| wan2-tc | eth-north | north-wan2 | 172.16.2.1/24 | Changed from 172.16.0.2 |
| app-router | eth-wan1 | north-wan1 | 172.16.1.254/24 | New |
| app-router | eth-wan2 | north-wan2 | 172.16.2.254/24 | New |
| app-router | eth-south | north-segment | 172.16.0.254/24 | New |
| productivity-server | eth1 | north-segment | 172.16.0.10/24 | Unchanged, gateway → .254 |
| streaming-server | eth1 | north-segment | 172.16.0.11/24 | Unchanged, gateway → .254 |
| conf-server | eth1 | north-segment | 172.16.0.12/24 | Unchanged, gateway → .254 |
| ipsec-hub | eth1 | north-segment | 172.16.0.20/24 | Unchanged, gateway → .254 |

### 3.3 App-router container

A minimal Alpine/Debian container with IP forwarding enabled and static routes.

**Routing table:**

```
# Forward: DUT LAN is reachable via either WAN path
ip route add 10.10.1.0/30 via 172.16.1.1 dev eth-wan1
ip route add 10.10.2.0/30 via 172.16.2.1 dev eth-wan2

# Return path: use policy routing so replies go back the way they came
ip rule add from 172.16.1.0/24 lookup wan1
ip rule add from 172.16.2.0/24 lookup wan2

ip route add default via 172.16.1.1 table wan1
ip route add 172.16.0.0/24 dev eth-south table wan1

ip route add default via 172.16.2.1 table wan2
ip route add 172.16.0.0/24 dev eth-south table wan2
```

**Implementation approach for symmetric return routing:**

The app-router must ensure that when traffic arrives from `north-wan1` destined for an app server on `north-segment`, the reply returns via `north-wan1` (not `north-wan2`). Two approaches:

1. **Policy routing with connection tracking (recommended).** Use `iptables` CONNMARK to tag connections by ingress interface, then use `ip rule fwmark` to select the return table. This correctly handles the case where app servers initiate connections (not just replies).

2. **Source-based policy routing (simpler).** Since traffic arriving via wan1-tc will have been SNAT'd by the DUT (source IP from 10.10.1.0/30 subnet), the app-router can use `ip rule from 10.10.1.0/30 lookup wan1` to route replies. This is simpler but assumes the DUT always NATs — which it does for LAN-sourced traffic.

The recommended approach is CONNMARK-based routing, as it works regardless of whether the DUT performs NAT:

```bash
# Mark incoming connections by interface
iptables -t mangle -A PREROUTING -i eth-wan1 -j CONNMARK --set-mark 1
iptables -t mangle -A PREROUTING -i eth-wan2 -j CONNMARK --set-mark 2

# Restore mark on reply packets
iptables -t mangle -A PREROUTING -j CONNMARK --restore-mark

# Route based on mark
ip rule add fwmark 1 lookup wan1
ip rule add fwmark 2 lookup wan2
```

### 3.4 Traffic controller changes

**Remove MASQUERADE.** The `iptables` NAT rule and the `iptables` package dependency are removed from the TC init script and Dockerfile. The TC returns to its intended role: pure `tc netem` impairment.

**Update north-side route.** The TC's static route for `192.168.10.0/24` (return path to LAN) currently points at the DUT's WAN IP. This remains correct — the TC still forwards LAN-destined traffic back through the DUT.

**Update north-side IP.** `wan1-tc` moves from `172.16.0.1/24` to `172.16.1.1/24`; `wan2-tc` moves from `172.16.0.2/24` to `172.16.2.1/24`.

### 3.5 SLA probe daemon adjustment

The SLA probe on the DUT sends ICMP probes to the TC gateway IPs. These addresses change:

| Link | Current probe target | New probe target |
| :--- | :--- | :--- |
| wan1 | 10.10.1.2 (wan1-tc eth-dut) | 10.10.1.2 (unchanged) |
| wan2 | 10.10.2.2 (wan2-tc eth-dut) | 10.10.2.2 (unchanged) |

The SLA probe targets the DUT-side interface of the TC (`eth-dut`), not the north-side. **No SLA probe changes needed.**

### 3.6 DUT (linux-sdwan-router) changes

The DUT's FRR routes point to the TC gateway IPs on the `dut-wan1` and `dut-wan2` subnets. These are unchanged:

- `ip route 0.0.0.0/0 10.10.1.2 10` (wan1 preferred)
- `ip route 0.0.0.0/0 10.10.2.2 200` (wan2 backup)

**No DUT changes needed.**

---

## 4. Files to modify

| File                                                  | Change                                                                                                                                 | Scope           |
| :---------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------- | :-------------- |
| `raikou/config_sdwan.json`                            | Add `north-wan1`, `north-wan2` bridges; add `app-router` container; update TC north-side bridge/IP; update app server gateways to .254 | Raikou topology |
| `raikou/docker-compose-sdwan.yaml`                    | Add `app-router` service; update TC image tag; remove `iptables` from TC if desired                                                    | Docker Compose  |
| `raikou/components/app-router/` (new)                 | `Dockerfile`, `resources/init` — minimal Alpine container with ip forwarding, policy routing, CONNMARK rules                           | New component   |
| `raikou/components/traffic-controller/resources/init` | Remove `iptables MASQUERADE` rule; update DUT gateway derivation if needed                                                             | TC init         |
| `raikou/components/traffic-controller/Dockerfile`     | Remove `iptables` from apt-get install (optional, keep if useful for debugging); bump version to `0.03`                                | TC Dockerfile   |
| `raikou/components/ipsec-hub/resources/init`          | Update static routes: `192.168.10.0/24 via 172.16.0.254` (app-router instead of wan1-tc)                                               | IPsec hub       |
| `bf_config/bf_config_sdwan.json`                      | No changes expected (app-router is infrastructure, not a Boardfarm-managed device)                                                     | —               |
| `testbed-configuration.md`                 | Update topology diagrams, network segments table, component table                                                                      | Documentation   |
| `tests/step_defs/sdwan_steps.py`                      | No changes expected (APP_CONFIG URLs use 172.16.0.x which is unchanged)                                                                | —               |
| `tests/unit/test_step_defs/test_sdwan_steps.py`       | No changes expected                                                                                                                    | —               |

---

## 5. New component: app-router

### 5.1 Dockerfile

```dockerfile
# App-Router — multi-path return routing for split north-segment topology
# Three interfaces from Raikou OVS:
#   eth-wan1 (north-wan1) — upstream path via wan1-tc
#   eth-wan2 (north-wan2) — upstream path via wan2-tc
#   eth-south (north-segment) — downstream to app services
#
# Provides symmetric return routing using CONNMARK + policy routing.
# See: app-router.md

FROM alpine:3.20

LABEL maintainer="rjvisser@alottabits.com"
LABEL version="app_router_0.01"

RUN apk add --no-cache \
    iproute2 \
    iptables \
    iputils-ping \
    && echo "net.ipv4.ip_forward = 1" >> /etc/sysctl.conf

COPY ./resources/init /root/init
RUN chmod +x /root/init

CMD ["/bin/sh", "/root/init"]
```

### 5.2 Init script (resources/init)

```bash
#!/bin/sh -e
#
# App-router init — symmetric return routing via CONNMARK
# Waits for three Raikou-injected interfaces, configures policy routing.

WAN1_IFACE="${APP_ROUTER_WAN1_IFACE:-eth-wan1}"
WAN2_IFACE="${APP_ROUTER_WAN2_IFACE:-eth-wan2}"
SOUTH_IFACE="${APP_ROUTER_SOUTH_IFACE:-eth-south}"

wait_for_iface() {
    local iface=$1 count=0
    while [ ! -d "/sys/class/net/$iface" ] && [ $count -lt 60 ]; do
        echo "Waiting for $iface..."
        sleep 2
        count=$((count + 1))
    done
    if [ ! -d "/sys/class/net/$iface" ]; then
        echo "ERROR: $iface not found after 120s"
        exit 1
    fi
    ip link set "$iface" up
    echo "$iface is up"
}

echo "Waiting for Raikou-injected interfaces..."
wait_for_iface "$WAN1_IFACE"
wait_for_iface "$WAN2_IFACE"
wait_for_iface "$SOUTH_IFACE"

sysctl -w net.ipv4.ip_forward=1

# --- Routing tables ---
echo "100 wan1" >> /etc/iproute2/rt_tables
echo "200 wan2" >> /etc/iproute2/rt_tables

# Table wan1: return traffic via north-wan1
ip route add 172.16.0.0/24 dev "$SOUTH_IFACE" table wan1
ip route add default via 172.16.1.1 table wan1

# Table wan2: return traffic via north-wan2
ip route add 172.16.0.0/24 dev "$SOUTH_IFACE" table wan2
ip route add default via 172.16.2.1 table wan2

# --- CONNMARK: tag connections by ingress WAN interface ---
iptables -t mangle -A PREROUTING -i "$WAN1_IFACE" -m conntrack --ctstate NEW -j CONNMARK --set-mark 1
iptables -t mangle -A PREROUTING -i "$WAN2_IFACE" -m conntrack --ctstate NEW -j CONNMARK --set-mark 2
iptables -t mangle -A PREROUTING -j CONNMARK --restore-mark

# --- Policy routing: select table by mark ---
ip rule add fwmark 1 lookup wan1 priority 100
ip rule add fwmark 2 lookup wan2 priority 200

echo "App-router ready. Policy routing active."
echo "  wan1 path: north-wan1 (172.16.1.0/24) via $WAN1_IFACE"
echo "  wan2 path: north-wan2 (172.16.2.0/24) via $WAN2_IFACE"
echo "  app-services: north-segment (172.16.0.0/24) via $SOUTH_IFACE"

# Keep container alive
exec tail -f /dev/null
```

---

## 6. Updated Raikou topology (config_sdwan.json)

Key changes highlighted:

```jsonc
{
    "bridge": {
        "lan-segment": {},
        "dut-wan1": {},
        "dut-wan2": {},
        "north-wan1": {},          // NEW — wan1-tc ↔ app-router
        "north-wan2": {},          // NEW — wan2-tc ↔ app-router
        "north-segment": {},       // RETAINED — app-router ↔ app services
        "content-internal": {}
    },
    "container": {
        // ... lan-qoe-client, linux-sdwan-router unchanged ...

        "wan1-tc": [
            { "bridge": "dut-wan1",  "iface": "eth-dut",   "ipaddress": "10.10.1.2/30" },
            { "bridge": "north-wan1", "iface": "eth-north", "ipaddress": "172.16.1.1/24" }
            //                        ^^^^^^^^^ changed from north-segment / 172.16.0.1
        ],
        "wan2-tc": [
            { "bridge": "dut-wan2",  "iface": "eth-dut",   "ipaddress": "10.10.2.2/30" },
            { "bridge": "north-wan2", "iface": "eth-north", "ipaddress": "172.16.2.1/24" }
            //                        ^^^^^^^^^ changed from north-segment / 172.16.0.2
        ],
        "app-router": [            // NEW
            { "bridge": "north-wan1",    "iface": "eth-wan1",  "ipaddress": "172.16.1.254/24" },
            { "bridge": "north-wan2",    "iface": "eth-wan2",  "ipaddress": "172.16.2.254/24" },
            { "bridge": "north-segment", "iface": "eth-south", "ipaddress": "172.16.0.254/24" }
        ],
        "productivity-server": [
            { "bridge": "north-segment", "iface": "eth1", "ipaddress": "172.16.0.10/24",
              "gateway": "172.16.0.254" }   // changed from 172.16.0.1
        ],
        "streaming-server": [
            { "bridge": "north-segment", "iface": "eth1", "ipaddress": "172.16.0.11/24",
              "gateway": "172.16.0.254" },  // changed from 172.16.0.1
            { "bridge": "content-internal", "iface": "eth2", "ipaddress": "10.100.0.1/30" }
        ],
        "conf-server": [
            { "bridge": "north-segment", "iface": "eth1", "ipaddress": "172.16.0.12/24",
              "gateway": "172.16.0.254" }   // changed from 172.16.0.1
        ],
        "ipsec-hub": [
            { "bridge": "north-segment", "iface": "eth1", "ipaddress": "172.16.0.20/24",
              "gateway": "172.16.0.254" }   // changed from 172.16.0.1
        ]
        // ... minio unchanged ...
    }
}
```

---

## 7. Updated topology diagram

```
                                        ┌──────────────────┐
           ┌────────────────────────────│   lan-segment     │────────────────────────────┐
           │                            │  192.168.10.0/24  │                            │
           │                            └──────────────────┘                            │
    ┌──────┴──────┐                                                              ┌──────┴──────┐
    │ lan-qoe-    │                                                              │ lan-traffic-│
    │ client      │                                                              │ gen (Ph2+)  │
    │ .10         │                                                              │ .20         │
    └─────────────┘                                                              └─────────────┘
                                   ┌─────────────────┐
                                   │ linux-sdwan-     │
                                   │ router (DUT)     │
                                   │ LAN: .1          │
                                   │ WAN1: 10.10.1.1  │
                                   │ WAN2: 10.10.2.1  │
                                   └───┬─────────┬───┘
                                       │         │
                          ┌────────────┘         └────────────┐
                   ┌──────┴──────┐                     ┌──────┴──────┐
                   │  dut-wan1   │                     │  dut-wan2   │
                   │ 10.10.1.0/30│                     │ 10.10.2.0/30│
                   └──────┬──────┘                     └──────┬──────┘
                   ┌──────┴──────┐                     ┌──────┴──────┐
                   │  wan1-tc    │                     │  wan2-tc    │
                   │ dut: .2    │                     │ dut: .2    │
                   │ north: .1   │                     │ north: .1   │
                   └──────┬──────┘                     └──────┬──────┘
                   ┌──────┴──────┐                     ┌──────┴──────┐
                   │ north-wan1  │                     │ north-wan2  │
                   │172.16.1.0/24│                     │172.16.2.0/24│
                   └──────┬──────┘                     └──────┬──────┘
                          │                                    │
                          └────────────┐         ┌────────────┘
                                   ┌───┴─────────┴───┐
                                   │   app-router     │
                                   │ wan1: .254       │
                                   │ wan2: .254       │
                                   │ south: .254      │
                                   └───────┬─────────┘
                                   ┌───────┴─────────┐
                                   │  north-segment   │
                                   │ 172.16.0.0/24    │
                                   └───┬───┬───┬───┬─┘
                                       │   │   │   │
                                  .10  .11 .12 .20
                                  prod strm conf ipsec
                                  srv  srv  srv  hub
```

---

## 8. Implementation sequence

### Phase 1: Infrastructure (no test changes)

1. Create `raikou/components/app-router/` (Dockerfile + init script)
2. Update `raikou/config_sdwan.json` (add bridges, add app-router, update TC and app server entries)
3. Update `raikou/docker-compose-sdwan.yaml` (add app-router service, update TC image tags)
4. Remove MASQUERADE from `raikou/components/traffic-controller/resources/init`
5. Update `raikou/components/ipsec-hub/resources/init` (gateway → 172.16.0.254)
6. Bump TC Dockerfile version to `traffic_controller_0.03`

### Phase 2: Rebuild and verify

7. `docker compose -f docker-compose-sdwan.yaml build`
8. `docker compose -f docker-compose-sdwan.yaml up -d`
9. Verify Raikou wires all new bridges correctly
10. Verify connectivity: `lan-qoe-client` → productivity-server via wan1 path
11. Verify connectivity: `lan-qoe-client` → productivity-server via wan2 path (with wan1 impaired)
12. Verify return-path symmetry without MASQUERADE

### Phase 3: Test suite validation

13. Run `pytest -k "UCSDWAN01Main"` — all 3 scenarios should pass without code changes
14. Update `testbed-configuration.md` topology diagrams and network segments table

---

## 9. Impact assessment

| Area | Impact |
| :--- | :--- |
| **Test code** (`sdwan_steps.py`, unit tests) | None. APP_CONFIG URLs use 172.16.0.x (north-segment), which is unchanged. |
| **Boardfarm device classes** | None. The app-router is infrastructure — not a Boardfarm-managed device. |
| **SLA probe daemon** | None. Probes target TC dut-side IPs (10.10.1.2, 10.10.2.2), unchanged. |
| **FRR routes on DUT** | None. Default routes via 10.10.1.2 and 10.10.2.2, unchanged. |
| **TC init script** | Simplified. MASQUERADE removed, DUT gateway route derivation unchanged. |
| **App server containers** | Gateway change only (172.16.0.1 → 172.16.0.254). No code changes. |
| **Docker resource usage** | +1 lightweight Alpine container (~10MB, minimal CPU). |

---

## 10. Future: Option B (IPsec overlay)

The split north-segment topology is a prerequisite for IPsec overlay testing. When Option B is implemented:

1. The `ipsec-hub` moves from `north-segment` to having interfaces on both `north-wan1` and `north-wan2` (similar to app-router)
2. The DUT builds IPsec tunnels to `ipsec-hub` through each WAN path
3. The `app-router` may be merged into or replaced by `ipsec-hub`
4. Decapsulated overlay traffic is routed to app services on `north-segment`

The OVS bridge infrastructure, IP addressing, and app-server placement established by Option A carry forward unchanged into Option B.
