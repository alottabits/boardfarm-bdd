# Testbed Certificate Authority (CA) Setup

**Date:** February 25, 2026
**Scope:** Phase 3.5 — Digital Twin Hardening (Optional)
**Related:** `WAN_Edge_Appliance_testing.md §4 (Phase 3.5)`, `LinuxSDWANRouter_Implementation_Plan.md §3.4`, `Application_Services_Implementation_Plan.md §6 Phase 3.5`, `QoE_Client_Implementation_Plan.md §5 Phase 3.5`

---

## 1. Overview

Phase 3.5 (Digital Twin Hardening) extends the testbed with:

- **HTTPS** on the Nginx Productivity and Streaming servers
- **HTTP/3 (QUIC)** on the Productivity server (via `Alt-Svc` upgrade)
- **WSS** (WebSocket Secure) on the `conf-server` WebRTC endpoint
- **IKEv2/IPsec** overlay encryption on the DUT (StrongSwan)

All four capabilities require TLS certificates signed by a shared root that all testbed components trust. This document is the **single authoritative procedure** for generating that root CA and all service certificates. All Phase 3.5 PKI references in the component implementation plans point here.

**The CA is generated once per testbed deployment** on the management host and stored in `./testbed-ca/` at the project root. Certificate files are distributed to containers via Docker volume mounts — no container image rebuild is required when certificates are renewed.

> **Security scope:** This CA is for testbed-internal use only. The root certificate is trusted by Playwright/Chromium solely to allow QoE measurement over HTTPS. It must not be trusted by any system outside the testbed.

---

## 2. Certificate Consumers

| Component | Container | Certificate purpose | Subject / SAN |
| :--- | :--- | :--- | :--- |
| Nginx Productivity + Streaming | `app-server` | HTTPS / HTTP/3 server TLS | `DNS:app-server`, `IP:172.16.0.10` |
| pion WebRTC Echo | `conf-server` | WSS (WebSocket Secure) TLS | `DNS:conf-server`, `IP:172.16.0.11` |
| StrongSwan DUT | `linux-sdwan-router` | IKEv2 peer identity | `DNS:dut.sdwan.testbed` |
| StrongSwan Hub (stub peer) | separate container | IKEv2 peer identity | `DNS:hub.sdwan.testbed` |
| Playwright / Chromium | `lan-client` | CA root trust store | CA root cert only — no service cert |

The CA private key (`pki/private/ca.key`) is **never mounted into any container**. Only `ca.crt` and per-service key/cert pairs are distributed.

---

## 3. Prerequisites

**Tool required on the management host:**

```bash
# Ubuntu / Debian
sudo apt-get install easy-rsa

# Verify
easyrsa --version    # expect 3.x
```

**Project directory structure after generation:**

```
./testbed-ca/
└── pki/
    ├── ca.crt                       ← CA root cert — distribute to all trust stores
    ├── private/
    │   ├── ca.key                   ← CA private key — NEVER mount into containers
    │   ├── app-server.key
    │   ├── conf-server.key
    │   ├── dut-strongswan.key
    │   └── hub-strongswan.key
    └── issued/
        ├── app-server.crt
        ├── conf-server.crt
        ├── dut-strongswan.crt
        └── hub-strongswan.crt
```

---

## 4. Step 1 — Generate the Root CA

Run **once** from the project root. The PKI is stored in `./testbed-ca/pki/`.

```bash
mkdir -p testbed-ca && cd testbed-ca

# Initialise the PKI directory structure
easyrsa init-pki

# Generate the CA certificate and key — no passphrase (testbed use only)
EASYRSA_REQ_CN="SD-WAN Testbed CA" easyrsa build-ca nopass
```

The CA certificate is written to `pki/ca.crt`. This file is the only CA artifact distributed to containers and trust stores.

---

## 5. Step 2 — Issue Service Certificates

Each command generates a private key and signs a certificate with the IP and DNS SANs that identify the container on the simulated network. The IPs match `SDWAN_Testbed_Configuration.md §8.2`.

### 5.1 app-server (Nginx — Productivity + Streaming)

```bash
# Generate key and CSR
easyrsa gen-req app-server nopass

# Sign — includes both IP and DNS SANs for flexibility
EASYRSA_SAN="IP:172.16.0.10,DNS:app-server" \
    easyrsa sign-req server app-server
```

| File | Path |
| :--- | :--- |
| Private key | `pki/private/app-server.key` |
| Certificate | `pki/issued/app-server.crt` |

