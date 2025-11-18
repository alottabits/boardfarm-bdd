#!/bin/sh
# Wrapper script that automatically adds --force flag to sysupgrade
# This ensures test images (which may return valid: false) can be upgraded
# Original sysupgrade is preserved at /sbin/sysupgrade_orig

# Check if --force is already present (avoid duplicate)
case "$*" in
    *--force*)
        # --force already present, call original directly
        exec /sbin/sysupgrade_orig "$@"
        ;;
    *)
        # Add --force flag
        exec /sbin/sysupgrade_orig --force "$@"
        ;;
esac

