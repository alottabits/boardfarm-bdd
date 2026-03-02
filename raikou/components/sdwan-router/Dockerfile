# SD-WAN Router — Dual WAN with FRR BFD failover
# Extends the router pattern (FRR + SSH) for SD-WAN testbed DUT.
# Uses Raikou-injected interfaces: eth-lan, eth-wan1, eth-wan2 (network_mode: none).
#
# See: docs/LinuxSDWANRouter_Implementation_Plan.md
# See: docs/SDWAN_Testbed_Configuration.md

FROM ssh:v1.2.0

LABEL maintainer="rjvisser@alottabits.com"
LABEL version="sdwan_frr_0.01"

ENV LEGACY="no"
ENV DEBIAN_FRONTEND=noninteractive
ENV PATH=/sbin:/bin:/usr/sbin:/usr/bin:/usr/local/sbin

# Interface names (Raikou config_sdwan.json); overridable via env
ENV LAN_IFACE=eth-lan
ENV WAN1_IFACE=eth-wan1
ENV WAN2_IFACE=eth-wan2

WORKDIR /root

COPY ./resources/frr.conf .
COPY ./resources/daemons .
COPY ./resources/init .

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    gnupg \
    lsb-release \
    && \
    curl -s https://deb.frrouting.org/frr/keys.gpg | tee \
        /usr/share/keyrings/frrouting.gpg > /dev/null \
    && \
    echo deb "[signed-by=/usr/share/keyrings/frrouting.gpg]" \
        https://deb.frrouting.org/frr "$(lsb_release -s -c)" frr-stable | tee \
        -a /etc/apt/sources.list.d/frr.list \
    && \
    apt-get update && apt-get install -y --no-install-recommends \
    dnsutils \
    iproute2 \
    iptables \
    iputils-ping \
    net-tools \
    frr \
    frr-pythontools \
    tcpdump \
    traceroute \
    procps \
    && \
    echo VTYSH_PAGER=more >> /etc/environment \
    && \
    echo "net.ipv4.ip_forward = 1" >> /etc/sysctl.conf \
    && echo "net.ipv4.conf.all.forwarding = 1" >> /etc/sysctl.conf \
    && echo "net.ipv4.conf.default.forwarding = 1" >> /etc/sysctl.conf \
    && echo "net.ipv4.conf.all.rp_filter = 0" >> /etc/sysctl.conf \
    && \
    apt-get purge -y curl ca-certificates gnupg lsb-release \
    && apt-get -y autoremove \
    && rm -rf /var/lib/apt/lists/* \
    && \
    mv /root/frr.conf /etc/frr/frr.conf \
    && mv /root/daemons /etc/frr/daemons \
    && chown -R frr:frr /etc/frr \
    && chmod +x init \
    && echo "root:boardfarm" | chpasswd

EXPOSE 22

ENTRYPOINT ["/root/init"]
