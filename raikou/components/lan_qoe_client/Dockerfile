# QoE Client — Playwright-based QoE measurement (productivity, streaming, conferencing)
# Test traffic via Raikou OVS: eth1 on lan-segment (192.168.10.10/24). Docker eth0 for SSH/port mapping only.
# Dante SOCKS v5 proxy on port 8080 for developer browser debugging.
#
# See: docs/QoE_Client_Implementation_Plan.md
# See: docs/SDWAN_Testbed_Configuration.md

FROM mcr.microsoft.com/playwright:v1.50.0-jammy

LABEL maintainer="rjvisser@alottabits.com"
LABEL version="qoe_client_0.01"

ENV DEBIAN_FRONTEND=noninteractive
ENV LEGACY=no

WORKDIR /root

COPY ./resources/init /root/init

# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server \
    iperf3 \
    iproute2 \
    dante-server \
    iputils-ping \
    net-tools \
    python3-pip \
    libnss3-tools \
    && rm -rf /var/lib/apt/lists/* \
    && pip3 install --no-cache-dir playwright==1.50.0 \
    && mkdir -p /run/sshd \
    && chmod 755 /run/sshd \
    && chmod +x /root/init \
    && useradd -m -s /bin/bash boardfarm \
    && echo "boardfarm:boardfarm" | chpasswd \
    && echo "root:boardfarm" | chpasswd \
    && sed -i 's/^#*PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config \
    && sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config

# Point the Python playwright package at the browser binaries already present
# in the base image — avoids downloading a second copy of Chromium.
# Written to /etc/environment so SSH login sessions inherit it (Docker ENV is
# only visible to processes started directly by Docker, not by sshd).
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN echo "PLAYWRIGHT_BROWSERS_PATH=/ms-playwright" >> /etc/environment

EXPOSE 22 8080

CMD ["/bin/bash", "/root/init"]
