#!/bin/bash
# SSH Service Validation Script
# Validates that ssh_service image is built and SSH is working in dependent containers

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/raikou" || { echo "Error: Could not find raikou directory"; exit 1; }

echo "========================================="
echo "SSH Service Validation"
echo "========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

SUCCESS=0
FAILED=0
WARNINGS=0

# Function to print success
print_success() {
    echo -e "${GREEN}✓${NC} $1"
    ((SUCCESS++))
}

# Function to print failure
print_failure() {
    echo -e "${RED}✗${NC} $1"
    ((FAILED++))
}

# Function to print warning
print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((WARNINGS++))
}

# Check if SSH image exists
echo "1. Checking SSH image..."
if docker images ssh:v1.2.0 2>/dev/null | grep -q "ssh.*v1.2.0"; then
    IMAGE_ID=$(docker images ssh:v1.2.0 --format "{{.ID}}")
    print_success "SSH image built (ID: ${IMAGE_ID:0:12})"
else
    print_failure "SSH image not found"
    echo "   Run: docker compose build ssh_service"
fi
echo ""

# Containers that use SSH (based on docker-compose.yaml)
CONTAINERS=("router" "wan" "lan" "dhcp" "acs" "sipcenter" "lan-phone" "wan-phone")

echo "2. Checking containers and SSH daemons..."
for container in "${CONTAINERS[@]}"; do
    # Check if container is running
    if docker compose ps "$container" 2>/dev/null | grep -q "Up"; then
        # Check if SSH daemon is running inside container
        if docker exec "$container" pgrep -x sshd > /dev/null 2>&1; then
            # Get SSH port from docker-compose.yaml
            PORT=$(docker compose port "$container" 22 2>/dev/null | cut -d: -f2 || echo "N/A")
            print_success "$container: Container running, SSH daemon active (SSH port: $PORT)"
        else
            print_failure "$container: Container running but SSH daemon not found"
        fi
    else
        print_warning "$container: Container not running"
    fi
done || true
echo ""

# Optional: Test SSH connectivity if sshpass is available
if command -v sshpass > /dev/null 2>&1; then
    echo "3. Testing SSH connectivity (with password authentication)..."
    for container in "${CONTAINERS[@]}"; do
        PORT=$(docker compose port "$container" 22 2>/dev/null | cut -d: -f2 || echo "")
        if [ -n "$PORT" ] && [ "$PORT" != "N/A" ]; then
            if sshpass -p 'bigfoot1' timeout 2 ssh -o ConnectTimeout=2 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -p "$PORT" root@localhost exit > /dev/null 2>&1; then
                print_success "$container: SSH connection successful (port $PORT)"
            else
                print_failure "$container: SSH connection failed (port $PORT)"
            fi
        fi
    done || true
    echo ""
else
    echo "3. Skipping SSH connectivity test (sshpass not installed)"
    echo "   Install with: sudo apt-get install sshpass"
    echo ""
fi

# Summary
echo "========================================="
echo "Summary"
echo "========================================="
echo -e "${GREEN}Success:${NC} $SUCCESS"
if [ $FAILED -gt 0 ]; then
    echo -e "${RED}Failed:${NC} $FAILED"
fi
if [ $WARNINGS -gt 0 ]; then
    echo -e "${YELLOW}Warnings:${NC} $WARNINGS"
fi
echo ""

# Exit with appropriate code
if [ $FAILED -gt 0 ]; then
    exit 1
elif [ $WARNINGS -gt 0 ]; then
    exit 0
else
    exit 0
fi

