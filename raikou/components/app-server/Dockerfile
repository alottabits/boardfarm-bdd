# Application Server — Productivity + Streaming + SSH
# Test traffic via Raikou OVS: eth1 (north-segment), eth2 (content-internal → MinIO).
# Phase 1: Productivity on 8080. Phase 2: HLS streaming on 8081 (proxy to MinIO).
#
# See: docs/Application_Services_Implementation_Plan.md
# See: docs/SDWAN_Testbed_Configuration.md

FROM nginx:alpine

LABEL maintainer="rjvisser@alottabits.com"
LABEL version="app_server_0.02"

# Productivity 8080; streaming 8081
EXPOSE 22 8080 8081

WORKDIR /root

COPY ./resources/nginx.conf /etc/nginx/nginx.conf
COPY ./resources/default.conf /etc/nginx/conf.d/default.conf
COPY ./resources/streaming.conf /etc/nginx/conf.d/streaming.conf
COPY ./resources/html /usr/share/nginx/html
COPY ./resources/api /usr/share/nginx/api
COPY ./resources/scripts /root/scripts
COPY ./resources/init /root/init

# hadolint ignore=DL3018
RUN apk add --no-cache \
    openssh-server \
    fcgiwrap \
    spawn-fcgi \
    python3 \
    ffmpeg \
    wget \
    && wget -q -O /usr/local/bin/mc "https://dl.min.io/client/mc/release/linux-amd64/mc" \
    && chmod +x /usr/local/bin/mc \
    && mkdir -p /run/sshd /var/run/fcgiwrap \
    && chmod 755 /run/sshd \
    && chmod +x /root/init \
    && chmod +x /root/scripts/ensure_streaming_content.sh \
    && chmod +x /usr/share/nginx/api/latency.cgi \
    && echo "root:boardfarm" | chpasswd \
    && sed -i 's/^#*PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config \
    && sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config \
    && ssh-keygen -A \
    && (echo -n '/*'; dd if=/dev/zero bs=1M count=2 2>/dev/null | tr '\0' ' '; echo '*/') > /usr/share/nginx/html/large_asset.js

CMD ["/bin/sh", "/root/init"]
