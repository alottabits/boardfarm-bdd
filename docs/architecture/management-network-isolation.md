# Management Network Isolation

**Status:** Implemented  
**Scope:** All Boardfarm testbeds (home gateway, SD-WAN, physical RPi)

---

## Problem Statement

All testbed containers that use Docker's default network (`192.168.55.0/24`) alongside
Raikou OVS bridges suffer from a gateway configuration bug. When `ovs-docker` attempts
to set a default route via `--gateway`, the command fails silently because Docker has
already installed a default route via `192.168.55.1`:

```bash
# ovs-docker line 157 — fails when Docker default route exists
ip netns exec "$PID" ip route add default via "$GATEWAY"
# RTNETLINK answers: File exists (silently ignored)
```

**Consequence:** Containers like the ACS cannot reach the CPE's private WAN subnet
(`10.1.1.0/24`). TR-069 connection requests fail with `ENETUNREACH`, forcing the CPE
to wait for the next periodic Inform (5 minutes) instead of responding immediately.

Some containers work around this accidentally because boardfarm's `_setup_static_routes()`
applies a `static-route` option during initialization (e.g., `wan`, `sipcenter`, phones).
The ACS and DHCP containers have no such workaround.

Beyond routing, having two network stacks (Docker + OVS) per container creates:

- **Traffic leakage risk** — test traffic can escape to the Docker bridge or vice versa
- **Docker iptables interference** — MASQUERADE, FORWARD, DOCKER-ISOLATION rules on the
  host can affect OVS-routed packets
- **Non-deterministic routing** — two default routes, two sets of reachability, kernel
  `rp_filter` can silently drop packets
- **No enforcement** — Docker's eth0 is nominally "management only" but nothing prevents
  applications from binding to or routing through it

## Solution: Full Network Isolation


Migrate all containers to `network_mode: none` and replace Docker's default network with
a dedicated OVS management bridge. This guarantees:

- **Single network stack** — all interfaces are OVS-managed, fully controlled by raikou
- **No Docker iptables** — Docker networking is completely absent from the container
- **`ovs-docker --gateway` works** — no pre-existing default route to conflict with
- **True isolation** — management and test planes are separate OVS bridges

### Precedent

This model is already used by:
- `linux-sdwan-router` — `network_mode: none` in the SDWAN testbed
- `cpe` — `network_mode: none` in the PrplOS testbed

---

## Architecture

### Before (current)

```text
Container (e.g., acs)
├─ eth0  (Docker)    192.168.55.11/24  ← management (SSH, port mapping)
│  └─ default via 192.168.55.1        ← Docker default route (BLOCKS ovs-docker gateway)
└─ eth1  (OVS)       172.25.1.40/24   ← test network
   └─ gateway 172.25.1.1              ← FAILS to apply
```

### After (isolated)

```text
Container (e.g., acs)
├─ eth0  (OVS mgmt)  192.168.55.11/24  ← management (SSH)
│  └─ 192.168.55.0/24 via mgmt bridge
└─ eth1  (OVS test)   172.25.1.40/24   ← test network
   └─ default via 172.25.1.1           ← applies cleanly
```

The host accesses management services directly via the OVS management bridge IP
(e.g., `192.168.55.11:3000` for the ACS GUI) instead of Docker port mappings
(`localhost:3000`).

---

## Testbed Inventory

### PrplOS Testbed

**Compose:** `raikou/docker-compose.yaml`
**Raikou config:** `raikou/config.json`
**Boardfarm config:** `bf_config/boardfarm_config_prplos_rpi.json`

| Container | Current `network_mode` | Docker `ports` | OVS bridge(s) | Needs migration |
|---|---|---|---|---|
| `router` | default | `4000:22` | `cpe-rtr`, `rtr-wan`, `rtr-uplink` | Yes |
| `cpe` | **none** | `4004:22` (*) | `cpe-rtr`, `lan-cpe` | No (already isolated) |
| `wan` | default | `4001:22`, `8001:8080` | `rtr-wan` | Yes |
| `sipcenter` | default | `4005:22` | `rtr-wan` | Yes |
| `lan-phone` | default | `4006:22` | `lan-cpe` | Yes |
| `wan-phone` | default | `4007:22` | `rtr-wan` | Yes |
| `wan-phone2` | default | `4008:22` | `rtr-wan` | Yes |
| `lan` | default | `4002:22`, `8002:8080` | `lan-cpe` | Yes |
| `dhcp` | default | `4003:22` | `rtr-wan` | Yes |
| `mongo` | default | `27017:27017` | (none) | Yes |
| `acs` | default | `4503:22`, `7547`, `7557`, `7567`, `3000` | `rtr-wan` | Yes |

