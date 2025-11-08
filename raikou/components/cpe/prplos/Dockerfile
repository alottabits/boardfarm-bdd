FROM ubuntu:24.04 AS builder

WORKDIR /root

# Downloading the latest release 3.0.2
ARG BUILD_LINK="https://gitlab.com/prpl-foundation/prplos/prplos/-/package_files/120532751/download"

ENV DEBIAN_FRONTEND=noninteractive
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    squashfs-tools \
    fdisk && \
    wget -q ${BUILD_LINK} --no-check-certificate -O image.img && \
    offset=$(sfdisk -d image.img | grep "image.img2" | sed -E 's/.*start=\s+([0-9]+).*/\1/g') && \
    unsquashfs -no-progress -quiet -offset $(( 512 * offset )) -dest "prplos" image.img

FROM scratch

COPY --from=builder /root/prplos /

# --- Add containerized upgrade support ---
# Copy platform hook that overrides platform_do_upgrade() to extract rootfs instead of writing to FLASH
# The 'z-' prefix ensures it's sourced after platform.sh (alphabetical order)
COPY z-container-hooks.sh /lib/upgrade/z-container-hooks.sh

# Copy entrypoint script that applies new rootfs at boot time
COPY docker-entrypoint.sh /docker-entrypoint.sh

# Copy script to populate MAC address after boot (runs via init system)
COPY set-mac-address.sh /etc/init.d/set-mac-address

# Make scripts executable and enable MAC address script via init system
RUN chmod +x /docker-entrypoint.sh && \
    chmod +x /lib/upgrade/z-container-hooks.sh && \
    chmod +x /etc/init.d/set-mac-address && \
    ln -s ../init.d/set-mac-address /etc/rc.d/S99set-mac-address
# --- End containerized upgrade support ---

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["/sbin/init"]
