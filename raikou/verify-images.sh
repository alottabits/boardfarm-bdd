#!/bin/bash
# Docker Compose Image Verification Script
# Verifies that containers are using the intended pre-built images

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || { echo "Error: Could not change to script directory"; exit 1; }

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

# Function to print info
print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Function to normalize image ID (remove sha256: prefix, get short ID)
normalize_image_id() {
    local id="$1"
    # Remove sha256: prefix if present
    id="${id#sha256:}"
    # Return first 12 characters (short ID)
    echo "${id:0:12}"
}

# Function to get project name from docker-compose.yaml
get_project_name() {
    if [ -f "docker-compose.yaml" ]; then
        # Try to extract name from docker-compose.yaml
        local name=$(grep -E "^name:" docker-compose.yaml 2>/dev/null | head -n1 | sed 's/^name:[[:space:]]*//' | tr -d '"' || echo "")
        if [ -n "$name" ]; then
            echo "$name"
            return
        fi
    fi
    # Fallback: use directory name or COMPOSE_PROJECT_NAME env var
    echo "${COMPOSE_PROJECT_NAME:-boardfarm-bdd}"
}

echo "========================================="
echo "Docker Compose Image Verification"
echo "========================================="
echo ""

# Get project name
PROJECT_NAME=$(get_project_name)
print_info "Project name: $PROJECT_NAME"
echo ""

# Check if docker-compose.yaml exists
if [ ! -f "docker-compose.yaml" ]; then
    print_failure "docker-compose.yaml not found in current directory"
    exit 1
fi

# Extract expected images from docker-compose.yaml
echo "1. Extracting expected images from docker-compose.yaml..."
declare -A EXPECTED_IMAGES

# Services with build tags
EXPECTED_IMAGES[ssh_service]="ssh:v1.2.0"
EXPECTED_IMAGES[router]="router:v1.2.0"
EXPECTED_IMAGES[wan]="wan:v1.2.0"
EXPECTED_IMAGES[lan]="lan:v1.2.0"
EXPECTED_IMAGES[dhcp]="dhcp:v1.2.0"
EXPECTED_IMAGES[acs]="acs:v1.2.0"
EXPECTED_IMAGES[cpe]="cpe:v1.2.0"
EXPECTED_IMAGES[sipcenter]="sip:v1.2.0"
EXPECTED_IMAGES[lan-phone]="phone:v1.2.0"
EXPECTED_IMAGES[wan-phone]="phone:v1.2.0"

# Services with explicit images
EXPECTED_IMAGES[mongo]="mongo:4.4"
EXPECTED_IMAGES[raikou-net]="ghcr.io/ketantewari/raikou/orchestrator:v1"

print_success "Found $((${#EXPECTED_IMAGES[@]})) services to verify"
echo ""

# Check if images exist locally
echo "2. Checking if images exist locally..."
for service in "${!EXPECTED_IMAGES[@]}"; do
    image="${EXPECTED_IMAGES[$service]}"
    if docker images "$image" --format "{{.Repository}}:{{.Tag}}" 2>/dev/null | grep -q "^${image}$" 2>/dev/null; then
        IMAGE_ID=$(docker images "$image" --format "{{.ID}}" 2>/dev/null | head -n1 || echo "unknown")
        CREATED=$(docker images "$image" --format "{{.CreatedAt}}" 2>/dev/null | head -n1 || echo "unknown")
        print_success "$service: Image '$image' exists (ID: ${IMAGE_ID:0:12}, Created: $CREATED)"
    else
        print_warning "$service: Image '$image' not found locally (will be built/pulled)"
    fi
done || true
echo ""

# Check running containers
echo "3. Verifying running containers..."
if ! docker compose ps --format json 2>/dev/null | grep -q "." 2>/dev/null; then
    print_warning "No containers are currently running"
    echo "   Run: docker compose up -d"
    echo ""