(*) CPE has `ports: 4004:22` but also `network_mode: none` — Docker ignores `ports`
when `network_mode: none` is set. SSH access to the CPE is via serial console, not SSH.

### OpenWrt RPi Testbed

**Compose:** `raikou/docker-compose-openwrt.yaml`
**Raikou config:** `raikou/config_openwrt.json`
**Boardfarm config:** `bf_config/boardfarm_config_prplos_rpi.json` (shared)

Identical container set as PrplOS except no `cpe` container (physical RPi instead).
All containers need migration. Same changes apply.

### SDWAN Testbed

**Compose:** `raikou/docker-compose-sdwan.yaml`
**Raikou config:** `raikou/config_sdwan.json`
**Boardfarm config:** `bf_config/bf_config_sdwan.json`

| Container | Current `network_mode` | Docker `ports` | OVS bridge(s) | Needs migration |
|---|---|---|---|---|
| `linux-sdwan-router` | **none** | (none) | `lan-segment`, `dut-wan1`, `dut-wan2` | No |
| `wan1-tc` | default | `5001:22` | `dut-wan1`, `north-wan1` | Yes |
| `wan2-tc` | default | `5002:22` | `dut-wan2`, `north-wan2` | Yes |
| `app-router` | default | (none) | `north-wan1`, `north-wan2`, `north-segment` | Yes |
| `lan-qoe-client` | default | `5003:22`, `18090:8080` | `lan-segment` | Yes |
| `lan-traffic-gen` | default | `5008:22` | `lan-segment` | Yes |
| `north-traffic-gen` | default | `5009:22` | `north-segment` | Yes |
| `productivity-server` | default | `5005:22`, `18080`, `18443` | `north-segment` | Yes |
| `streaming-server` | default | `5006:22`, `18081`, `18444` | `north-segment`, `content-internal` | Yes |
| `conf-server` | default | `5007:22`, `18445` | `north-segment` | Yes |
| `ipsec-hub` | default | (none) | `north-segment` | Yes |
| `minio` | default | `19000`, `19001` | `content-internal` | Yes |
| `log-collector` | default | (none) | (none) | Special (see below) |

**Note on `log-collector`:** This container mounts the Docker socket to tail container
logs. It does not participate in test traffic and has no OVS interfaces. It can remain
on Docker networking or use `network_mode: host` since it only reads Docker logs.

---

## Implementation Plan

### Phase 1: Management Bridge Definition

Add a `mgmt` OVS bridge to each raikou config with the same `192.168.55.0/24` subnet
currently used by Docker's default network. This preserves existing IP assignments.

The host-side bridge gets `192.168.55.1/24`, serving as the gateway for containers
that need outbound management access (e.g., ACS reaching external NTP, DNS).

#### `raikou/config.json` (PrplOS)

Add to the `bridge` section:

```json
"mgmt": {
    "iprange": "192.168.55.0/24",
    "ipaddress": "192.168.55.1/24"
}
```

Add a management interface as the **first entry** for each container (shown here for
containers that previously had Docker port mappings):

