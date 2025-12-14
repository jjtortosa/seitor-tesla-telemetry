#!/bin/bash
#
# Tesla Fleet Telemetry Server - Interactive Setup
# This script configures your server for first-time deployment.
#
# Usage: ./setup.sh
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Header
echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     Tesla Fleet Telemetry Server - Interactive Setup         ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  This script will configure your server for deployment.      ║"
echo "║  You will need:                                              ║"
echo "║    - A public domain with DNS configured                     ║"
echo "║    - SSL certificates for your domain                        ║"
echo "║    - Docker and Docker Compose installed                     ║"
echo "║    - MQTT broker (Mosquitto) in Home Assistant               ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed. Please install Docker first.${NC}"
    echo "   https://docs.docker.com/engine/install/"
    exit 1
fi
echo -e "${GREEN}✓ Docker installed${NC}"

# Check Docker Compose
if ! docker compose version &> /dev/null && ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed. Please install Docker Compose first.${NC}"
    echo "   https://docs.docker.com/compose/install/"
    exit 1
fi
echo -e "${GREEN}✓ Docker Compose installed${NC}"

# Check if running as root (needed for port 443)
if [ "$EUID" -ne 0 ] && [ ! -w /var/run/docker.sock ]; then
    echo -e "${YELLOW}⚠ You may need sudo to run Docker or bind to port 443${NC}"
fi

echo ""

# ============================================================
# STEP 1: Domain Configuration
# ============================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Step 1: Domain Configuration${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Enter your domain for Tesla Fleet Telemetry."
echo "This must be a valid domain with DNS pointing to this server."
echo "Example: tesla-telemetry.yourdomain.com"
echo ""

read -p "Domain: " TELEMETRY_DOMAIN

if [ -z "$TELEMETRY_DOMAIN" ]; then
    echo -e "${RED}❌ Domain is required${NC}"
    exit 1
fi

# Validate domain format (basic check)
if ! echo "$TELEMETRY_DOMAIN" | grep -qE '^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*$'; then
    echo -e "${RED}❌ Invalid domain format${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Domain: $TELEMETRY_DOMAIN${NC}"
echo ""

# ============================================================
# STEP 2: MQTT Broker Configuration
# ============================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Step 2: MQTT Broker Configuration${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Enter your Home Assistant MQTT broker details."
echo "This is typically the Mosquitto add-on in Home Assistant."
echo ""

# Try to detect local IP
DETECTED_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || ip route get 1 2>/dev/null | awk '{print $7}' || echo "")
if [ -n "$DETECTED_IP" ]; then
    echo -e "${YELLOW}Detected network IP: $DETECTED_IP${NC}"
fi

read -p "MQTT Broker Host (Home Assistant IP): " MQTT_HOST
if [ -z "$MQTT_HOST" ]; then
    echo -e "${RED}❌ MQTT host is required${NC}"
    exit 1
fi

read -p "MQTT Port [1883]: " MQTT_PORT
MQTT_PORT=${MQTT_PORT:-1883}

read -p "MQTT Username: " MQTT_USERNAME
read -s -p "MQTT Password: " MQTT_PASSWORD
echo ""

if [ -z "$MQTT_USERNAME" ] || [ -z "$MQTT_PASSWORD" ]; then
    echo -e "${YELLOW}⚠ MQTT credentials not set. Make sure anonymous access is enabled.${NC}"
fi

echo -e "${GREEN}✓ MQTT Broker: $MQTT_HOST:$MQTT_PORT${NC}"
echo ""

# ============================================================
# STEP 3: MQTT Topic Configuration
# ============================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Step 3: MQTT Topic Configuration${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "MQTT topic base for telemetry messages."
echo "Topics will be: <base>/<VIN>/v/<field>"
echo ""

read -p "MQTT Topic Base [tesla]: " MQTT_TOPIC_BASE
MQTT_TOPIC_BASE=${MQTT_TOPIC_BASE:-tesla}

echo -e "${GREEN}✓ MQTT Topic Base: $MQTT_TOPIC_BASE${NC}"
echo ""

# ============================================================
# STEP 4: Create Directory Structure
# ============================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Step 4: Creating Directory Structure${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

mkdir -p certs keys logs
chmod 700 keys
chmod 755 certs logs

echo -e "${GREEN}✓ Created directories: certs/, keys/, logs/${NC}"
echo ""

# ============================================================
# STEP 5: Generate Configuration Files
# ============================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Step 5: Generating Configuration Files${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Generate .env file
cat > .env << EOF
# Tesla Fleet Telemetry Server Configuration
# Generated by setup.sh on $(date)

# Domain Configuration
TELEMETRY_DOMAIN=${TELEMETRY_DOMAIN}

# MQTT Configuration
MQTT_HOST=${MQTT_HOST}
MQTT_PORT=${MQTT_PORT}
MQTT_USERNAME=${MQTT_USERNAME}
MQTT_PASSWORD=${MQTT_PASSWORD}
MQTT_TOPIC_BASE=${MQTT_TOPIC_BASE}

