# Productivity Server — Mock SaaS (index.html, large_asset.js, /api/latency)
# Test traffic via Raikou OVS: eth1 (north-segment) only.
# Separate container enables L7 path steering: productivity vs streaming via different WAN paths.
#
# See: docs/Application_Services_Implementation_Plan.md §3.1
# See: docs/WAN_Edge_Appliance_testing.md §4.2

FROM nginx:alpine

LABEL maintainer="rjvisser@alottabits.com"
LABEL version="productivity_server_0.01"

EXPOSE 22 8080

WORKDIR /root

COPY ./resources/nginx.conf /etc/nginx/nginx.conf
COPY ./resources/default.conf /etc/nginx/conf.d/default.conf
COPY ./resources/html /usr/share/nginx/html
COPY ./resources/api /usr/share/nginx/api
COPY ./resources/init /root/init

# hadolint ignore=DL3018
RUN apk add --no-cache \
    openssh-server \
    fcgiwrap \
    spawn-fcgi \
    python3 \
    && mkdir -p /run/sshd /var/run/fcgiwrap \
    && chmod 755 /run/sshd \
    && chmod +x /root/init \
    && chmod +x /usr/share/nginx/api/latency.cgi \
    && echo "root:boardfarm" | chpasswd \
    && sed -i 's/^#*PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config \
    && sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config \
    && ssh-keygen -A \
    && (echo -n '/*'; dd if=/dev/zero bs=1M count=2 2>/dev/null | tr '\0' ' '; echo '*/') > /usr/share/nginx/html/large_asset.js

CMD ["/bin/sh", "/root/init"]