```json
"router":    [{ "bridge": "mgmt", "iface": "eth0", "ipaddress": "192.168.55.7/24" }, ...],
"wan":       [{ "bridge": "mgmt", "iface": "eth0", "ipaddress": "192.168.55.10/24" }, ...],
"lan":       [{ "bridge": "mgmt", "iface": "eth0", "ipaddress": "192.168.55.8/24" }, ...],
"dhcp":      [{ "bridge": "mgmt", "iface": "eth0", "ipaddress": "192.168.55.6/24" }, ...],
"sipcenter": [{ "bridge": "mgmt", "iface": "eth0", "ipaddress": "192.168.55.5/24" }, ...],
"lan-phone": [{ "bridge": "mgmt", "iface": "eth0", "ipaddress": "192.168.55.12/24" }, ...],
"wan-phone": [{ "bridge": "mgmt", "iface": "eth0", "ipaddress": "192.168.55.13/24" }, ...],
"wan-phone2":[{ "bridge": "mgmt", "iface": "eth0", "ipaddress": "192.168.55.14/24" }, ...],
"mongo":     [{ "bridge": "mgmt", "iface": "eth0", "ipaddress": "192.168.55.9/24" }],
"acs":       [{ "bridge": "mgmt", "iface": "eth0", "ipaddress": "192.168.55.11/24" }, ...]
```

The existing OVS test-network entries (second, third entries) remain unchanged.

#### `raikou/config_openwrt.json` (OpenWrt RPi)

Same management bridge and management interface entries as PrplOS (identical container
set minus the `cpe`).

#### `raikou/config_sdwan.json` (SDWAN)

Add to the `bridge` section:

```json
"mgmt": {
    "iprange": "192.168.55.0/24",
    "ipaddress": "192.168.55.1/24"
}
```

Add management interfaces:

```json
"wan1-tc":             [{ "bridge": "mgmt", "iface": "eth0", "ipaddress": "192.168.55.20/24" }, ...],
"wan2-tc":             [{ "bridge": "mgmt", "iface": "eth0", "ipaddress": "192.168.55.21/24" }, ...],
"app-router":          [{ "bridge": "mgmt", "iface": "eth0", "ipaddress": "192.168.55.22/24" }, ...],
"lan-qoe-client":      [{ "bridge": "mgmt", "iface": "eth0", "ipaddress": "192.168.55.23/24" }, ...],
"lan-traffic-gen":     [{ "bridge": "mgmt", "iface": "eth0", "ipaddress": "192.168.55.24/24" }, ...],
"north-traffic-gen":   [{ "bridge": "mgmt", "iface": "eth0", "ipaddress": "192.168.55.25/24" }, ...],
"productivity-server": [{ "bridge": "mgmt", "iface": "eth0", "ipaddress": "192.168.55.26/24" }, ...],
"streaming-server":    [{ "bridge": "mgmt", "iface": "eth0", "ipaddress": "192.168.55.27/24" }, ...],
"conf-server":         [{ "bridge": "mgmt", "iface": "eth0", "ipaddress": "192.168.55.28/24" }, ...],
"ipsec-hub":           [{ "bridge": "mgmt", "iface": "eth0", "ipaddress": "192.168.55.29/24" }, ...],
"minio":               [{ "bridge": "mgmt", "iface": "eth0", "ipaddress": "192.168.55.30/24" }, ...]
```

`linux-sdwan-router` already uses `network_mode: none` and does not need management
SSH — it is accessed via `docker exec`. No management interface needed.

### Phase 2: Docker Compose Changes

For each compose file, apply two changes per container:

1. Add `network_mode: none`
2. Remove the `ports:` directive

#### Example: ACS container in `raikou/docker-compose.yaml`

**Before:**

```yaml
acs:
    image: ghcr.io/alottabits/boardfarm-bdd/acs:v1.2.0
    depends_on:
        - mongo
    restart: always
    container_name: acs
    hostname: acs
    environment:
        - GENIEACS_MONGODB_CONNECTION_URL=mongodb://admin:bigfoot1@mongo:27017
    privileged: true
    ports:
        - 4503:22
        - 7547:7547
        - 7557:7557
        - 7567:7567
        - 3000:3000
    volumes:
        - opt_volume:/opt
```

**After:**

```yaml
acs:
    image: ghcr.io/alottabits/boardfarm-bdd/acs:v1.2.0
    depends_on:
        - mongo
    restart: always
    container_name: acs
    hostname: acs
    network_mode: none
    environment:
        - GENIEACS_MONGODB_CONNECTION_URL=mongodb://admin:bigfoot1@192.168.55.9:27017
    privileged: true
    volumes:
        - opt_volume:/opt
```

Key changes:

