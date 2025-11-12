#!/bin/sh
# Script to populate HWMACADDRESS and MANUFACTUREROUI in /var/etc/environment
# This runs after the container is fully booted and interfaces are available
# PrplOS generates /var/etc/environment, but HWMACADDRESS needs to be updated
# from eth1 MAC address (set by Raikou from config.json)
#
# Note: PrplOS generates /var/etc/environment with all environment variables including
# SOFTWAREVERSION. We only update HWMACADDRESS and MANUFACTUREROUI here to match the
# container's eth1 MAC address, which reflects real-world behavior where these values
# come from hardware.

# Wait for eth1 interface to be available (added by Raikou)
TIMEOUT=120
ELAPSED=0

while [ $ELAPSED -lt $TIMEOUT ]; do
    if [ -f /sys/class/net/eth1/address ]; then
        # Read MAC address from eth1 (set by Raikou from config.json)
        ETH1_MAC=$(cat /sys/class/net/eth1/address 2>/dev/null || echo "")
        if [ -n "$ETH1_MAC" ]; then
            # Extract OUI (first 6 hex digits, uppercase, no colons)
            # MAC format: c2:68:68:c9:bc:ae -> OUI: C26868
            OUI=$(echo "$ETH1_MAC" | tr -d ':' | cut -c1-6 | tr '[:lower:]' '[:upper:]')
            
            # Update HWMACADDRESS and MANUFACTUREROUI in /var/etc/environment
            if grep -q "^export HWMACADDRESS=" /var/etc/environment 2>/dev/null; then
                sed -i "s|^export HWMACADDRESS=.*|export HWMACADDRESS=\"$ETH1_MAC\"|" /var/etc/environment
            else
                echo "export HWMACADDRESS=\"$ETH1_MAC\"" >> /var/etc/environment
            fi
            
            if grep -q "^export MANUFACTUREROUI=" /var/etc/environment 2>/dev/null; then
                sed -i "s|^export MANUFACTUREROUI=.*|export MANUFACTUREROUI=\"$OUI\"|" /var/etc/environment
            else
                echo "export MANUFACTUREROUI=\"$OUI\"" >> /var/etc/environment
            fi
            
            echo "Set HWMACADDRESS=$ETH1_MAC and MANUFACTUREROUI=$OUI in /var/etc/environment"
            
            # Configure eth1 as WAN interface with DHCP in UCI network config
            # PrplOS netifd needs UCI configuration to know eth1 should use DHCP
            # This is needed because eth1 is added dynamically by Raikou after netifd starts
            if command -v uci >/dev/null 2>&1; then
                echo "Configuring eth1 as WAN interface with DHCP..."
                # Check if wan interface already exists
                if ! uci get network.wan >/dev/null 2>&1; then
                    # Add wan interface configuration
                    uci set network.wan=interface
                    uci set network.wan.device='eth1'
                    uci set network.wan.proto='dhcp'
                    uci commit network
                    echo "Added WAN interface configuration for eth1"
                else
                    # Update existing wan interface to use eth1 if needed
                    current_device=$(uci get network.wan.device 2>/dev/null || echo "")
                    if [ "$current_device" != "eth1" ]; then
                        uci set network.wan.device='eth1'
                        uci commit network
                        echo "Updated WAN interface to use eth1"
                    fi
                fi
                
                # Trigger network reload to apply configuration
                if [ -f /etc/init.d/network ]; then
                    echo "Triggering network service to apply WAN configuration..."
                    /etc/init.d/network reload 2>/dev/null || /etc/init.d/network restart 2>/dev/null || true
                fi
            else
                echo "Warning: uci command not found, cannot configure network interface"
            fi
            
            exit 0
        fi
    fi
    sleep 2
    ELAPSED=$((ELAPSED + 2))
done

echo "Warning: eth1 interface not available after ${TIMEOUT}s, HWMACADDRESS not set"
exit 1
