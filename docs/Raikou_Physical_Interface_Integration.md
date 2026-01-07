# Raikou Physical Interface Integration Guide

This document describes how to integrate a physical OpenWrt Raspberry Pi with the Raikou network orchestrator, replacing the containerized CPE/Router/LAN gateway components.

## Architecture Overview

### Containerized Gateway (PrplOS)

In the standard Raikou setup, the gateway function is provided by **three containers**:
- **CPE** (PrplOS): The home gateway device
- **Router**: ISP router simulation with NAT and routing
- **LAN**: Local network services

```
┌─────────────────────────────────────────────────────────────────┐
│                         rtr-wan (172.25.1.x)                    │
│    ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐              │
│    │  DHCP  │  │  ACS   │  │  WAN   │  │ Router │              │
│    │  .20   │  │  .40   │  │  .2    │  │  .1    │              │
│    └────────┘  └────────┘  └────────┘  └───┬────┘              │
└────────────────────────────────────────────┼───────────────────┘
                                             │ cpe interface
                                    ┌────────┴────────┐
                                    │   cpe-rtr       │
                                    │  (10.1.1.x)     │
                                    └────────┬────────┘
                                             │
                                    ┌────────┴────────┐
                                    │   CPE (PrplOS)  │
                                    │   Container     │
                                    └────────┬────────┘
                                             │
                                    ┌────────┴────────┐
                                    │    lan-cpe      │
                                    └────────┬────────┘
                                             │
                                    ┌────────┴────────┐
                                    │  LAN Container  │
                                    └─────────────────┘
```

### Physical Gateway (OpenWrt RPi)

When using a physical Raspberry Pi with OpenWrt, the **RPi replaces all three gateway containers** (CPE, Router, LAN). The RPi connects directly to the infrastructure:

```
                              Internet
                                  │
                                  ▼ (Host NAT)
                        ┌─────────────────┐
                        │   rtr-uplink    │ (172.25.2.x)
                        │   Host: .254    │
                        └────────┬────────┘
                                 │ aux0 (.1)
                        ┌────────┴────────┐
                        │     Router      │ ← Simplified: routing + NAT only
                        │   Container     │
                        └────────┬────────┘
                                 │ eth1 (.1)
┌────────────────────────────────┼────────────────────────────────┐
│                         rtr-wan (172.25.1.x)                    │
│    ┌────────┐  ┌────────┐  ┌────────┐            ┌────────┐    │
│    │  DHCP  │  │  ACS   │  │  WAN   │            │OpenWrt │    │
│    │  .20   │  │  .40   │  │  .2    │            │  RPi   │    │
│    └────────┘  └────────┘  └────────┘            │ .100+  │    │
│                                                   └───┬────┘    │
└───────────────────────────────────────────────────────┼────────┘
                                                        │ eth1 (WAN)
                                              [USB Dongle: enx00e04c5b7570]
                                                        │
                                              ┌─────────┴─────────┐
                                              │   OpenWrt RPi     │
                                              │  (Physical Device)│
                                              └─────────┬─────────┘
                                                        │ eth0 (LAN)
                                              [USB Dongle: enx00e04c327b58]
                                                        │
                                              ┌─────────┴─────────┐
                                              │      lan-cpe      │
                                              └─────────┬─────────┘
                                                        │
                                              ┌─────────┴─────────┐
                                              │  LAN Phone, etc.  │
                                              └───────────────────┘
```

### Key Differences

| Aspect | Containerized (PrplOS) | Physical (OpenWrt RPi) |
|--------|------------------------|------------------------|
| Gateway device | CPE + Router + LAN containers | Single RPi |
| RPi WAN connection | N/A | Directly on rtr-wan (172.25.1.x) |
| WAN IP source | Router's cpe interface (10.1.1.x) | DHCP container (172.25.1.x) |
| Router container | Full gateway (cpe, eth1, aux0) | Simplified (eth1, aux0 only) |
| cpe-rtr bridge | Required | Not used |

## Configuration

### Raikou Config (`config_openwrt.json`)

```json
{
    "bridge": {
        "lan-cpe": {
            "parents": [
                {"iface": "enx00e04c327b58"}
            ]
        },
        "rtr-uplink": {
            "iprange": "172.25.2.0/24",
            "ipaddress": "172.25.2.254/24"
        },
        "rtr-wan": {
            "parents": [
                {"iface": "enx00e04c5b7570"}
            ]
        }
    },
    "container": {
        "router": [
            {
                "bridge": "rtr-wan",
                "iface": "eth1"
            },
            {
                "bridge": "rtr-uplink",
                "iface": "aux0"
            }
        ],
        "dhcp": [
            {
                "bridge": "rtr-wan",
                "gateway": "172.25.1.1",
                "iface": "eth1",
                "ipaddress": "172.25.1.20/24"
            }
        ],
        ...
    }
}
```

**Key points:**
- `rtr-wan` bridge has the USB dongle for RPi WAN (`enx00e04c5b7570`)
- `lan-cpe` bridge has the USB dongle for RPi LAN (`enx00e04c327b58`)
- `rtr-uplink` has host gateway IP (172.25.2.254) for internet access
- Router container only has `eth1` and `aux0` (no `cpe` interface)
- No `cpe-rtr` bridge needed

### Docker Compose (`docker-compose-openwrt.yaml`)

Router container configuration:

