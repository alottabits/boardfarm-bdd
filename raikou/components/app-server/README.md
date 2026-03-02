# Application Server Component

**Version:** app_server_0.02  
**Maintainer:** rjvisser@alottabits.com

North-side application server. Productivity (Mock SaaS) on 8080, HLS streaming on 8081.

**Networking:** Test traffic via Raikou OVS: eth1 (north-segment 172.16.0.10), eth2 (content-internal → MinIO).

**Reference:** `docs/Application_Services_Implementation_Plan.md`, `docs/SDWAN_Testbed_Configuration.md`

## Phase 1: Productivity

- **index.html** — Minimal SPA for Page Load Time measurement
- **large_asset.js** — 2MB dummy asset for throughput measurement
- **/api/latency** — JSON endpoint reflecting request timestamp (Application Response Time)
- **Port:** 8080 (host 18080)
- **SSH:** Port 5005 (password: boardfarm)

## Phase 2: Streaming (HLS)

- **Port:** 8081 (host 18081)
- **Proxy:** `/hls/*` → MinIO (10.100.0.2:9000) on content-internal bridge
- **Manifest URL:** `http://172.16.0.10:8081/hls/default/index.m3u8`
- **Content:** Run `ensure_streaming_content.sh` to generate and ingest HLS (FFmpeg + mc)

```bash
# From host, via SSH into app-server:
ssh -p 5005 root@localhost
/root/scripts/ensure_streaming_content.sh default
```

## Build

```bash
cd raikou
docker build -t app-server:app_server_0.02 -f components/app-server/Dockerfile components/app-server
```

## Usage

Requires Raikou to inject eth1 (north-segment) and eth2 (content-internal). Use with `docker-compose-sdwan.yaml` (includes MinIO):

```bash
docker compose -p boardfarm-bdd-sdwan -f docker-compose-sdwan.yaml up -d
```

**Productivity URL:** `http://172.16.0.10:8080/` (from lan-client via DUT)  
**Streaming manifest:** `http://172.16.0.10:8081/hls/default/index.m3u8` (after content ingest)
