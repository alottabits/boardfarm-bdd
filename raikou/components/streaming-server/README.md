# Streaming Server Component

**Version:** streaming_server_0.01  
**Maintainer:** rjvisser@alottabits.com

North-side HLS streaming edge. Proxies /hls/* to MinIO content origin. Separate container enables L7 path steering: streaming traffic can be routed via a different WAN path than productivity traffic.

**Networking:** Test traffic via Raikou OVS: eth1 (north-segment 172.16.0.11), eth2 (content-internal → MinIO).

**Reference:** `docs/Application_Services_Implementation_Plan.md §3.2`, `docs/WAN_Edge_Appliance_testing.md §4.2`

## Phase 2: Streaming (HLS)

- **Port:** 8081 (host 18081)
- **Proxy:** `/hls/*` → MinIO (10.100.0.2:9000) on content-internal bridge
- **Manifest URL:** `http://172.16.0.11:8081/hls/default/index.m3u8`
- **Content:** Run `ensure_streaming_content.sh` to generate and ingest HLS (FFmpeg + mc)

```bash
# From host, via SSH into streaming-server:
ssh -p 5006 root@localhost
/root/scripts/ensure_streaming_content.sh default
```

## Build

```bash
cd raikou
docker build -t streaming-server:streaming_server_0.01 -f components/streaming-server/Dockerfile components/streaming-server
```

## Usage

Requires Raikou to inject eth1 (north-segment) and eth2 (content-internal). Use with `docker-compose-sdwan.yaml` (includes MinIO):

```bash
docker compose -p boardfarm-bdd-sdwan -f docker-compose-sdwan.yaml up -d
```

**Streaming manifest:** `http://172.16.0.11:8081/hls/default/index.m3u8` (after content ingest)
