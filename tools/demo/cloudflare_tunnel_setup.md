# Cloudflare Tunnel Setup for Demo

Cloudflare Tunnel is the easiest way to expose HA Test publicly without port forwarding or NPM.

## Benefits

- ✅ No port forwarding needed
- ✅ Automatic SSL
- ✅ DDoS protection
- ✅ Free tier available
- ✅ Zero Trust security

## Setup Steps

### 1. Install cloudflared on HA Test

SSH into HA Test (via Proxmox console or SSH add-on):

```bash
# For Home Assistant OS with Terminal add-on
# Or via Proxmox console

# Download cloudflared
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared
chmod +x /usr/local/bin/cloudflared

# Verify installation
cloudflared --version
```

### 2. Authenticate with Cloudflare

```bash
cloudflared tunnel login
```

This opens a browser to authenticate. Select `seitor.com` zone.

### 3. Create the Tunnel

```bash
# Create tunnel named "ha-demo"
cloudflared tunnel create ha-demo

# This creates credentials in ~/.cloudflared/
# Note the Tunnel ID (e.g., abc123-def456-...)
```

### 4. Configure DNS

```bash
# Create CNAME record pointing to the tunnel
cloudflared tunnel route dns ha-demo demo.seitor.com
```

### 5. Create Tunnel Configuration

```bash
cat > ~/.cloudflared/config.yml << 'EOF'
tunnel: ha-demo
credentials-file: /root/.cloudflared/<TUNNEL_ID>.json

ingress:
  - hostname: demo.seitor.com
    service: http://localhost:8123
    originRequest:
      noTLSVerify: true
  - service: http_status:404
EOF
```

Replace `<TUNNEL_ID>` with your actual tunnel ID.

### 6. Run the Tunnel

```bash
# Test first
cloudflared tunnel run ha-demo

# If working, install as service
cloudflared service install
systemctl enable cloudflared
systemctl start cloudflared
```

### 7. Verify

```bash
# Check tunnel status
cloudflared tunnel info ha-demo

# Test access
curl -I https://demo.seitor.com
```

## Alternative: Cloudflare Tunnel via Docker

If HA Test supports Docker add-on:

```yaml
# docker-compose.yml for cloudflared
version: '3'
services:
  cloudflared:
    image: cloudflare/cloudflared:latest
    restart: unless-stopped
    command: tunnel run
    environment:
      - TUNNEL_TOKEN=<YOUR_TUNNEL_TOKEN>
```

Get token from Cloudflare Zero Trust dashboard.

## Cloudflare Zero Trust Dashboard Method (Easiest)

1. Go to https://one.dash.cloudflare.com
2. Select your account
3. Go to **Access** → **Tunnels**
4. Click **Create a tunnel**
5. Name: `ha-demo`
6. Choose **Cloudflared** connector
7. Copy the installation command
8. Run on HA Test
9. Add public hostname:
   - Subdomain: `demo`
   - Domain: `seitor.com`
   - Service: `http://localhost:8123`

## Security Notes

- Cloudflare Tunnel encrypts all traffic
- Consider adding Cloudflare Access for authentication
- HA's own authentication still applies
