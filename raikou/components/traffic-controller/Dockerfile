# Traffic Controller — tc netem WAN impairment
# Interfaces from Raikou OVS (config_sdwan.json), NOT Docker network.
# Dual-homed: eth-dut (dut-wan1/dut-wan2 bridge), eth-north (north-segment bridge).
# Per-direction impairment: Boardfarm applies tc netem on eth-north (forward) and eth-dut (return).
#
# See: docs/Traffic_Management_Components_Architecture.md
# See: docs/SDWAN_Testbed_Configuration.md

FROM ssh:v1.2.0

LABEL maintainer="rjvisser@alottabits.com"
LABEL version="traffic_controller_0.01"

ENV DEBIAN_FRONTEND=noninteractive
ENV LEGACY=no

# Interface names (Raikou config_sdwan.json); overridable via env
ENV TC_DUT_IFACE=eth-dut
ENV TC_NORTH_IFACE=eth-north

WORKDIR /root

COPY ./resources/init /root/init

# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends \
    iproute2 \
    iputils-ping \
    net-tools \
    && rm -rf /var/lib/apt/lists/* \
    && chmod +x /root/init \
    && echo "root:boardfarm" | chpasswd \
    && echo "net.ipv4.ip_forward = 1" >> /etc/sysctl.conf \
    && echo "net.ipv4.conf.all.forwarding = 1" >> /etc/sysctl.conf

EXPOSE 22

CMD ["/bin/bash", "/root/init"]