else
    for service in "${!EXPECTED_IMAGES[@]}"; do
        expected_image="${EXPECTED_IMAGES[$service]}"
        
        # Get container name (some services have container_name, others use service name)
        container_name=""
        # Special case: raikou-net service uses container name "orchestrator"
        if [ "$service" = "raikou-net" ]; then
            if docker ps --format "{{.Names}}" 2>/dev/null | grep -q "^orchestrator$" 2>/dev/null; then
                container_name="orchestrator"
            fi
        fi
        # Try service name match
        if [ -z "$container_name" ] && docker ps --format "{{.Names}}" 2>/dev/null | grep -q "^${service}$" 2>/dev/null; then
            container_name="$service"
        fi
        # Try partial match
        if [ -z "$container_name" ] && docker ps --format "{{.Names}}" 2>/dev/null | grep -q "${service}" 2>/dev/null; then
            container_name=$(docker ps --format "{{.Names}}" 2>/dev/null | grep "${service}" 2>/dev/null | head -n1 || echo "")
        fi
        
        if [ -z "$container_name" ]; then
            print_warning "$service: Container not running"
            continue
        fi
        
        # Get actual image used by container
        actual_image=$(docker inspect "$container_name" --format '{{.Config.Image}}' 2>/dev/null || echo "")
        actual_image_id=$(docker inspect "$container_name" --format '{{.Image}}' 2>/dev/null || echo "")
        created=$(docker inspect "$container_name" --format '{{.Created}}' 2>/dev/null || echo "")
        
        if [ -z "$actual_image" ] || [ -z "$actual_image_id" ]; then
            print_failure "$service: Could not inspect container '$container_name'"
            continue
        fi
        
        # Normalize image IDs for comparison
        actual_id_normalized=$(normalize_image_id "$actual_image_id")
        
        # Get expected image ID (try multiple naming conventions)
        expected_image_id=""
        
        # Try to get image ID from expected tag first
        expected_image_id=$(docker images "$expected_image" --format "{{.ID}}" 2>/dev/null | head -n1 || echo "")
        
        # If not found, try Docker Compose naming convention with current project name
        if [ -z "$expected_image_id" ]; then
            compose_image="${PROJECT_NAME}-${service}"
            expected_image_id=$(docker images "$compose_image" --format "{{.ID}}" 2>/dev/null | head -n1 || echo "")
        fi
        
        # If still not found, try legacy "raikou-" prefix
        if [ -z "$expected_image_id" ]; then
            compose_image="raikou-${service}"
            expected_image_id=$(docker images "$compose_image" --format "{{.ID}}" 2>/dev/null | head -n1 || echo "")
        fi
        
        # Normalize expected image ID
        expected_id_normalized=""
        if [ -n "$expected_image_id" ]; then
            expected_id_normalized=$(normalize_image_id "$expected_image_id")
        fi
        
        # Compare by normalized image ID (most reliable)
        if [ -n "$expected_id_normalized" ] && [ "$actual_id_normalized" = "$expected_id_normalized" ]; then
            print_success "$service: Container '$container_name' using correct image"
            print_info "      Image: $actual_image (ID: $actual_id_normalized)"
            print_info "      Expected: $expected_image (ID: $expected_id_normalized)"
            print_info "      Created: $(date -d "$created" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || echo "$created")"
        elif [ "$actual_image" = "$expected_image" ] || [[ "$actual_image" == *"$expected_image"* ]]; then
            # Fallback to name matching
            print_success "$service: Container '$container_name' using correct image '$actual_image'"
            print_info "      Image ID: $actual_id_normalized, Created: $(date -d "$created" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || echo "$created")"
        elif [[ "$actual_image" == ${PROJECT_NAME}-* ]] || [[ "$actual_image" == raikou-* ]] || [[ "$actual_image" == bf-demo-* ]]; then
            # Check if project-prefixed image matches expected image ID
            compose_image_id=$(docker images "$actual_image" --format "{{.ID}}" 2>/dev/null | head -n1 || echo "")
            if [ -n "$compose_image_id" ]; then
                compose_id_normalized=$(normalize_image_id "$compose_image_id")
                if [ -n "$expected_id_normalized" ] && [ "$compose_id_normalized" = "$expected_id_normalized" ]; then
                    print_success "$service: Container '$container_name' using correct image (Docker Compose tag)"
                    print_info "      Image: $actual_image (ID: $actual_id_normalized)"
                    print_info "      Expected: $expected_image (ID: $expected_id_normalized)"
                else
                    print_failure "$service: Container '$container_name' using unexpected image"
                    print_info "      Expected: $expected_image (ID: ${expected_id_normalized:-unknown})"
                    print_info "      Actual:   $actual_image (ID: $actual_id_normalized)"
                fi
            else
                print_failure "$service: Container '$container_name' using unexpected image"
                print_info "      Expected: $expected_image"
                print_info "      Actual:   $actual_image (ID: $actual_id_normalized)"
            fi
        else
            print_failure "$service: Container '$container_name' using unexpected image"
            print_info "      Expected: $expected_image"
            print_info "      Actual:   $actual_image (ID: $actual_id_normalized)"
        fi
    done
    echo ""
fi

