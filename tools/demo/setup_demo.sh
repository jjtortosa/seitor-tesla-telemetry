#!/bin/bash
#
# Tesla Fleet Telemetry Demo Setup Script
#
# This script configures Home Assistant for the demo:
# 1. Copies the integration to HA config
# 2. Configures MQTT
# 3. Sets up the demo vehicle
#
# Usage:
#   ./setup_demo.sh [HA_CONFIG_PATH]
#
# Example:
#   ./setup_demo.sh /config
#   ./setup_demo.sh /home/homeassistant/.homeassistant

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚗 Tesla Fleet Telemetry Demo Setup${NC}"
echo "========================================"

# Get HA config path
HA_CONFIG="${1:-/config}"

if [ ! -d "$HA_CONFIG" ]; then
    echo -e "${RED}❌ Error: HA config directory not found: $HA_CONFIG${NC}"
    echo "Usage: $0 [HA_CONFIG_PATH]"
    exit 1
fi

echo -e "${YELLOW}📁 HA Config path: $HA_CONFIG${NC}"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo -e "${YELLOW}📁 Repo root: $REPO_ROOT${NC}"

# 1. Copy integration
echo ""
echo -e "${GREEN}1️⃣ Installing Tesla Fleet Telemetry integration...${NC}"

INTEGRATION_SRC="$REPO_ROOT/custom_components/tesla_telemetry_local"
INTEGRATION_DST="$HA_CONFIG/custom_components/tesla_telemetry_local"

if [ ! -d "$INTEGRATION_SRC" ]; then
    echo -e "${RED}❌ Error: Integration not found at $INTEGRATION_SRC${NC}"
    exit 1
fi

mkdir -p "$HA_CONFIG/custom_components"
rm -rf "$INTEGRATION_DST"
cp -r "$INTEGRATION_SRC" "$INTEGRATION_DST"
echo -e "${GREEN}   ✅ Integration copied to $INTEGRATION_DST${NC}"

# 2. Create configuration.yaml additions if needed
echo ""
echo -e "${GREEN}2️⃣ Checking configuration.yaml...${NC}"

CONFIG_FILE="$HA_CONFIG/configuration.yaml"
if ! grep -q "logger:" "$CONFIG_FILE" 2>/dev/null; then
    echo "" >> "$CONFIG_FILE"
    echo "# Tesla Fleet Telemetry Demo logging" >> "$CONFIG_FILE"
    echo "logger:" >> "$CONFIG_FILE"
    echo "  default: info" >> "$CONFIG_FILE"
    echo "  logs:" >> "$CONFIG_FILE"
    echo "    custom_components.tesla_telemetry_local: debug" >> "$CONFIG_FILE"
    echo -e "${GREEN}   ✅ Added logger configuration${NC}"
else
    echo -e "${YELLOW}   ⏭️ Logger already configured${NC}"
fi

# 3. Print next steps
echo ""
echo -e "${GREEN}========================================"
echo "✅ Demo setup complete!"
echo "========================================${NC}"
echo ""
echo "Next steps:"
echo ""
echo "1. Start the demo stack:"
echo "   docker compose -f docker-compose.demo.yml up -d"
echo ""
echo "2. Access Home Assistant:"
echo "   http://localhost:8123"
echo ""
echo "3. Complete HA onboarding, then:"
echo "   - Go to Settings → Devices & Services → Add Integration"
echo "   - Search for 'Tesla Fleet Telemetry Local'"
echo "   - Configure with:"
echo "     - MQTT Topic Base: tesla"
echo "     - Vehicle VIN: DEMO0TESLA0VIN00"
echo "     - Vehicle Name: Demo Tesla"
echo ""
echo "4. The mock telemetry generator is already running!"
echo "   View logs: docker logs -f tesla-mock"
echo ""
echo "🎉 Enjoy your demo!"