- `network_mode: none` added
- `ports:` removed (host accesses services via management bridge IP)
- `mongo` hostname replaced with explicit management IP `192.168.55.9`

#### Full container list — compose changes

**PrplOS / OpenWrt RPi** (`docker-compose.yaml`, `docker-compose-openwrt.yaml`):

| Container | Add `network_mode: none` | Remove `ports` | Update env vars |
|---|---|---|---|
| `router` | Yes | Yes | — |
| `cpe` | Already done | — | — |
| `wan` | Yes | Yes | — |
| `sipcenter` | Yes | Yes | — |
| `lan-phone` | Yes | Yes | — |
| `wan-phone` | Yes | Yes | — |
| `wan-phone2` | Yes | Yes | — |
| `lan` | Yes | Yes | — |
| `dhcp` | Yes | Yes | — |
| `mongo` | Yes | Yes | — |
| `acs` | Yes | Yes | `MONGODB_CONNECTION_URL`: `mongo` → `192.168.55.9` |

**SDWAN** (`docker-compose-sdwan.yaml`):

| Container | Add `network_mode: none` | Remove `ports` | Update env vars |
|---|---|---|---|
| `linux-sdwan-router` | Already done | — | — |
| `wan1-tc` | Yes | Yes | — |
| `wan2-tc` | Yes | Yes | — |
| `app-router` | Yes | — | — |
| `lan-qoe-client` | Yes | Yes | — |
| `lan-traffic-gen` | Yes | Yes | — |
| `north-traffic-gen` | Yes | Yes | — |
| `productivity-server` | Yes | Yes | — |
| `streaming-server` | Yes | Yes | — |
| `conf-server` | Yes | Yes | — |
| `ipsec-hub` | Yes | — | — |
| `minio` | Yes | Yes | — |
| `log-collector` | No (keep as-is or `network_mode: host`) | — | — |

#### Docker default network

Remove the `networks:` section from compose files or keep it only for `log-collector`
if that container remains on Docker networking. If all containers use
`network_mode: none`, the Docker default network is unused and can be omitted:

```yaml
# Remove or leave empty — no containers use Docker networking
# networks:
#     default:
#         ipam:
#             config:
#                 - subnet: 192.168.55.0/24
#                   gateway: 192.168.55.1
```

### Phase 3: Boardfarm Config Changes

Update device connection details from `localhost:<mapped-port>` to direct management
bridge IPs.

#### `bf_config/boardfarm_config_prplos_rpi.json`

| Device | Current `ipaddr` | Current `port` | New `ipaddr` | New `port` |
|---|---|---|---|---|
| `wan` | `localhost` | `4001` | `192.168.55.10` | `22` |
| `lan` | `localhost` | `4002` | `192.168.55.8` | `22` |
| `lan_phone` | `localhost` | `4006` | `192.168.55.12` | `22` |
| `sipcenter` | `localhost` | `4005` | `192.168.55.5` | `22` |
| `wan_phone` | `localhost` | `4007` | `192.168.55.13` | `22` |
| `wan_phone2` | `localhost` | `4008` | `192.168.55.14` | `22` |
| `provisioner` (dhcp) | `localhost` | `4003` | `192.168.55.6` | `22` |
| `genieacs` (acs) | `localhost` | `4503` | `192.168.55.11` | `22` |

Also update the `http_proxy` fields:
- `wan`: `"http_proxy": "192.168.55.10:8080"` (was `"localhost:8001"`)
- `lan`: `"http_proxy": "192.168.55.8:8080"` (was `"localhost:8002"`)

Also update the `router_ipaddr` in the provisioner:
- `"router_ipaddr": "192.168.55.7;22"` (was `"localhost;4000"`)

Also update the ACS GUI access:
- `"gui_port": 3000` remains the same (access via `192.168.55.11:3000`)

The `options` fields with `static-route:0.0.0.0/0-172.25.1.1` can be **removed** from
`wan`, `sipcenter`, `wan_phone`, `wan_phone2` since the OVS gateway will now apply
correctly. However, keeping them is harmless and provides defense-in-depth.

#### `bf_config/bf_config_sdwan.json`