### 5.2 conf-server (pion WebRTC Echo)

```bash
easyrsa gen-req conf-server nopass

EASYRSA_SAN="IP:172.16.0.11,DNS:conf-server" \
    easyrsa sign-req server conf-server
```

| File | Path |
| :--- | :--- |
| Private key | `pki/private/conf-server.key` |
| Certificate | `pki/issued/conf-server.crt` |

### 5.3 DUT — StrongSwan IKEv2

StrongSwan matches peers using the certificate's Subject Alternative Name. The DNS SAN must match the `leftid` / `rightid` values in `/etc/ipsec.conf` (see `LinuxSDWANRouter_Implementation_Plan.md §3.4`).

```bash
easyrsa gen-req dut-strongswan nopass

EASYRSA_SAN="DNS:dut.sdwan.testbed" \
    easyrsa sign-req server dut-strongswan
```

| File | Path |
| :--- | :--- |
| Private key | `pki/private/dut-strongswan.key` |
| Certificate | `pki/issued/dut-strongswan.crt` |

### 5.4 Hub Peer — StrongSwan IKEv2

```bash
easyrsa gen-req hub-strongswan nopass

EASYRSA_SAN="DNS:hub.sdwan.testbed" \
    easyrsa sign-req server hub-strongswan
```

| File | Path |
| :--- | :--- |
| Private key | `pki/private/hub-strongswan.key` |
| Certificate | `pki/issued/hub-strongswan.crt` |

---

## 6. Step 3 — Distribute Certificates via Volume Mounts

Certificate files are mounted read-only into containers at startup. Add the following `volumes` entries to the relevant services in `raikou/docker-compose-sdwan.yaml` when enabling Phase 3.5.

> **Note — HTTPS port mappings:** Enabling TLS on `app-server` and `conf-server` requires adding HTTPS port mappings alongside the HTTP ones. `app-server` gains `443` (HTTPS/HTTP3) and `conf-server`'s existing port `8443` changes from plain WS to WSS. Update the `ports:` blocks in `docker-compose-sdwan.yaml` accordingly.

**`app-server`:**

```yaml
volumes:
    - ./testbed-ca/pki/ca.crt:/certs/ca.crt:ro
    - ./testbed-ca/pki/issued/app-server.crt:/certs/server.crt:ro
    - ./testbed-ca/pki/private/app-server.key:/certs/server.key:ro
```

Referenced in the Nginx config as:

```nginx
listen 443 ssl;
ssl_certificate     /certs/server.crt;
ssl_certificate_key /certs/server.key;
ssl_protocols       TLSv1.3;

# HTTP/3 — requires Nginx ≥ 1.25 built with --with-http_v3_module
listen 443 quic reuseport;
add_header Alt-Svc 'h3=":443"; ma=86400';
```

**`conf-server`:**

```yaml
volumes:
    - ./testbed-ca/pki/ca.crt:/certs/ca.crt:ro
    - ./testbed-ca/pki/issued/conf-server.crt:/certs/server.crt:ro
    - ./testbed-ca/pki/private/conf-server.key:/certs/server.key:ro
```

Pass cert paths to `pion` via environment:

```yaml
environment:
    - PION_CERT_FILE=/certs/server.crt
    - PION_KEY_FILE=/certs/server.key
```

**`linux-sdwan-router` (DUT — StrongSwan):**

```yaml
volumes:
    - ./testbed-ca/pki/ca.crt:/etc/strongswan/certs/ca.crt:ro
    - ./testbed-ca/pki/issued/dut-strongswan.crt:/etc/strongswan/certs/dut.crt:ro
    - ./testbed-ca/pki/private/dut-strongswan.key:/etc/strongswan/private/dut.key:ro
```

Referenced in `/etc/ipsec.conf` as:

```ini
leftcert=/etc/strongswan/certs/dut.crt
```

And in `/etc/strongswan.conf` or `/etc/ipsec.secrets`:

```
: RSA /etc/strongswan/private/dut.key
```

**`lan-client` (CA trust store only):**

```yaml
volumes:
    - ./testbed-ca/pki/ca.crt:/usr/local/share/ca-certificates/testbed-ca.crt:ro
```

---

## 7. Step 4 — Trust the CA in the QoE Client

The `lan-client` container's init script must register the CA root with the system trust store on startup. This makes Playwright/Chromium accept HTTPS connections to `app-server` and WSS connections to `conf-server` without errors.

**In the `lan-client` init script** (add before starting `sshd`):

