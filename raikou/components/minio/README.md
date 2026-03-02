# MinIO Content Origin Component

**Version:** content_origin_0.01  
**Maintainer:** rjvisser@alottabits.com

S3-compatible object store for HLS streaming content. Connected to Raikou OVS `content-internal` bridge only — streaming-server reaches it at 10.100.0.2:9000.

**Networking:** eth1 from Raikou OVS (content-internal 10.100.0.2/30). Docker eth0 for management port mapping only.

**Reference:** `docs/Application_Services_Implementation_Plan.md §5`

## Build

```bash
cd raikou
docker build -t minio:content_origin_0.01 -f components/minio/Dockerfile components/minio
```

## Usage

Requires Raikou to inject eth1 (content-internal). Use with `docker-compose-sdwan.yaml`:

```bash
docker compose -p boardfarm-bdd-sdwan -f docker-compose-sdwan.yaml up -d
```

**S3 API (from host):** `http://localhost:19000`  
**Console (from host):** `http://localhost:19001`  
**From streaming-server:** `http://10.100.0.2:9000` (content-internal)