```yaml
router:
    environment:
        - ENABLE_NAT_ON=aux0      # NAT for internet-bound traffic
        - FRR_AUTO_CONF=no        # Disable dynamic routing (not needed)
        - TRIPLE_PLAY=no
    volumes:
        - ./config/staticd.conf:/etc/frr/staticd.conf
```

### Static Routes (`config/staticd.conf`)

```
! Static routes for OpenWrt testbed
! Default route via host gateway on rtr-uplink
ip route 0.0.0.0/0 172.25.2.254
```

### DHCP Configuration (`config/kea-dhcp4.conf`)

The DHCP container serves addresses on rtr-wan (172.25.1.x):

```json
{
    "subnet4": [
        {
            "subnet": "172.25.1.0/24",
            "interface": "eth1",
            "option-data": [
                {"name": "routers", "data": "172.25.1.1"},
                {"name": "domain-name-servers", "data": "172.25.1.2"}
            ],
            "pools": [
                {"pool": "172.25.1.100 - 172.25.1.200"}
            ]
        }
    ]
}
```

## Host Prerequisites

### 1. Prevent NetworkManager from Managing USB Dongles

```bash
sudo tee /etc/NetworkManager/conf.d/99-unmanaged-usb-dongles.conf << 'EOF'
[keyfile]
unmanaged-devices=interface-name:enx00e04c327b58;interface-name:enx00e04c5b7570
EOF

sudo systemctl restart NetworkManager
```

### 2. Install Open vSwitch

```bash
sudo apt install openvswitch-switch openvswitch-common
```

### 3. Internet Access Script (`enable_internet_access.sh`)

```bash
#!/bin/bash
INTERNET_IFACE="${1:-eno1}"
sudo iptables -t nat -A POSTROUTING -s 172.25.2.0/24 -o "$INTERNET_IFACE" -j MASQUERADE
sudo sysctl -w net.ipv4.ip_forward=1
```

## OpenWrt Configuration

### DNS Configuration

OpenWrt needs to use a working DNS server. Configure on OpenWrt:

```bash
uci set network.wan.peerdns='0'
uci add_list network.wan.dns='8.8.8.8'
uci add_list network.wan.dns='8.8.4.4'
uci commit network
/etc/init.d/network restart
```

## Startup Sequence

```bash
cd boardfarm-bdd/raikou

# 1. Start containers
docker compose -f docker-compose-openwrt.yaml up -d

# 2. Wait for orchestrator
sleep 15

# 3. Enable host NAT
./enable_internet_access.sh

# 4. Power on RPi (if not already on)
```

## Verification

### From Host

```bash
# Check OVS bridges
docker exec orchestrator ovs-vsctl show

# Check USB dongles are attached
docker exec orchestrator ovs-vsctl show | grep enx
```

### From Containers

```bash
# Router can reach internet
docker exec router ping -c 2 8.8.8.8

# WAN container can reach internet
docker exec wan ping -c 2 8.8.8.8
```

### From OpenWrt (via serial console)

```bash
# Check WAN IP (should be 172.25.1.x)
ip addr show eth1

# Check gateway (should be 172.25.1.1)
ip route show

# Test internet
ping -c 3 8.8.8.8
ping -c 3 -4 downloads.openwrt.org

# Test package downloads
opkg update
```

## Traffic Flow

```
OpenWrt (172.25.1.100)
    │
    ▼ eth1 (WAN)
    │
[USB Dongle] ─── rtr-wan bridge ─── Router eth1 (172.25.1.1)
                                        │
                                        ▼ [NAT]
                                        │
                                    Router aux0 (172.25.2.1)
                                        │
                        rtr-uplink bridge ─── Host (172.25.2.254)
                                                    │
                                                    ▼ [NAT]
                                                    │
                                                Host eno1 ─── Internet
```

## Interface Mapping

| Host USB Interface | OVS Bridge | Connected To | Network |
|-------------------|------------|--------------|---------|
| `enx00e04c5b7570` | `rtr-wan` | RPi eth1 (WAN) | 172.25.1.x |
| `enx00e04c327b58` | `lan-cpe` | RPi eth0 (LAN) | 192.168.10.x |

## Troubleshooting

### OpenWrt Gets Wrong IP (10.1.1.x instead of 172.25.1.x)

**Cause:** DHCP config still set for old cpe-rtr network

**Fix:** Update `config/kea-dhcp4.conf` to serve 172.25.1.0/24 subnet and restart DHCP container.

### DNS Not Working

**Cause:** WAN container's dnsmasq has `--local-service` flag

**Fix:** Configure OpenWrt to use public DNS directly:
```bash
uci set network.wan.peerdns='0'
uci add_list network.wan.dns='8.8.8.8'
uci commit network
/etc/init.d/network restart
```

### Router Can't Reach Internet

**Cause:** Missing default route or host NAT

**Fix:**
1. Verify `staticd.conf` has `ip route 0.0.0.0/0 172.25.2.254`
2. Run `./enable_internet_access.sh`

### USB Dongles Not Attached to OVS

**Cause:** NetworkManager managing interfaces

**Fix:**
```bash
sudo nmcli device set enx00e04c327b58 managed no
sudo nmcli device set enx00e04c5b7570 managed no
```

## References

- [OpenWrt Implementation Plan](./openwrt_implementation_plan.md)
- [Testbed Network Topology](./Testbed%20Network%20Topology.md)
- [Raikou-Net README](https://github.com/lgirdk/raikou-net)
