#!/bin/bash
#
# Verify Setup - Pre-deployment validation script
#
# This script checks that all prerequisites are met before deploying
# the Tesla Fleet Telemetry stack on HA Test instance.
#
# Usage:
#   ./verify_setup.sh
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
PASS=0
FAIL=0
WARN=0

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}Tesla Fleet Telemetry - Setup Verification${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Helper functions
check_pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASS++))
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    ((FAIL++))
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((WARN++))
}

# Check 1: Docker
echo -e "${BLUE}[1/10]${NC} Checking Docker..."
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version | awk '{print $3}' | tr -d ',')
    check_pass "Docker installed: $DOCKER_VERSION"

    # Check if Docker daemon is running
    if docker ps &> /dev/null; then
        check_pass "Docker daemon is running"
    else
        check_fail "Docker daemon is not running"
        echo "       Start with: sudo systemctl start docker"
    fi
else
    check_fail "Docker not found"
    echo "       Install with: apt-get install -y docker.io"
fi
echo ""

# Check 2: Docker Compose
echo -e "${BLUE}[2/10]${NC} Checking Docker Compose..."
if command -v docker-compose &> /dev/null; then
    COMPOSE_VERSION=$(docker-compose --version | awk '{print $4}' | tr -d ',')
    check_pass "Docker Compose installed: $COMPOSE_VERSION"
elif docker compose version &> /dev/null; then
    COMPOSE_VERSION=$(docker compose version --short)
    check_pass "Docker Compose (plugin) installed: $COMPOSE_VERSION"
else
    check_fail "Docker Compose not found"
    echo "       Install with: apt-get install -y docker-compose"
fi
echo ""

# Check 3: Git
echo -e "${BLUE}[3/10]${NC} Checking Git..."
if command -v git &> /dev/null; then
    GIT_VERSION=$(git --version | awk '{print $3}')
    check_pass "Git installed: $GIT_VERSION"
else
    check_fail "Git not found"
    echo "       Install with: apt-get install -y git"
fi
echo ""

# Check 4: Python 3
echo -e "${BLUE}[4/10]${NC} Checking Python..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    check_pass "Python 3 installed: $PYTHON_VERSION"

    # Check pip3
    if command -v pip3 &> /dev/null; then
        check_pass "pip3 installed"
    else
        check_warn "pip3 not found (may be needed later)"
    fi
else
    check_fail "Python 3 not found"
    echo "       Install with: apt-get install -y python3 python3-pip"
fi
echo ""

# Check 5: Network tools
echo -e "${BLUE}[5/10]${NC} Checking Network tools..."
if command -v nc &> /dev/null || command -v netcat &> /dev/null; then
    check_pass "netcat (nc) installed"
else
    check_warn "netcat not found (useful for debugging)"
    echo "       Install with: apt-get install -y netcat"
fi

if command -v netstat &> /dev/null || command -v ss &> /dev/null; then
    check_pass "netstat/ss installed"
else
    check_warn "netstat/ss not found (useful for debugging)"
    echo "       Install with: apt-get install -y net-tools"
fi
echo ""

# Check 6: Ports availability
echo -e "${BLUE}[6/10]${NC} Checking port availability..."
if command -v netstat &> /dev/null; then
    if netstat -tuln | grep -q ":9092 "; then
        check_warn "Port 9092 (Kafka) is already in use"
        echo "       Stop existing service or use different port"
    else
        check_pass "Port 9092 (Kafka) is available"
    fi

    if netstat -tuln | grep -q ":443 "; then
        check_warn "Port 443 (HTTPS) is already in use"
        echo "       This may conflict with Fleet Telemetry"
    else
        check_pass "Port 443 (HTTPS) is available"
    fi
