#!/bin/sh
# Script to populate HWMACADDRESS and MANUFACTUREROUI in /etc/environment
# This runs after the container is fully booted and interfaces are available
# Similar to how VCPE_OFW uses /etc/boot.d/start
# The MAC address is fixed in Raikou config.json, ensuring stability across reboots

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
            
            # Update or add HWMACADDRESS to /etc/environment
            if grep -q "^export HWMACADDRESS=" /etc/environment 2>/dev/null; then
                sed -i "s|^export HWMACADDRESS=.*|export HWMACADDRESS=\"$ETH1_MAC\"|" /etc/environment
            else
                echo "export HWMACADDRESS=\"$ETH1_MAC\"" >> /etc/environment
            fi
            
            # Update or add MANUFACTUREROUI to /etc/environment (derived from MAC)
            if grep -q "^export MANUFACTUREROUI=" /etc/environment 2>/dev/null; then
                sed -i "s|^export MANUFACTUREROUI=.*|export MANUFACTUREROUI=\"$OUI\"|" /etc/environment
            else
                echo "export MANUFACTUREROUI=\"$OUI\"" >> /etc/environment
            fi
            
            echo "Set HWMACADDRESS=$ETH1_MAC and MANUFACTUREROUI=$OUI in /etc/environment"
            
            # Configure eth1 as WAN interface with DHCP in UCI
            # This ensures PrplOS's netifd starts DHCP client on eth1
            # This mimics real-world PrplOS network configuration
            if command -v uci >/dev/null 2>&1; then
                echo "Configuring eth1 as WAN interface with DHCP via UCI..."
                
                # Check if wan interface already exists, create if not
                if ! uci get network.wan >/dev/null 2>&1; then
                    uci set network.wan=interface
                    echo "Created network.wan interface"
                fi
                
                # Configure eth1 as the device for WAN interface
                uci set network.wan.device='eth1'
                
                # Set protocol to DHCP
                uci set network.wan.proto='dhcp'
                
                # Commit the changes
                uci commit network
                
                echo "UCI network configuration committed for eth1 (WAN with DHCP)"
                
                # Reload network configuration to start DHCP client
                # This triggers netifd to read the new config and start DHCP on eth1
                if [ -f /etc/init.d/network ]; then
                    /etc/init.d/network reload 2>/dev/null || {
                        echo "Warning: network reload failed, trying restart..."
                        /etc/init.d/network restart 2>/dev/null || true
                    }
                    echo "Network configuration reloaded, DHCP client should start on eth1"
                else
                    echo "Warning: /etc/init.d/network not found, DHCP may not start automatically"
                fi
            else
                echo "Warning: uci command not found, cannot configure network via UCI"
            fi
        fi
        exit 0
    fi
    sleep 2
    ELAPSED=$((ELAPSED + 2))
done

echo "Warning: eth1 interface not available after ${TIMEOUT}s, HWMACADDRESS not set"