| Device | Current `ipaddr` | Current `port` | New `ipaddr` | New `port` |
|---|---|---|---|---|
| `wan1_tc` | `localhost` | `5001` | `192.168.55.20` | `22` |
| `wan2_tc` | `localhost` | `5002` | `192.168.55.21` | `22` |
| `lan_qoe_client` | `localhost` | `5003` | `192.168.55.23` | `22` |
| `lan_traffic_gen` | `localhost` | `5008` | `192.168.55.24` | `22` |
| `north_traffic_gen` | `localhost` | `5009` | `192.168.55.25` | `22` |

The `sdwan` device uses `docker exec` (connection_type: `local_cmd`), so no change
needed.

### Phase 4: Host Access to Services

With Docker port mappings removed, host access to container services changes:

| Service | Before | After |
|---|---|---|
| ACS GUI | `http://localhost:3000` | `http://192.168.55.11:3000` |
| ACS NBI | `http://localhost:7557` | `http://192.168.55.11:7557` |
| ACS CWMP | `http://localhost:7547` | `http://192.168.55.11:7547` |
| MongoDB | `localhost:27017` | `192.168.55.9:27017` |
| WAN HTTP proxy | `localhost:8001` | `192.168.55.10:8080` |
| LAN HTTP proxy | `localhost:8002` | `192.168.55.8:8080` |
| MinIO S3 API | `localhost:19000` | `192.168.55.30:9000` |
| MinIO Console | `localhost:19001` | `192.168.55.30:9001` |
| Productivity HTTP | `localhost:18080` | `192.168.55.26:8080` |
| Streaming HTTP | `localhost:18081` | `192.168.55.27:8081` |

The host can reach these IPs because the `mgmt` OVS bridge is a host-level network
device with IP `192.168.55.1/24`.

**Optional:** If `localhost` access is desired for developer convenience, add iptables
DNAT rules on the host:

```bash
iptables -t nat -A PREROUTING -p tcp --dport 3000 -j DNAT --to-destination 192.168.55.11:3000
```

Or use a simple script that creates `socat` forwarders for each mapped port.

### Phase 5: Inter-Container Service Dependencies

Containers that reference other containers by Docker DNS name must switch to explicit
management IPs.

| Container | Reference | Before | After |
|---|---|---|---|
| `acs` | MongoDB | `mongodb://...@mongo:27017` | `mongodb://...@192.168.55.9:27017` |
| `streaming-server` | MinIO | (if using `minio` hostname) | `192.168.55.30` or content-internal IP |

For the SDWAN testbed, inter-container references are already via explicit IPs on OVS
test bridges, so no changes needed.

---

## Migration Order

Execute in this order to minimize downtime and allow incremental verification.

### Step 1: Add management bridge to raikou configs

All three `config*.json` files get the `mgmt` bridge definition and management interface
entries. **This is additive** — existing containers still work with Docker networking.
Raikou will create the bridge and attempt to add interfaces, but containers on Docker
networking will simply get an additional interface.

### Step 2: Verify management bridge connectivity

With containers still on Docker networking, verify that the `mgmt` bridge is created
and that the host can reach management IPs:

```bash
ping 192.168.55.11  # ACS management IP (via OVS mgmt bridge)
ssh root@192.168.55.11  # Should reach ACS container's eth0 on mgmt bridge
```

### Step 3: Migrate one testbed at a time

Start with the **PrplOS testbed** (simplest, most tested):

1. Update `docker-compose.yaml` (add `network_mode: none`, remove `ports`)
2. Update `boardfarm_config_prplos_rpi.json` (management IPs)
3. Bring containers down and up
4. Run the boardfarm initialization
5. Verify: SSH access, ACS NBI, ACS GUI, connection requests, reboot test

Then repeat for **OpenWrt RPi** and **SDWAN** testbeds.


### Step 4: Clean up

- Remove `static-route` options from boardfarm configs (optional, defense-in-depth)
- Remove the `networks:` section from compose files
- Update any CI/CD scripts that reference `localhost:<port>`
- Update developer documentation and READMEs

---


## Verification Checklist

For each migrated testbed, verify:

- [ ] `docker exec <container> ip route` shows only OVS-managed routes (no `192.168.55.1`
  via Docker bridge)