```bash
# Register testbed CA — required for Playwright/Chromium HTTPS/WSS acceptance
update-ca-certificates
```

The `update-ca-certificates` command reads all `.crt` files in `/usr/local/share/ca-certificates/` (including the mounted `testbed-ca.crt`) and registers them with both the system OpenSSL store and the NSS database used by Chromium.

> **Phase 3.5 note in `QoE_Client_Implementation_Plan.md §5`:** The alternative `--ignore-certificate-errors` Playwright launch flag is documented for reference only. It must **not** be used for Phase 4 security pillar tests, which explicitly validate TLS certificate chain behaviour. Use `update-ca-certificates` for all Phase 3.5+ work.

---

## 8. Verification Commands

Run after `docker compose -p boardfarm-bdd-sdwan -f raikou/docker-compose-sdwan.yaml up` to confirm each consumer has a valid, trusted certificate chain.

### 8.1 Nginx TLS — app-server

```bash
# From inside lan-client — simulates Playwright's exact network path and trust store
docker exec lan-client curl -sv \
    --cacert /usr/local/share/ca-certificates/testbed-ca.crt \
    https://172.16.0.10/
```

Expected: `SSL connection using TLSv1.3`, issuer `SD-WAN Testbed CA`, HTTP 200.

```bash
# Verify HTTP/3 upgrade — check for Alt-Svc header and h3 protocol on second request
docker exec lan-client curl -sv \
    --cacert /usr/local/share/ca-certificates/testbed-ca.crt \
    --http3 https://172.16.0.10/
```

Expected: `HTTP/3 200`.

### 8.2 WebRTC WSS — conf-server

```bash
docker exec lan-client openssl s_client \
    -connect 172.16.0.11:8443 \
    -CAfile /usr/local/share/ca-certificates/testbed-ca.crt \
    </dev/null 2>&1 | grep -E "Verify return code|subject|issuer"
```

Expected: `Verify return code: 0 (ok)`, subject `conf-server`, issuer `SD-WAN Testbed CA`.

### 8.3 StrongSwan IKEv2 — DUT

```bash
# Check tunnel is ESTABLISHED
docker exec linux-sdwan-router ipsec statusall 2>&1 \
    | grep -E "ESTABLISHED|INSTALLED|Security Associations"

# Verify SPD entries (inbound + outbound)
docker exec linux-sdwan-router ip xfrm policy list
```

Expected: `sdwan-overlay[...]: ESTABLISHED`, two SPD entries.

```bash
# End-to-end: encrypted ping from LAN through DUT tunnel to north side
docker exec lan-client ping -c 3 172.16.0.10
```

Expected: 3 replies; `ip xfrm monitor` on DUT shows ESP packet counts incrementing.

### 8.4 QoE Client trust store

```bash
# Confirm the CA root is registered and validates against itself
docker exec lan-client openssl verify \
    -CAfile /usr/local/share/ca-certificates/testbed-ca.crt \
    /usr/local/share/ca-certificates/testbed-ca.crt
```

Expected: `/usr/local/share/ca-certificates/testbed-ca.crt: OK`.

---

## 9. Certificate Renewal

Certificates are issued with easy-rsa's default 825-day validity. To renew before expiry:

```bash
cd testbed-ca

easyrsa renew app-server nopass
easyrsa renew conf-server nopass
easyrsa renew dut-strongswan nopass
easyrsa renew hub-strongswan nopass
```

Then restart the affected containers:

```bash
docker compose -p boardfarm-bdd-sdwan -f raikou/docker-compose-sdwan.yaml restart app-server conf-server linux-sdwan-router
```

No container rebuild is required — the renewed files in `pki/issued/` and `pki/private/` are read from the volume mount on next container startup.

---

## 10. References

This document is referenced by the following Phase 3.5 sections as the PKI prerequisite:

| Document | Section | What it needs from here |
| :--- | :--- | :--- |
| `WAN_Edge_Appliance_testing.md` | §4 Phase 3.5 | "Stand up a lightweight testbed CA" |
| `LinuxSDWANRouter_Implementation_Plan.md` | §3.4 | StrongSwan IKEv2 cert paths and `ipsec.conf` identity values |
| `Application_Services_Implementation_Plan.md` | §6 Phase 3.5 | Nginx TLS cert prerequisite for HTTPS/HTTP3 enablement |
| `QoE_Client_Implementation_Plan.md` | §5 Phase 3.5 | Playwright/Chromium trust store registration |
