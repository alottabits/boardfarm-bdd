# Build Stage for bind.so
FROM node:18-buster AS bind-build-stage

# Configure apt to use archive repositories for Debian Buster
# Replace sources.list with archive repositories and disable Valid-Until check
RUN echo "deb http://archive.debian.org/debian buster main" > /etc/apt/sources.list && \
    echo "deb http://archive.debian.org/debian buster-updates main" >> /etc/apt/sources.list && \
    echo "deb http://archive.debian.org/debian-security buster/updates main" >> /etc/apt/sources.list && \
    echo 'Acquire::Check-Valid-Until "false";' > /etc/apt/apt.conf.d/99no-check-valid-until

# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

RUN wget -q http://daniel-lange.com/software/bind.c -O bind.c \
    && sed -i '/#include <errno.h>/a #include <arpa\/inet.h>' bind.c \
    && gcc -nostartfiles -fpic -shared bind.c -o bind.so -ldl -D_GNU_SOURCE \
    && strip bind.so


# Final Stage
FROM drumsergio/genieacs:1.2.9

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN echo "root:bigfoot1" | chpasswd

RUN mkdir /var/log/ssh

# Configure apt to use archive repositories if this is Buster-based (defensive approach)
RUN sed -i 's/deb.debian.org/archive.debian.org/g' /etc/apt/sources.list 2>/dev/null || true && \
    sed -i 's/security.debian.org/archive.debian.org/g' /etc/apt/sources.list 2>/dev/null || true && \
    echo 'Acquire::Check-Valid-Until "false";' > /etc/apt/apt.conf.d/99no-check-valid-until

# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server \
    iproute2 \
    sudo \
    supervisor \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir /var/run/sshd \
    && sed -i 's/.*PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config \
    && sed -i 's/.*GatewayPorts.*/GatewayPorts yes/' /etc/ssh/sshd_config \
    && sed -i 's/.*PermitTunnel.*/PermitTunnel yes/' /etc/ssh/sshd_config

ENV LEGACY="no"
ENV TIMEOUT 60

COPY --from=bind-build-stage /root/bind.so /usr/lib/

COPY isolate_docker_iface /usr/bin/

COPY ./init /root/init

EXPOSE 22/tcp

ENTRYPOINT ["/bin/bash","/root/init"]
