#!/bin/sh
# Script to deduplicate /var/etc/environment after all environment generation scripts
# This runs late in the boot process (S99z) to clean up duplicate entries
# that may have been introduced during containerized upgrade process
#
# Execution order:
# - S12: deviceinfo-environment generates /var/etc/environment
# - S15: environment generates /var/etc/environment (may regenerate or append)
# - S99: set-mac-address updates/append HWMACADDRESS and MANUFACTUREROUI to /var/etc/environment
# - S99z: deduplicate-environment cleans up duplicates (runs after S99set-mac-address alphabetically)
#
# Note: PrplOS generates /var/etc/environment during boot. After upgrades, config restoration
# may restore an old version, then PrplOS regenerates it, causing duplicates.
#
# The script keeps only the LAST occurrence of each export statement,
# preserving the most recent value for each variable (which is what
# scripts sourcing this file would see anyway)

ENV_FILE="/var/etc/environment"
TEMP_FILE="/tmp/environment.dedup"

# Only process if file exists and is readable
if [ ! -f "$ENV_FILE" ] || [ ! -r "$ENV_FILE" ]; then
    exit 0
fi

# Deduplicate: keep only the last occurrence of each export statement
# First pass: identify which line numbers contain the last occurrence of each variable
# Second pass: output lines, skipping earlier duplicates
awk '
BEGIN {
    # First pass: store all lines and track last occurrence of each variable
}
{
    lines[NR] = $0
    # Check if this is an export statement
    if (match($0, /^export ([A-Z_]+)=/, arr)) {
        var = arr[1]
        # Track the line number of the last occurrence
        last_occurrence[var] = NR
    }
}
END {
    # Second pass: output lines, keeping only the last occurrence of each variable
    for (i = 1; i <= NR; i++) {
        line = lines[i]
        # Check if this is an export statement
        if (match(line, /^export ([A-Z_]+)=/, arr)) {
            var = arr[1]
            # Only output if this is the last occurrence of this variable
            if (last_occurrence[var] == i) {
                print line
            }
        } else {
            # Non-export lines: always output
            print line
        }
    }
}' "$ENV_FILE" > "$TEMP_FILE" 2>/dev/null && {
    # Only replace if temp file was created successfully and is different
    if [ -f "$TEMP_FILE" ] && [ -s "$TEMP_FILE" ]; then
        # Check if file actually changed (avoid unnecessary writes)
        if ! cmp -s "$ENV_FILE" "$TEMP_FILE" 2>/dev/null; then
            mv "$TEMP_FILE" "$ENV_FILE"
            echo "Deduplicated /var/etc/environment" >&2
        else
            rm -f "$TEMP_FILE"
        fi
    else
        rm -f "$TEMP_FILE"
    fi
}

exit 0