elif command -v ss &> /dev/null; then
    if ss -tuln | grep -q ":9092 "; then
        check_warn "Port 9092 (Kafka) is already in use"
    else
        check_pass "Port 9092 (Kafka) is available"
    fi

    if ss -tuln | grep -q ":443 "; then
        check_warn "Port 443 (HTTPS) is already in use"
    else
        check_pass "Port 443 (HTTPS) is available"
    fi
else
    check_warn "Cannot check port availability (netstat/ss not found)"
fi
echo ""

# Check 7: Disk space
echo -e "${BLUE}[7/10]${NC} Checking disk space..."
DISK_AVAIL=$(df -h / | awk 'NR==2 {print $4}' | sed 's/G//')
if (( $(echo "$DISK_AVAIL > 10" | bc -l) )); then
    check_pass "Sufficient disk space: ${DISK_AVAIL}G available"
else
    check_warn "Low disk space: ${DISK_AVAIL}G available"
    echo "       Recommend >10GB for Docker images and logs"
fi
echo ""

# Check 8: Memory
echo -e "${BLUE}[8/10]${NC} Checking memory..."
MEM_TOTAL=$(free -m | awk 'NR==2 {print $2}')
MEM_AVAIL=$(free -m | awk 'NR==2 {print $7}')
if [ "$MEM_AVAIL" -gt 2048 ]; then
    check_pass "Sufficient memory: ${MEM_AVAIL}MB available of ${MEM_TOTAL}MB"
else
    check_warn "Low available memory: ${MEM_AVAIL}MB available of ${MEM_TOTAL}MB"
    echo "       Recommend >2GB available for smooth operation"
fi
echo ""

# Check 9: Repository cloned
echo -e "${BLUE}[9/10]${NC} Checking repository..."
if [ -d "/opt/seitor-tesla-telemetry" ]; then
    check_pass "Repository found at /opt/seitor-tesla-telemetry"

    # Check for server directory
    if [ -d "/opt/seitor-tesla-telemetry/server" ]; then
        check_pass "Server directory exists"
    else
        check_fail "Server directory not found"
    fi

    # Check for docker-compose.yml
    if [ -f "/opt/seitor-tesla-telemetry/server/docker-compose.yml" ]; then
        check_pass "docker-compose.yml found"
    else
        check_fail "docker-compose.yml not found"
    fi
else
    check_warn "Repository not found at /opt/seitor-tesla-telemetry"
    echo "       Clone with: git clone https://github.com/jjtortosa/seitor-tesla-telemetry.git /opt/seitor-tesla-telemetry"
fi
echo ""

# Check 10: Home Assistant
echo -e "${BLUE}[10/10]${NC} Checking Home Assistant..."
if docker ps | grep -q homeassistant; then
    check_pass "Home Assistant container is running"

    # Check if we can exec into it
    if docker exec homeassistant echo "test" &> /dev/null; then
        check_pass "Can access Home Assistant container"
    else
        check_warn "Cannot access Home Assistant container"
    fi
else
    check_warn "Home Assistant container not found"
    echo "       Make sure Home Assistant is running on this machine"
fi
echo ""

# Summary
echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}Summary${NC}"
echo -e "${BLUE}================================================${NC}"
echo -e "${GREEN}Passed:${NC}  $PASS"
echo -e "${YELLOW}Warnings:${NC} $WARN"
echo -e "${RED}Failed:${NC}  $FAIL"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}✓ System is ready for deployment!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Clone repository (if not done): git clone https://github.com/jjtortosa/seitor-tesla-telemetry.git /opt/seitor-tesla-telemetry"
    echo "2. Configure SSL certificates: /opt/seitor-tesla-telemetry/server/certs/"
    echo "3. Review configuration: /opt/seitor-tesla-telemetry/server/config.json"
    echo "4. Deploy stack: cd /opt/seitor-tesla-telemetry/server && docker-compose up -d"
    echo "5. Follow testing guide: docs/07_real_world_testing.md"
    exit 0
else
    echo -e "${RED}✗ Please fix the failed checks before proceeding${NC}"
    exit 1
fi
