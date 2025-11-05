FROM debian:stable-slim

LABEL maintainer="saurav.kochar01@infosys.com"
LABEL pjsip-version="2.14"

ENV TIMEOUT="60"
ENV LEGACY="no"
ENV DEBIAN_FRONTEND=noninteractive
ENV DNS_IPv4=""
ENV DNS_IPv6=""

COPY ./utils/init.sh /root/init.sh
COPY ./utils/isolate_docker_iface /usr/bin/isolate_docker_iface

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
WORKDIR /root/

# Configure apt to use archive repositories if this is Buster-based (defensive approach)
# This handles cases where debian:stable-slim might resolve to Buster
RUN if grep -q "buster" /etc/os-release 2>/dev/null; then \
        sed -i 's/deb.debian.org/archive.debian.org/g' /etc/apt/sources.list && \
        sed -i 's/security.debian.org/archive.debian.org/g' /etc/apt/sources.list && \
        echo 'Acquire::Check-Valid-Until "false";' > /etc/apt/apt.conf.d/99no-check-valid-until; \
    fi

# hadolint ignore=DL3008, DL3009
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    iproute2 \
    openssh-server \
    isc-dhcp-client \
    iputils-ping \
    net-tools\
    traceroute \
    dnsutils\
    --reinstall ca-certificates \
    && echo 'root:bigfoot1' | chpasswd \
    && sed -i 's/.*PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config \
    && sed -i 's/.*Gateway Ports.*/GatewayPorts yes/' /etc/ssh/sshd_config \
    && sed -i 's/.*PermitTunnel.*/PermitTunnel yes/' /etc/ssh/sshd_config \
    && mkdir -p /var/run/sshd \
    && chmod +x /root/init.sh \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY ./resources/pjsua_2_14_dev /root/pjsua
COPY ./resources/dhclient-script /sbin/dhclient-script
COPY ./resources/dhclient.conf /etc/dhcp/dhclient.conf

ENV PATH="/root:${PATH}"

CMD [ "/root/init.sh" ]
