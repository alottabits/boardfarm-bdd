# ACS URL Discovery During Testbed Initialization

This document explains how the CPE (Customer Premises Equipment) discovers the ACS (Auto Configuration Server) URL during testbed initialization, with particular focus on the role of the DHCP server.

## Overview

The CPE can discover the ACS URL through **two mechanisms** in the testbed:

1. **DHCP Vendor Options** (Standard TR-069 provisioning) - supported but currently **not actively used**
2. **Direct Configuration by Boardfarm** (Manual/fallback) - **currently the primary mechanism**

---

## 1. DHCP Server Role (Kea Configuration)

The DHCP server (Kea) is **pre-configured** to support ACS URL provisioning via vendor-specific options. The option definitions are in place, but the actual ACS URL value must be dynamically set during testbed initialization.

### Option Definitions

#### DHCPv4 - Option 43 (VSIO) and Option 125 (VIVSO)

From `bf_config/kea_eth_provisioner4.conf`:

```json
"option-def": [
    {
        "code": 1,
        "name": "acs-url",
        "space": "vendor-encapsulated-options-space",
        "type": "binary",
        "array": false
    },
    {
        "code": 2,
        "name": "provisioning-code",
        "space": "vendor-encapsulated-options-space",
        "type": "string",
        "array": false
    },
    {
        "code": 1,
        "name": "acs-url",
        "space": "vendor-3561",
        "type": "binary",
        "array": false
    },
    {
        "code": 2,
        "name": "provisioning-code",
        "space": "vendor-3561",
        "type": "string",
        "array": false
    }
]
```

#### DHCPv6 - Option 17 (Vendor-Specific Information)

From `raikou/config/kea-dhcp6.conf`:

```json
"option-def": [
    {
        "name": "acs-url",
        "code": 1,
        "space": "vendor-3561",
        "type": "binary",
        "array": false
    },
    {
        "name": "provisioning-code",
        "code": 2,
        "space": "vendor-3561",
        "type": "string",
        "array": false
    }
]
```

### Key Identifiers

| Identifier | Value | Description |
|------------|-------|-------------|
| Enterprise ID | 3561 (`0x0de9`) | DSL Forum / Broadband Forum |
| Sub-option code 1 | ACS URL | The TR-069 management server URL |
| Sub-option code 2 | Provisioning Code | Optional provisioning identifier |

---

## 2. CPE-Side DHCP Option Parsing

The raikou CPE containers (Devuan/RDK-B emulation) include scripts that parse DHCP vendor options and extract the ACS URL.

### DHCPv4 - Option 43 Parsing

From `raikou/components/cpe/devuan/rg/udhcpc_vlan.script`:

```bash
if [ -n "$opt43" ]; then
    while [ -n "$opt43" ] ; do
        option_code=$(echo $opt43 | awk '{print substr($0,0,2)}')
        length=$(echo $opt43 | awk '{print substr($0,3,2)}')
        dec_length=$(( 16#$length ))
        dec_length=$((dec_length*2))

        if [ "$option_code" = "01" ] ; then  # Sub-option 1 = ACS URL
            acs_url=$(echo $opt43 | awk '{print substr($0,5,CUR)}' CUR=$dec_length)
            ascii_url=$(hex2string $acs_url)
            sysevent set DHCPv4_ACS_URL "$ascii_url"
            echo "DHCPv4_ACS_URL $ascii_url" >> /tmp/dhcp_acs_url
        fi
        ...
    done
fi
```

### DHCPv6 - Option 17 Parsing

From `raikou/components/cpe/devuan/rg/client-notify.sh`:

```bash
"1")  # Sub-option 1 = ACS URL
    echo "OPT17 for CL_V6OPTION_ACS_SERVER is received: $suboption_data"
    suboption_data=$(echo $suboption_data | sed "s/://g")
    ascii_url=$(hex2string $suboption_data)
    echo "DHCPv6_ACS_URL $ascii_url" >> /tmp/dhcp_acs_url
    sysevent set DHCPv6_ACS_URL "$ascii_url"
;;
```

### Vendor Class Identification

The CPE identifies itself as a DSL Forum device during DHCP:

From `raikou/components/cpe/devuan/rg/vlan_dhcp_service.sh`:
```bash
VENDOR_CLASS_ID="eRouter1.0 dslforum.org"
```

