# Streaming Server — HLS proxy to MinIO (CDN edge)
# Test traffic via Raikou OVS: eth1 (north-segment), eth2 (content-internal → MinIO).
# Separate container enables L7 path steering: streaming vs productivity via different WAN paths.
#
# See: docs/Application_Services_Implementation_Plan.md §3.2
# See: docs/WAN_Edge_Appliance_testing.md §4.2

FROM nginx:alpine

LABEL maintainer="rjvisser@alottabits.com"
LABEL version="streaming_server_0.01"

EXPOSE 22 8081

WORKDIR /root

COPY ./resources/nginx.conf /etc/nginx/nginx.conf
COPY ./resources/streaming.conf /etc/nginx/conf.d/streaming.conf
COPY ./resources/scripts /root/scripts
COPY ./resources/init /root/init

# hadolint ignore=DL3018
RUN apk add --no-cache \
    openssh-server \
    python3 \
    ffmpeg \
    wget \
    && wget -q -O /usr/local/bin/mc "https://dl.min.io/client/mc/release/linux-amd64/mc" \
    && chmod +x /usr/local/bin/mc \
    && mkdir -p /run/sshd \
    && chmod 755 /run/sshd \
    && chmod +x /root/init \
    && chmod +x /root/scripts/ensure_streaming_content.sh \
    && echo "root:boardfarm" | chpasswd \
    && sed -i 's/^#*PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config \
    && sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config \
    && ssh-keygen -A

CMD ["/bin/sh", "/root/init"]
