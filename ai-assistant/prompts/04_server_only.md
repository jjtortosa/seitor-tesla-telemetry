# Prompt: Server Setup Only

Use this if you only need help setting up the Fleet Telemetry server.

---

## Prompt

```
I need help setting up the Tesla Fleet Telemetry server. I'll handle the Home Assistant integration separately.

Please read the CLAUDE_CONTEXT.md file in this project for context.

**My infrastructure**:
- Server OS: [e.g., Ubuntu 22.04, Debian 12, Proxmox LXC]
- Docker installed: [YES/NO]
- Docker Compose installed: [YES/NO]

**Domain setup**:
- Domain: [YOUR DOMAIN]
- DNS provider: [e.g., Cloudflare, Route53, local]
- Current DNS status: [POINTING TO SERVER / NOT CONFIGURED]

**SSL certificates**:
- Method: [Let's Encrypt / Nginx Proxy Manager / Cloudflare / Other]
- Already have certificates: [YES/NO]

**Network**:
- Server public IP: [YOUR PUBLIC IP]
- Server local IP: [YOUR LOCAL IP]
- Port 443 forwarded: [YES/NO/NOT SURE]

Please help me:
1. Set up the Docker stack
2. Configure SSL certificates
3. Verify the server is accessible from internet
4. Test that Tesla can connect
```

---

## Prerequisite Checks

Run these before asking for help:

```bash
# Check Docker
docker --version
docker compose version

# Check ports
sudo netstat -tlnp | grep -E "443|9092"

# Check if domain resolves
nslookup your-domain.com

# Test port 443 from outside (use online tool or different network)
```
