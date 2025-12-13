# Prompt: Setup with Nginx Proxy Manager

Use this if you're using Nginx Proxy Manager for SSL and reverse proxy.

---

## Prompt

```
I want to set up Tesla Fleet Telemetry using Nginx Proxy Manager for SSL/reverse proxy.

Please read the CLAUDE_CONTEXT.md file in this project for context.

**My NPM setup**:
- NPM URL: [e.g., http://192.168.1.10:81]
- NPM is working: [YES/NO]
- I can create SSL certificates in NPM: [YES/NO]

**My domain**:
- Domain: [YOUR DOMAIN]
- DNS points to: [NPM SERVER IP / PUBLIC IP]
- Cloudflare proxy: [ENABLED/DISABLED]

**Fleet Telemetry server**:
- Will run on IP: [e.g., 192.168.1.100]
- Same machine as NPM: [YES/NO]

Please help me:
1. Configure NPM proxy host for Fleet Telemetry
2. Set up SSL certificate
3. Configure Fleet Telemetry to work behind NPM
4. Test the connection
```

---

## NPM Configuration Notes

For Tesla Fleet Telemetry behind NPM:

**Proxy Host Settings**:
- Domain: `tesla-telemetry.yourdomain.com`
- Scheme: `https`
- Forward Hostname/IP: `<fleet-telemetry-server-ip>`
- Forward Port: `443`
- Enable "Websockets Support"
- SSL Certificate: Request new or use existing

**Important**: Fleet Telemetry uses WebSocket connections. Make sure "Websockets Support" is enabled.

**SSL Configuration**:
- You can use Let's Encrypt through NPM
- Or use Cloudflare Origin certificates
- Certificate files go in Fleet Telemetry's `certs/` folder