From `raikou/components/cpe/devuan/rg/prepare_dhcpv6_config.sh`:
```bash
# Add Option: Vendor Class (16) with Enterprise ID: 3561 (0x0de9)
# vendor-class-data: dslforum.org
echo "option 0016 hex 0x00000de9000c64736c666f72756d2e6f7267" >> $OPTION_FILE
```

---

## 3. Current Testbed Behavior (Boardfarm Direct Configuration)

**Important**: The current implementation **bypasses the DHCP mechanism** and directly configures the ACS URL on the CPE.

From `boardfarm/boardfarm3/devices/prplos_cpe.py`:

```python
# This part is kept since the x86 version is missing
# implementation to add ACS URL from DHCP vendor options
if acs := device_manager.get_device_by_type(ACS):
    acs_url = acs.config.get("acs_mib", "acs_server.boardfarm.com:7545")
    self.sw.configure_management_server(url=acs_url)
```

### How Direct Configuration Works

For prplOS/OpenWrt devices, the ACS URL is configured via UCI/ubus:

```python
# From boardfarm/boardfarm3/devices/rpiprplos_cpe.py
cmd = f'ubus call bbfdm set \'{{"path": "Device.ManagementServer.URL", "value": "{url}"}}\''
```

The ACS URL is obtained from the inventory configuration:

```json
{
    "acs_mib": "http://172.25.1.40:7547",
    "name": "genieacs",
    "type": "bf_acs"
}
```

---

## 4. The Kea Provisioner's Capabilities

The `KeaProvisioner` class in Boardfarm **can** inject ACS URL via DHCP, but it requires the environment definition to specify the options.

From `boardfarm/boardfarm3/devices/kea_provisioner.py`:

```python
@property
def _supported_vsio_options(self) -> list[DHCPSubOption]:
    """VSIO (Option 43) sub-options."""
    return [
        {"name": "acs-url", "sub-option-code": 1, "data": ""},
        {"name": "provisioning-code", "sub-option-code": 2, "data": ""},
    ]

@property
def _supported_vivso_options(self) -> DHCPVendorOptions:
    """VIVSO (Option 125) with Enterprise ID 3561."""
    return {
        "vendor-id": 3561,  # DSL Forum Enterprise ID
        "sub-options": [
            {"name": "acs-url", "sub-option-code": 1, "data": ""},
            {"name": "provisioning-code", "sub-option-code": 2, "data": ""},
        ],
    }
```

### ACS URL Encoding

The ACS URL is hex-encoded before being sent in DHCP options:

```python
if option["name"] == "acs-url":
    # Encode to binary with space char in case of empty data
    if not option["data"].strip():
        option["data"] = " "
    option["data"] = option["data"].encode().hex()  # URL → hex encoding
```

---

## 5. DHCP-Based ACS Discovery Flow (If Enabled)

If pure DHCP-based ACS discovery were used, the flow would be:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         ACS URL Discovery via DHCP                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  1. Testbed Initialization                                                       │
│     ┌─────────────┐                                                              │
│     │  Boardfarm  │ ──reads──► acs_url from inventory/env config                 │
│     └──────┬──────┘                                                              │
│            │                                                                     │
│            ▼                                                                     │
│  2. DHCP Server Configuration                                                    │
│     ┌─────────────┐                                                              │
│     │ Kea (DHCP)  │ ──configures──► Option 43/125 (v4) or Option 17 (v6)         │
│     │ Provisioner │     with ACS URL encoded as hex in vendor-3561 space         │
│     └──────┬──────┘                                                              │
│            │                                                                     │
│            ▼                                                                     │
│  3. CPE Boot & DHCP Request                                                      │
│     ┌─────────────┐                                                              │
│     │   prplOS    │ ──DHCPDISCOVER/SOLICIT──► Includes Vendor Class ID           │
│     │    CPE      │     "dslforum.org" (triggers vendor option response)         │
│     └──────┬──────┘                                                              │
│            │                                                                     │
│            ▼                                                                     │
│  4. DHCP Response with ACS URL                                                   │
│     ┌─────────────┐                                                              │
│     │ Kea (DHCP)  │ ──DHCPOFFER/ADVERTISE──► IP + Option 43/17 with ACS URL      │
│     │ Provisioner │                                                              │
│     └──────┬──────┘                                                              │
│            │                                                                     │
│            ▼                                                                     │
│  5. CPE Parses DHCP Options                                                      │
│     ┌─────────────┐                                                              │
│     │   prplOS    │ ──udhcpc/dibbler──► Parses vendor options                    │
│     │    CPE      │ ──writes──► /tmp/dhcp_acs_url                                │
│     │             │ ──sysevent──► DHCPv4_ACS_URL or DHCPv6_ACS_URL               │
│     └──────┬──────┘                                                              │
│            │                                                                     │
│            ▼                                                                     │
│  6. TR-069 Client Uses ACS URL                                                   │
│     ┌─────────────┐                                                              │
│     │   icwmpd    │ ──reads──► ACS URL from sysevent/bbfdm                       │
│     │ (TR-069)    │ ──HTTP POST──► Inform message to ACS                         │
│     └─────────────┘                                                              │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Configuration Files Reference