# Paths (relative to docker-compose.yml)
CERTS_PATH=./certs
KEYS_PATH=./keys
LOGS_PATH=./logs

# Fleet Telemetry
LOG_LEVEL=info
EOF

echo -e "${GREEN}✓ Created .env file${NC}"

# Generate config.json
cat > config.json << EOF
{
  "host": "0.0.0.0",
  "port": 443,
  "log_level": "info",
  "json_log_enable": true,
  "namespace": "tesla",
  "tls": {
    "server_cert": "/certs/fullchain.pem",
    "server_key": "/certs/privkey.pem"
  },
  "mqtt": {
    "broker": "${MQTT_HOST}:${MQTT_PORT}",
    "client_id": "fleet-telemetry",
    "username": "${MQTT_USERNAME}",
    "password": "${MQTT_PASSWORD}",
    "topic_base": "${MQTT_TOPIC_BASE}",
    "qos": 1,
    "retained": true
  },
  "records": {
    "V": ["mqtt"],
    "alerts": ["mqtt"],
    "errors": ["mqtt"]
  },
  "reliable_ack": true,
  "reliable_ack_sources": {
    "V": "mqtt"
  },
  "rate_limit": {
    "enabled": true,
    "message_limit": 1000,
    "message_interval_time_seconds": 30
  },
  "metrics": {
    "port": 8443,
    "enabled": true,
    "namespace": "tesla_telemetry"
  }
}
EOF

echo -e "${GREEN}✓ Created config.json${NC}"
echo ""

# ============================================================
# STEP 6: Generate Keys
# ============================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Step 6: Tesla API Keys${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ -f "keys/private_key.pem" ]; then
    echo -e "${YELLOW}⚠ Tesla API keys already exist in keys/${NC}"
    read -p "Generate new keys? (y/N): " GENERATE_KEYS
else
    read -p "Generate Tesla API keys now? (Y/n): " GENERATE_KEYS
    GENERATE_KEYS=${GENERATE_KEYS:-Y}
fi

if [[ "$GENERATE_KEYS" =~ ^[Yy]$ ]]; then
    ./scripts/generate_keys.sh
else
    echo -e "${YELLOW}⚠ Skipping key generation. Run ./scripts/generate_keys.sh later.${NC}"
fi

echo ""

# ============================================================
# SUMMARY
# ============================================================
echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    Setup Complete!                           ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "${GREEN}Configuration Summary:${NC}"
echo "  Domain:          $TELEMETRY_DOMAIN"
echo "  MQTT Broker:     $MQTT_HOST:$MQTT_PORT"
echo "  MQTT Topic Base: $MQTT_TOPIC_BASE"
echo ""

echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}NEXT STEPS:${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${BLUE}1. SSL Certificates${NC}"
echo "   Copy your SSL certificates to the certs/ directory:"
echo "   - certs/fullchain.pem  (certificate + chain)"
echo "   - certs/privkey.pem    (private key)"
echo ""
echo "   Options for obtaining certificates:"
echo "   - Let's Encrypt (certbot)"
echo "   - Nginx Proxy Manager"
echo "   - Cloudflare Origin Certificates"
echo ""

echo -e "${BLUE}2. DNS Configuration${NC}"
echo "   Ensure ${TELEMETRY_DOMAIN} points to this server's public IP."
echo "   Important: Do NOT proxy through Cloudflare (grey cloud, not orange)."
echo ""

echo -e "${BLUE}3. Firewall/Port Forwarding${NC}"
echo "   Open port 443 (HTTPS) for incoming connections from Tesla."
echo ""

echo -e "${BLUE}4. Tesla Developer Portal${NC}"
echo "   a. Register at https://developer.tesla.com/"
echo "   b. Create an application"
echo "   c. Set Fleet Telemetry endpoint: https://${TELEMETRY_DOMAIN}"
echo "   d. Host public key at:"
echo "      https://${TELEMETRY_DOMAIN}/.well-known/appspecific/com.tesla.3p.public-key.pem"
echo ""

echo -e "${BLUE}5. Start the Server${NC}"
echo "   docker compose up -d"
echo ""
echo "   Check status:"
echo "   docker compose ps"
echo "   docker compose logs -f fleet-telemetry"
echo ""

echo -e "${BLUE}6. Verify MQTT Messages${NC}"
echo "   Subscribe to MQTT topics from Home Assistant:"
echo "   mosquitto_sub -h localhost -t \"${MQTT_TOPIC_BASE}/#\" -v"
echo ""

echo -e "${BLUE}7. Home Assistant Integration${NC}"
echo "   In HA, add the Tesla Fleet Telemetry Local integration:"
echo "   Settings → Devices & Services → Add Integration"
echo "   - MQTT Topic Base: ${MQTT_TOPIC_BASE}"
echo "   - Vehicle VIN: Your 17-character VIN"
echo "   - Vehicle Name: Friendly name"
echo ""

echo -e "${GREEN}For detailed instructions, see: docs/04_server_deployment.md${NC}"
echo ""
