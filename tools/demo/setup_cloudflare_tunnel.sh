#!/bin/bash
#
# Setup Cloudflare Tunnel for demo.seitor.com
#
# Prerequisites:
# 1. cloudflared installed on HA Test
# 2. Tunnel created in Cloudflare Zero Trust dashboard
# 3. Tunnel token obtained
#
# Usage:
#   ./setup_cloudflare_tunnel.sh <TUNNEL_TOKEN>
#
# Or run interactively without arguments

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

HA_HOST="192.168.6.41"

echo -e "${GREEN}🌐 Cloudflare Tunnel Setup for demo.seitor.com${NC}"
echo "=================================================="

# Get token
if [ -n "$1" ]; then
    TUNNEL_TOKEN="$1"
else
    echo ""
    echo -e "${CYAN}To get a tunnel token:${NC}"
    echo "1. Go to https://one.dash.cloudflare.com"
    echo "2. Select your account"
    echo "3. Navigate to Networks → Tunnels"
    echo "4. Click 'Create a tunnel'"
    echo "5. Name: 'ha-demo'"
    echo "6. Choose 'Cloudflared' connector"
    echo "7. Copy the token from the install command"
    echo ""
    read -p "Enter the tunnel token: " TUNNEL_TOKEN
fi

if [ -z "$TUNNEL_TOKEN" ]; then
    echo -e "${RED}❌ No token provided. Exiting.${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}📡 Configuring tunnel on HA Test (${HA_HOST})...${NC}"

# Stop any existing cloudflared processes
ssh -o StrictHostKeyChecking=no root@${HA_HOST} "pkill cloudflared 2>/dev/null || true"

# Create systemd service
ssh -o StrictHostKeyChecking=no root@${HA_HOST} << ENDSSH
# Create service file
cat > /etc/systemd/system/cloudflared.service << 'EOF'
[Unit]
Description=Cloudflare Tunnel
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/cloudflared tunnel --no-autoupdate run --token ${TUNNEL_TOKEN}
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
systemctl daemon-reload
systemctl enable cloudflared
systemctl start cloudflared
systemctl status cloudflared --no-pager
ENDSSH

echo ""
echo -e "${GREEN}✅ Cloudflare Tunnel configured!${NC}"
echo ""
echo "Next steps:"
echo "1. Go back to Cloudflare Zero Trust dashboard"
echo "2. In the tunnel configuration, add a public hostname:"
echo "   - Subdomain: demo"
echo "   - Domain: seitor.com"
echo "   - Service Type: HTTP"
echo "   - URL: localhost:8123"
echo ""
echo "3. Save and verify at: https://demo.seitor.com"