- [ ] Management SSH works: `ssh root@192.168.55.x`
- [ ] OVS gateway is applied: default route points to the correct test-network gateway
- [ ] ACS can ping CPE: `docker exec acs ping 10.1.1.22` (PrplOS/RPi testbeds)
- [ ] Connection request works: task with `?connection_request=` triggers immediate
  `6 CONNECTION REQUEST` Inform
- [ ] ACS GUI accessible from host: `curl http://192.168.55.11:3000`
- [ ] MongoDB accessible from ACS: `docker exec acs curl http://192.168.55.9:27017`
- [ ] Boardfarm initialization completes (`boardfarm -c <config> -e <env>`)
- [ ] Test execution passes (reboot test, password change, etc.)

---

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Container init scripts assume Docker DNS | Audit all env vars and config files for hostname references; replace with management IPs |
| Developer workflows depend on `localhost:port` | Document new access URLs; optionally provide a port-forwarding helper script |
| Raikou orchestrator loop timing — management bridge must be ready before containers need SSH | Raikou processes bridges first (line 333-334 in `orchestrator.py`), then containers — bridge will exist before interfaces are added |
| MongoDB on `network_mode: none` may not start if it expects Docker networking | MongoDB does not depend on Docker networking; it binds to `0.0.0.0` by default, which works on any interface |
| Container restart with `restart: always` — OVS interfaces are lost | This is an existing limitation. Raikou's 15-second polling loop re-adds interfaces. Management SSH may be briefly unavailable during re-injection. |
| `log-collector` needs Docker socket access | Keep `log-collector` on Docker networking or `network_mode: host` — it only reads Docker logs, no test traffic involvement |

---

## IP Address Allocation Plan

### PrplOS / OpenWrt RPi — Management Bridge (`192.168.55.0/24`)

| IP | Container | Notes |
|---|---|---|
| `192.168.55.1` | Host (bridge IP) | Gateway for management subnet |
| `192.168.55.5` | `sipcenter` | |
| `192.168.55.6` | `dhcp` | |
| `192.168.55.7` | `router` | |
| `192.168.55.8` | `lan` | |
| `192.168.55.9` | `mongo` | Referenced by ACS MongoDB URL |
| `192.168.55.10` | `wan` | |
| `192.168.55.11` | `acs` | ACS GUI, NBI, CWMP |
| `192.168.55.12` | `lan-phone` | |
| `192.168.55.13` | `wan-phone` | |
| `192.168.55.14` | `wan-phone2` | |

### SDWAN — Management Bridge (`192.168.55.0/24`)

| IP | Container | Notes |
|---|---|---|
| `192.168.55.1` | Host (bridge IP) | Gateway for management subnet |
| `192.168.55.20` | `wan1-tc` | |
| `192.168.55.21` | `wan2-tc` | |
| `192.168.55.22` | `app-router` | |
| `192.168.55.23` | `lan-qoe-client` | Playwright + SOCKS proxy |
| `192.168.55.24` | `lan-traffic-gen` | |
| `192.168.55.25` | `north-traffic-gen` | |
| `192.168.55.26` | `productivity-server` | Nginx HTTP/HTTPS |
| `192.168.55.27` | `streaming-server` | Nginx HLS |
| `192.168.55.28` | `conf-server` | WebRTC signalling |
| `192.168.55.29` | `ipsec-hub` | StrongSwan |
| `192.168.55.30` | `minio` | S3 API + console |

IP ranges `192.168.55.2–4` and `192.168.55.15–19` are reserved for future containers.

---

## No Changes Required in Raikou-Net

The raikou-net orchestrator and `ovs-docker` utility already fully support
`network_mode: none` containers. The `ovs-docker add-port` command works by:

1. Getting the container PID via `docker inspect`
2. Creating a veth pair
3. Moving one end into the container's network namespace
4. Assigning IP, MAC, and gateway

This mechanism is independent of Docker networking. With `network_mode: none`,
`ovs-docker --gateway` succeeds because there is no pre-existing default route.

No code changes are needed in:

- `raikou-net/app/orchestrator.py`
- `raikou-net/app/schemas.py`
- `/usr/bin/ovs-docker`
