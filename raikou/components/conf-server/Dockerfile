# Conferencing Server — pion WebRTC Echo (Phase 3.5)
# Synthetic conferencing endpoint: negotiates a real WebRTC peer connection
# and echoes the media stream back for QoE measurement via getStats().
#
# Test traffic via Raikou OVS: eth1 (north-segment, 172.16.0.12/24).
# Signalling: WSS on port 8443 (TLS via testbed CA certs at /certs/).
# ICE: host candidate only — PION_PUBLIC_IP suppresses management-network candidates.
#
# See: docs/Application_Services_Implementation_Plan.md §3.3
# See: docs/Testbed_CA_Setup.md §5.2

FROM golang:1.22-alpine AS builder

WORKDIR /build
COPY ./resources/main.go .
COPY ./resources/go.mod .
COPY ./resources/go.sum .
RUN go mod download && CGO_ENABLED=0 go build -o /pion-echo main.go

FROM alpine:3.20

LABEL maintainer="rjvisser@alottabits.com"
LABEL version="conf_server_0.01"

EXPOSE 22 8443/tcp 8443/udp

WORKDIR /root

COPY --from=builder /pion-echo /usr/local/bin/pion-echo
COPY ./resources/init /root/init

# hadolint ignore=DL3018
RUN apk add --no-cache \
    openssh-server \
    iproute2 \
    && mkdir -p /run/sshd \
    && chmod 755 /run/sshd \
    && chmod +x /root/init \
    && echo "root:boardfarm" | chpasswd \
    && sed -i 's/^#*PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config \
    && sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config \
    && ssh-keygen -A

CMD ["/bin/sh", "/root/init"]