# Check for containers using wrong images
echo "4. Checking for image mismatches..."
if docker compose ps --format json 2>/dev/null | grep -q "." 2>/dev/null; then
    for service in "${!EXPECTED_IMAGES[@]}"; do
        expected_image="${EXPECTED_IMAGES[$service]}"
        # Special case: raikou-net service uses container name "orchestrator"
        if [ "$service" = "raikou-net" ]; then
            container_name=$(docker ps --format "{{.Names}}" 2>/dev/null | grep -E "^orchestrator$" 2>/dev/null | head -n1 || echo "")
        else
            # Try exact match first to avoid matching wan-phone when looking for wan
            container_name=$(docker ps --format "{{.Names}}" 2>/dev/null | grep -E "^${service}$" 2>/dev/null | head -n1 || echo "")
            # If no exact match, try partial match
            if [ -z "$container_name" ]; then
                container_name=$(docker ps --format "{{.Names}}" 2>/dev/null | grep -E "${service}-" 2>/dev/null | head -n1 || echo "")
            fi
        fi
        
        if [ -n "$container_name" ]; then
            actual_image=$(docker inspect "$container_name" --format '{{.Config.Image}}' 2>/dev/null || echo "")
            actual_image_id=$(docker inspect "$container_name" --format '{{.Image}}' 2>/dev/null || echo "")
            
            # Normalize image IDs for comparison
            actual_id_normalized=$(normalize_image_id "$actual_image_id")
            
            # Get expected image ID (try multiple naming conventions)
            expected_image_id=$(docker images "$expected_image" --format "{{.ID}}" 2>/dev/null | head -n1 || echo "")
            if [ -z "$expected_image_id" ]; then
                compose_image="${PROJECT_NAME}-${service}"
                expected_image_id=$(docker images "$compose_image" --format "{{.ID}}" 2>/dev/null | head -n1 || echo "")
            fi
            if [ -z "$expected_image_id" ]; then
                compose_image="raikou-${service}"
                expected_image_id=$(docker images "$compose_image" --format "{{.ID}}" 2>/dev/null | head -n1 || echo "")
            fi
            
            # Normalize expected image ID
            expected_id_normalized=""
            if [ -n "$expected_image_id" ]; then
                expected_id_normalized=$(normalize_image_id "$expected_image_id")
            fi
            
            # Compare by normalized image ID (most reliable)
            if [ -n "$expected_id_normalized" ] && [ -n "$actual_id_normalized" ] && [ "$actual_id_normalized" != "$expected_id_normalized" ]; then
                print_failure "$service: Image ID mismatch detected!"
                print_info "      Expected: $expected_image (ID: $expected_id_normalized)"
                print_info "      Actual:   $actual_image (ID: $actual_id_normalized)"
            fi
        fi
    done
    echo ""
fi

# Summary table
echo "5. Summary - Container Image Status"
echo "========================================="
printf "%-20s %-30s %-15s\n" "Service" "Expected Image" "Status"
echo "----------------------------------------"
for service in "${!EXPECTED_IMAGES[@]}"; do
    expected_image="${EXPECTED_IMAGES[$service]}"
    # Special case: raikou-net service uses container name "orchestrator"
    if [ "$service" = "raikou-net" ]; then
        container_name=$(docker ps --format "{{.Names}}" 2>/dev/null | grep -E "^orchestrator$" 2>/dev/null | head -n1 || echo "")
    else
        # Try exact match first to avoid matching wan-phone when looking for wan
        container_name=$(docker ps --format "{{.Names}}" 2>/dev/null | grep -E "^${service}$" 2>/dev/null | head -n1 || echo "")
        # If no exact match, try partial match
        if [ -z "$container_name" ]; then
            container_name=$(docker ps --format "{{.Names}}" 2>/dev/null | grep -E "${service}-" 2>/dev/null | head -n1 || echo "")
        fi
    fi
    
    if [ -n "$container_name" ]; then
        actual_image=$(docker inspect "$container_name" --format '{{.Config.Image}}' 2>/dev/null || echo "")
        actual_image_id=$(docker inspect "$container_name" --format '{{.Image}}' 2>/dev/null || echo "")
        
        # Normalize image IDs for comparison
        actual_id_normalized=$(normalize_image_id "$actual_image_id")
        
        # Get expected image ID (try multiple naming conventions)
        expected_image_id=$(docker images "$expected_image" --format "{{.ID}}" 2>/dev/null | head -n1 || echo "")
        if [ -z "$expected_image_id" ]; then
            compose_image="${PROJECT_NAME}-${service}"
            expected_image_id=$(docker images "$compose_image" --format "{{.ID}}" 2>/dev/null | head -n1 || echo "")
        fi
        if [ -z "$expected_image_id" ]; then
            compose_image="raikou-${service}"
            expected_image_id=$(docker images "$compose_image" --format "{{.ID}}" 2>/dev/null | head -n1 || echo "")
        fi
        
        # Normalize expected image ID
        expected_id_normalized=""
        if [ -n "$expected_image_id" ]; then
            expected_id_normalized=$(normalize_image_id "$expected_image_id")
        fi
        
        # Compare by normalized image ID
        if [ -n "$expected_id_normalized" ] && [ -n "$actual_id_normalized" ] && [ "$actual_id_normalized" = "$expected_id_normalized" ]; then
            status="${GREEN}✓ OK${NC}"
        elif [ "$actual_image" = "$expected_image" ] || [[ "$actual_image" == *"$expected_image"* ]]; then
            status="${GREEN}✓ OK${NC}"
        else
            status="${RED}✗ MISMATCH${NC}"
        fi
    else
        status="${YELLOW}⚠ NOT RUNNING${NC}"
    fi
    
    printf "%-20s %-30s %-15s\n" "$service" "$expected_image" "$status"
done || true
echo ""

# Final summary
echo "========================================="
echo "Verification Summary"
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
else
    exit 0
fi

