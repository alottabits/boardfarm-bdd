#!/usr/bin/env bash
# Generate the testbed CA and device certificates used by the SD-WAN
# digital-twin docker-compose stack.
#
# Produces, relative to this script's directory:
#   pki/ca.crt
#   pki/private/ca.key
#   pki/issued/<name>.crt   for dut-strongswan, hub-strongswan,
#   pki/private/<name>.key  app-server, streaming-server, conf-server
#
# These paths are mounted read-only by docker-compose-sdwan.yaml.
#
# Usage:  ./generate-certs.sh [--force]
#   Without --force, exits early if pki/ca.crt already exists.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PKI="$SCRIPT_DIR/pki"

FORCE=0
if [[ "${1:-}" == "--force" ]]; then
    FORCE=1
fi

if [[ -f "$PKI/ca.crt" && $FORCE -eq 0 ]]; then
    echo "CA already present at $PKI/ca.crt — pass --force to regenerate."
    exit 0
fi

command -v openssl >/dev/null || { echo "openssl not found in PATH"; exit 1; }

rm -rf "$PKI"
mkdir -p "$PKI/private" "$PKI/issued" "$PKI/reqs"
chmod 700 "$PKI/private"

CA_DAYS=3650
LEAF_DAYS=825

echo "==> Generating root CA (SD-WAN Testbed CA)"
openssl genrsa -out "$PKI/private/ca.key" 4096 >/dev/null 2>&1
openssl req -x509 -new -nodes \
    -key "$PKI/private/ca.key" \
    -sha256 \
    -days "$CA_DAYS" \
    -subj "/CN=SD-WAN Testbed CA" \
    -out "$PKI/ca.crt"

# gen_leaf <name> <subjectAltName-value>
gen_leaf() {
    local name="$1"
    local san="$2"
    local key="$PKI/private/${name}.key"
    local req="$PKI/reqs/${name}.req"
    local crt="$PKI/issued/${name}.crt"
    local ext
    ext="$(mktemp)"
    trap 'rm -f "$ext"' RETURN

    cat >"$ext" <<EOF
basicConstraints = CA:FALSE
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth, clientAuth
subjectAltName = $san
EOF

    echo "==> Issuing ${name} (SAN: ${san})"
    openssl genrsa -out "$key" 2048 >/dev/null 2>&1
    openssl req -new -key "$key" -subj "/CN=${name}" -out "$req"
    openssl x509 -req \
        -in "$req" \
        -CA "$PKI/ca.crt" \
        -CAkey "$PKI/private/ca.key" \
        -CAcreateserial \
        -out "$crt" \
        -days "$LEAF_DAYS" \
        -sha256 \
        -extfile "$ext"
}

gen_leaf "dut-strongswan"   "DNS:dut.sdwan.testbed"
gen_leaf "hub-strongswan"   "DNS:hub.sdwan.testbed"
gen_leaf "app-server"       "DNS:app-server,IP:172.16.0.10"
gen_leaf "streaming-server" "DNS:streaming-server,IP:172.16.0.11"
gen_leaf "conf-server"      "DNS:conf-server,IP:172.16.0.12"

chmod 600 "$PKI/private/"*.key
rm -f "$PKI/"*.srl

echo
echo "Done. CA at $PKI/ca.crt, 5 device certs under $PKI/issued/."
