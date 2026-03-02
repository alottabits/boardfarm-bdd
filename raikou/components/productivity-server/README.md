# Productivity Server Component

**Version:** productivity_server_0.01  
**Maintainer:** rjvisser@alottabits.com

North-side Mock SaaS server. Separate container enables L7 path steering: productivity traffic can be routed via a different WAN path than streaming traffic.

**Networking:** Test traffic via Raikou OVS: eth1 (north-segment 172.16.0.10).

**Reference:** `docs/Application_Services_Implementation_Plan.md §3.1`, `docs/WAN_Edge_Appliance_testing.md §4.2`

## Phase 1: Productivity

- **index.html** — Minimal SPA for Page Load Time measurement
- **large_asset.js** — 2MB dummy asset for throughput measurement
- **/api/latency** — JSON endpoint reflecting request timestamp (Application Response Time)
- **Port:** 8080 (host 18080)
- **SSH:** Port 5005 (password: boardfarm)

## Build

```bash
cd raikou
docker build -t productivity-server:productivity_server_0.01 -f components/productivity-server/Dockerfile components/productivity-server
```

## Usage

Requires Raikou to inject eth1 (north-segment). Use with `docker-compose-sdwan.yaml`:

```bash
docker compose -p boardfarm-bdd-sdwan -f docker-compose-sdwan.yaml up -d
```

**Productivity URL:** `http://172.16.0.10:8080/` (from lan-client via DUT)
