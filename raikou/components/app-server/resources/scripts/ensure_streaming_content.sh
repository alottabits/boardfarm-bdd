#!/bin/sh
#
# Ensure HLS streaming content is available in MinIO.
# Idempotent: if content exists, returns immediately.
# Called by Boardfarm ensure_content_available() or manually for debugging.
#
# Usage: ensure_streaming_content.sh [video_id]
# Default video_id: default
#
set -e

VIDEO_ID="${1:-default}"
MINIO_ALIAS="testbed"
# Raikou OVS content-internal — NOT Docker network
MINIO_ENDPOINT="http://10.100.0.2:9000"
BUCKET="streaming-content"
CONTENT_ROOT="/tmp/streaming/${VIDEO_ID}"

# Check if we can reach MinIO (eth2 must be up)
if ! wget -q -O /dev/null --timeout=5 "${MINIO_ENDPOINT}/minio/health/live" 2>/dev/null; then
    echo "MinIO not reachable at ${MINIO_ENDPOINT} (is eth2/content-internal up?)"
    exit 1
fi

# Configure mc alias (idempotent)
mc alias set "${MINIO_ALIAS}" "${MINIO_ENDPOINT}" testbed testbed-secret 2>/dev/null || true

# Create bucket if not exists
mc mb --ignore-existing "${MINIO_ALIAS}/${BUCKET}" 2>/dev/null || true

# Set anonymous download for HLS (allows nginx proxy without auth)
mc anonymous set download "${MINIO_ALIAS}/${BUCKET}" 2>/dev/null || true

# Check if content already exists
if mc ls "${MINIO_ALIAS}/${BUCKET}/${VIDEO_ID}/" 2>/dev/null | grep -q "360p"; then
    echo "Content ${VIDEO_ID} already in MinIO"
    exit 0
fi

# Generate HLS content with FFmpeg (three profiles: 360p, 720p, 1080p)
mkdir -p "${CONTENT_ROOT}/360p" "${CONTENT_ROOT}/720p" "${CONTENT_ROOT}/1080p"

echo "Generating HLS content for ${VIDEO_ID}..."
for res in "360p:640:360:400k" "720p:1280:720:1500k" "1080p:1920:1080:4000k"; do
    name="${res%%:*}"
    rest="${res#*:}"
    w="${rest%%:*}"
    rest="${rest#*:}"
    h="${rest%%:*}"
    br="${rest#*:}"
    ffmpeg -y -f lavfi -i "testsrc2=size=1920x1080:rate=25" -t 60 \
        -vf "scale=${w}:${h}" -b:v "${br}" -hls_time 6 -hls_list_size 0 \
        -hls_segment_filename "${CONTENT_ROOT}/${name}/seg%03d.ts" \
        -f hls "${CONTENT_ROOT}/${name}/index.m3u8" 2>/dev/null
done

# Create master playlist
cat > "${CONTENT_ROOT}/index.m3u8" << 'MASTER'
#EXTM3U
#EXT-X-VERSION:3
#EXT-X-STREAM-INF:BANDWIDTH=400000,RESOLUTION=640x360
360p/index.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=1500000,RESOLUTION=1280x720
720p/index.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=4000000,RESOLUTION=1920x1080
1080p/index.m3u8
MASTER

# Ingest to MinIO
echo "Ingesting to MinIO..."
mc cp --recursive "${CONTENT_ROOT}/" "${MINIO_ALIAS}/${BUCKET}/${VIDEO_ID}/"

echo "Content ${VIDEO_ID} ready. Manifest: http://172.16.0.10:8081/hls/${VIDEO_ID}/index.m3u8"
