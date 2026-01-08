#!/bin/bash
# Enable internet access for the OpenWrt testbed
# 
# This script configures NAT on the host to allow testbed containers
# to reach the internet via the rtr-uplink bridge.
#
# Run this AFTER docker-compose up -d
#
# Usage: ./enable_internet_access.sh [internet_interface]
#   internet_interface: Host interface with internet access (default: eno1)

set -e

INTERNET_IFACE="${1:-eno1}"
TESTBED_NETWORK="172.25.2.0/24"

echo "Enabling internet access for testbed..."
echo "  Internet interface: $INTERNET_IFACE"
echo "  Testbed network: $TESTBED_NETWORK"

# Check if the rule already exists
if iptables -t nat -C POSTROUTING -s "$TESTBED_NETWORK" -o "$INTERNET_IFACE" -j MASQUERADE 2>/dev/null; then
    echo "NAT rule already exists, skipping."
else
    # Add MASQUERADE rule for testbed traffic
    sudo iptables -t nat -A POSTROUTING -s "$TESTBED_NETWORK" -o "$INTERNET_IFACE" -j MASQUERADE
    echo "NAT rule added."
fi

# Ensure IP forwarding is enabled
if [ "$(cat /proc/sys/net/ipv4/ip_forward)" != "1" ]; then
    echo "Enabling IP forwarding..."
    sudo sysctl -w net.ipv4.ip_forward=1
fi

# Add FORWARD rules to allow traffic from rtr-uplink to internet interface
# Check if FORWARD rule already exists
if iptables -C FORWARD -i rtr-uplink -o "$INTERNET_IFACE" -j ACCEPT 2>/dev/null; then
    echo "FORWARD rule already exists, skipping."
else
    echo "Adding FORWARD rule for rtr-uplink → $INTERNET_IFACE..."
    sudo iptables -A FORWARD -i rtr-uplink -o "$INTERNET_IFACE" -j ACCEPT
    echo "FORWARD rule added."
fi

# Add reverse FORWARD rule for return traffic
if iptables -C FORWARD -i "$INTERNET_IFACE" -o rtr-uplink -j ACCEPT 2>/dev/null; then
    echo "Reverse FORWARD rule already exists, skipping."
else
    echo "Adding reverse FORWARD rule for $INTERNET_IFACE → rtr-uplink..."
    sudo iptables -A FORWARD -i "$INTERNET_IFACE" -o rtr-uplink -j ACCEPT
    echo "Reverse FORWARD rule added."
fi

echo ""
echo "Internet access enabled. Test with:"
echo "  docker exec router ping -c 2 8.8.8.8"
echo "  docker exec wan ping -c 2 8.8.8.8"

