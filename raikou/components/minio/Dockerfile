# MinIO — S3-compatible content origin for HLS streaming
# Raikou OVS injects eth1 (content-internal 10.100.0.2). Init configures it before starting MinIO.
# All connectivity via Raikou OVS; Docker ports 19000/19001 for host management only.
#
# See: docs/Application_Services_Implementation_Plan.md §5

FROM alpine:3.19

RUN apk add --no-cache iproute2 wget ca-certificates \
    && wget -q -O /usr/local/bin/minio "https://dl.min.io/server/minio/release/linux-amd64/minio" \
    && chmod +x /usr/local/bin/minio

COPY ./resources/init /minio-init
RUN chmod +x /minio-init

ENV MINIO_ROOT_USER=testbed
ENV MINIO_ROOT_PASSWORD=testbed-secret

EXPOSE 9000 9001

ENTRYPOINT ["/minio-init"]
