# IPsec Hub — StrongSwan IKEv2 responder (Phase 3.5)
# Stub peer for the LinuxSDWANRouter IKEv2 tunnel.
# Sits on north-segment via Raikou OVS (172.16.0.20/24).
# Reachable from LinuxSDWANRouter via WAN1 TC (10.10.1.2).
#
# See: docs/LinuxSDWANRouter_Implementation_Plan.md §3.4
# See: docs/Testbed_CA_Setup.md §5.4

FROM debian:bookworm-slim

LABEL maintainer="rjvisser@alottabits.com"
LABEL version="ipsec_hub_0.01"

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /root

COPY ./resources/ipsec.conf /root/ipsec.conf
COPY ./resources/ipsec.secrets /root/ipsec.secrets
COPY ./resources/init /root/init

# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends \
    strongswan \
    libcharon-extra-plugins \
    iproute2 \
    iputils-ping \
    procps \
    && rm -rf /var/lib/apt/lists/* \
    && mv /root/ipsec.conf /etc/ipsec.conf \
    && mv /root/ipsec.secrets /etc/ipsec.secrets \
    && chmod 600 /etc/ipsec.secrets \
    && chmod +x /root/init

CMD ["/bin/bash", "/root/init"]