### Inventory Configuration (bf_config/boardfarm_config_*.json)

```json
{
    "provisioner": {
        "acs_url": "http://172.25.1.40:7547",
        "type": "bf_dhcp",
        "vlans": {
            "untagged": {
                "iface": "eth1",
                "ipv4": "10.1.1.0/24",
                "ipv6": "2001:dead:cafe:1::/64"
            }
        }
    },
    "genieacs": {
        "acs_mib": "http://172.25.1.40:7547",
        "type": "bf_acs"
    }
}
```

### Environment Configuration (bf_config/boardfarm_env_*.json)

To enable DHCP-based ACS URL provisioning, specify `dhcp_options` in the environment:

```json
{
    "environment_def": {
        "board": {
            "eRouter_Provisioning_mode": "ipv4"
        },
        "dhcp_options": {
            "dhcpv4": {
                "vivso": {
                    "vendor-id": 3561,
                    "sub-options": [
                        {"name": "acs-url", "sub-option-code": 1, "data": "http://172.25.1.40:7547"}
                    ]
                }
            }
        }
    }
}
```

---

## 7. Summary Comparison

| Aspect | Current Implementation | DHCP-Based (Standard TR-069) |
|--------|----------------------|------------------------------|
| **How ACS URL reaches CPE** | Boardfarm directly writes to `Device.ManagementServer.URL` via `ubus call bbfdm set` | DHCP server sends Option 43/125 (v4) or Option 17 (v6) with encoded ACS URL |
| **DHCP Server Role** | Provides IP, DNS, gateway only | Would also provide ACS URL in vendor options |
| **When it happens** | After CPE boots, during `boardfarm_device_boot()` | During DHCP handshake, before boot completes |
| **Enterprise ID** | N/A | 3561 (DSL Forum/Broadband Forum: `0x0de9`) |
| **Why current approach** | Code comment: "x86 version is missing implementation to add ACS URL from DHCP vendor options" | Would require CPE firmware to properly parse vendor options |

---

## 8. Related Standards

- **TR-069** (CWMP) - CPE WAN Management Protocol
- **TR-181** - Device Data Model for TR-069
- **RFC 2132** - DHCP Options (Option 43: Vendor-Specific Information)
- **RFC 3925** - DHCP Option 125: Vendor-Identifying Vendor Options (VIVSO)
- **RFC 3315** - DHCPv6 Option 17: Vendor-Specific Information

---

## 9. Key Files

| File | Purpose |
|------|---------|
| `boardfarm/boardfarm3/devices/kea_provisioner.py` | DHCP server configuration with vendor options |
| `boardfarm/boardfarm3/devices/rpiprplos_cpe.py` | prplOS CPE with `configure_management_server()` |
| `raikou/components/cpe/devuan/rg/udhcpc_vlan.script` | DHCPv4 Option 43 parsing |
| `raikou/components/cpe/devuan/rg/client-notify.sh` | DHCPv6 Option 17 parsing |
| `raikou/config/kea-dhcp4.conf` | Kea DHCPv4 option definitions |
| `raikou/config/kea-dhcp6.conf` | Kea DHCPv6 option definitions |
| `bf_config/boardfarm_config_*.json` | Testbed inventory with ACS URL |

---

**Document Created**: January 22, 2026  
**Last Updated**: January 22, 2026
