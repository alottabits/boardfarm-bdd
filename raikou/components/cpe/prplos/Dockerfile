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

# Build static unsquashfs using Alpine (musl-based) so it works on PrplOS
# PrplOS doesn't have squashfs-tools via opkg, so we build a static binary
# Must include XZ compression support as PrplOS uses xz-compressed SquashFS
FROM alpine:latest AS unsquashfs-builder

RUN apk add --no-cache \
    build-base \
    zlib-dev \
    zlib-static \
    xz-dev \
    xz-static \
    wget && \
    cd /tmp && \
    # Use version 4.6 (4.7 may not exist, verify URL)
    wget -q https://github.com/plougher/squashfs-tools/archive/4.6.tar.gz -O squashfs-tools.tar.gz && \
    tar xzf squashfs-tools.tar.gz && \
    cd squashfs-tools-4.6/squashfs-tools && \
    # Enable XZ support - this is critical for PrplOS xz-compressed images
    # XZ_SUPPORT enables XZ format (LZMA2 compression)
    sed -i 's/^#XZ_SUPPORT = 1/XZ_SUPPORT = 1/' Makefile && \
    # Also enable LZMA_XZ_SUPPORT for compatibility
    sed -i 's/^#LZMA_XZ_SUPPORT = 1/LZMA_XZ_SUPPORT = 1/' Makefile && \
    # Build static binary with XZ support
    make EXTRA_CFLAGS="-static" EXTRA_LDFLAGS="-static -llzma -lz" unsquashfs && \
    # Verify binary was created
    test -f unsquashfs || (echo "ERROR: unsquashfs binary not created" && exit 1) && \
    cp unsquashfs /usr/bin/unsquashfs.static && \
    chmod +x /usr/bin/unsquashfs.static && \
    # Verify binary exists and is executable
    test -f /usr/bin/unsquashfs.static || (echo "ERROR: unsquashfs.static not created" && exit 1) && \
    # Verify XZ support is compiled in (check version output)
    /usr/bin/unsquashfs.static -version || true

# --- Add containerized upgrade support ---
# Use intermediate stage to set up permissions (FROM scratch can't run commands)
FROM alpine:latest AS setup-stage
# Copy wrapper script and upgrade hook from build context
COPY container-init.sh /usr/local/bin/container-init.sh
COPY z-container-hooks.sh /lib/upgrade/z-container-hooks.sh

# Make scripts executable
RUN chmod +x /usr/local/bin/container-init.sh && \
    chmod +x /lib/upgrade/z-container-hooks.sh

# Final stage: Copy from setup-stage and builder
FROM scratch

COPY --from=builder /root/prplos /

# Copy static unsquashfs binary from Alpine builder (musl-based) for upgrade process
# Static binary built with musl libc works on PrplOS (which also uses musl)
# This binary will be removed after upgrade completes (see container-init.sh)
COPY --from=unsquashfs-builder /usr/bin/unsquashfs.static /usr/bin/unsquashfs

# Copy wrapper script from setup-stage (with proper permissions)
# Wrapper script that applies new rootfs at boot time (uses CMD instead of ENTRYPOINT)
# This avoids Docker lifecycle timing issues with Raikou's dynamic interface attachment
COPY --from=setup-stage /usr/local/bin/container-init.sh /usr/local/bin/container-init.sh

# Copy platform hook that overrides platform_do_upgrade() for containerized upgrades
# The 'z-' prefix ensures it's sourced after platform.sh (alphabetical order)
# This hook intercepts PrplOS upgrade functions to handle containerized upgrade process
COPY --from=setup-stage /lib/upgrade/z-container-hooks.sh /lib/upgrade/z-container-hooks.sh

# Note: set-mac-address.sh script exists but is not installed as an init script.
# PrplOS generates HWMACADDRESS automatically from eth1 during boot, so this script is not needed.
# Note: deduplicate-environment.sh script exists but is not used.
# If /var/etc/environment duplication occurs in regular PrplOS upgrades,
# we should not interfere with PrplOS's normal behavior.
# --- End containerized upgrade support ---

# Use CMD with wrapper script instead of ENTRYPOINT
# This keeps container lifecycle closer to bf_demo and avoids timing issues
# with Raikou's dynamic interface attachment
CMD ["/usr/local/bin/container-init.sh"]
