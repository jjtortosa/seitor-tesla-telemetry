# Infrastructure Setup

This guide covers setting up the infrastructure required to run the Fleet Telemetry server.

## Prerequisites

- ✅ Proxmox server (or equivalent Docker host)
- ✅ Domain name with DNS control (e.g., seitor.com)
- ✅ Router with port forwarding capability
- ✅ Basic Linux command-line knowledge

**Estimated time**: 1-2 hours

---

## Step 1: Create Proxmox LXC Container

### 1.1 Create Container

**Recommended specs**:
- **Template**: Ubuntu 22.04 or 24.04
- **Container ID**: e.g., 105
- **Hostname**: `tesla-telemetry`
- **CPU**: 2 cores
- **RAM**: 4096 MB (4GB)
- **Swap**: 512 MB
- **Disk**: 20 GB
- **Network**: Bridge (vmbr0) with static IP

**Proxmox Web UI**:
1. Select node → "Create CT"
2. General tab:
   - CT ID: 105
   - Hostname: `tesla-telemetry`
   - Unprivileged container: ✅ Yes
   - Nesting: ✅ Enable (required for Docker)
3. Template tab:
   - Storage: local
   - Template: `ubuntu-22.04-standard`
4. Disks tab:
   - Disk size: 20 GB
5. CPU tab:
   - Cores: 2
6. Memory tab:
   - Memory: 4096 MB
   - Swap: 512 MB
7. Network tab:
   - Bridge: vmbr0
   - IPv4: Static
   - IPv4/CIDR: e.g., 192.168.5.105/24
   - Gateway: e.g., 192.168.5.1
8. DNS tab:
   - Use host settings: ✅
9. Confirm and create

### 1.2 Enable Nesting and Features

Edit container config to support Docker:

```bash
# On Proxmox host
nano /etc/pve/lxc/105.conf
```

Add these lines:

```conf
# Docker support
features: nesting=1,keyctl=1
lxc.apparmor.profile: unconfined
lxc.cap.drop:
lxc.cgroup2.devices.allow: a
lxc.mount.auto: sys:rw
```

**Reboot container**:
```bash
pct reboot 105
```

### 1.3 Initial Container Setup

Enter container console:

```bash
# From Proxmox host
pct enter 105
```

Update system:

```bash
apt update && apt upgrade -y
apt install -y curl wget git nano htop net-tools
```

---

## Step 2: Install Docker

### 2.1 Install Docker Engine

```bash
# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Set up the repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Verify installation
docker --version
docker compose version
```

Expected output:
```
Docker version 24.0.x
Docker Compose version v2.23.x
```

### 2.2 Enable Docker Service

```bash
systemctl enable docker
systemctl start docker
systemctl status docker
```

### 2.3 Test Docker

```bash
docker run hello-world
```

You should see: _"Hello from Docker!"_

---

## Step 3: Configure DNS

You need a public subdomain pointing to your home IP address.

### 3.1 Option A: Static Public IP

If you have a static public IP:

1. Log in to your domain registrar (e.g., Cloudflare, Namecheap)
2. Add an **A record**:
   - **Name**: `tesla-telemetry` (or `tesla-telemetry.seitor.com`)
   - **Type**: A
   - **Value**: Your public IP (e.g., `93.45.123.45`)
   - **TTL**: 300 (5 minutes)
3. Save changes

### 3.2 Option B: Dynamic DNS (DDNS)

If your public IP changes (typical for home ISPs):

**Using Cloudflare**:

1. Create API token:
   - Log in to Cloudflare
   - My Profile → API Tokens → Create Token
   - Template: "Edit zone DNS"
   - Zone Resources: Include → Specific zone → seitor.com
   - Copy token

2. Install DDNS updater on Proxmox host or router:

```bash
# Example: ddclient on Proxmox host
apt install -y ddclient

# Configure /etc/ddclient.conf
protocol=cloudflare
use=web, web=checkip.dyndns.org
ssl=yes
server=api.cloudflare.com/client/v4
login=your-cloudflare-email@example.com
password=your-api-token
zone=seitor.com
tesla-telemetry.seitor.com
```

3. Enable ddclient:

```bash
systemctl enable ddclient
systemctl start ddclient
systemctl status ddclient
```

**Alternative**: Many routers have built-in DDNS support (check router settings).

### 3.3 Verify DNS Resolution

From any computer:

```bash
nslookup tesla-telemetry.seitor.com
# or
dig tesla-telemetry.seitor.com

# Should return your public IP
```

**Wait 5-10 minutes** for DNS propagation if just created.

---

## Step 4: Port Forwarding

Configure your router to forward external traffic to the Proxmox container.

### 4.1 Router Configuration

Access your router's admin panel (typically `192.168.1.1` or `192.168.0.1`).

**Port forwarding rule**:
- **Name**: Tesla Telemetry
- **External port**: 443 (HTTPS)
- **Internal IP**: 192.168.5.105 (container IP)
- **Internal port**: 443
- **Protocol**: TCP
- **Enable**: ✅

**Example (varies by router)**:
```
Service Name: Tesla Telemetry
WAN Port: 443
LAN IP: 192.168.5.105
LAN Port: 443
Protocol: TCP
```

### 4.2 Verify Port Forwarding

From **outside your network** (use mobile hotspot or https://www.yougetsignal.com/tools/open-ports/):

```bash
# Check if port 443 is accessible
nc -zv tesla-telemetry.seitor.com 443
# or
telnet tesla-telemetry.seitor.com 443
```

Expected: Connection successful (even if no service running yet)

**Troubleshooting**:
- Firewall on router: Ensure 443 is allowed
- ISP blocking: Some ISPs block port 443 for residential users (rare)
- Double NAT: Check if router has public IP or another NAT layer

---

## Step 5: SSL Certificate Setup

Tesla requires a valid SSL certificate. We'll use Let's Encrypt (free).

### 5.1 Install Certbot

On the **Proxmox container**:

```bash
apt install -y certbot
```

### 5.2 Generate Certificate

**Standalone mode** (requires port 80 temporarily):

```bash
# Stop any service on port 80 if running
# Then generate cert:

certbot certonly --standalone \
  -d tesla-telemetry.seitor.com \
  --non-interactive \
  --agree-tos \
  --email your-email@example.com
```

**Expected output**:
```
Successfully received certificate.
Certificate is saved at: /etc/letsencrypt/live/tesla-telemetry.seitor.com/fullchain.pem
Key is saved at:         /etc/letsencrypt/live/tesla-telemetry.seitor.com/privkey.pem
```

**Webroot mode** (if you have a web server running):

```bash
mkdir -p /var/www/html/.well-known/acme-challenge

certbot certonly --webroot \
  -w /var/www/html \
  -d tesla-telemetry.seitor.com \
  --non-interactive \
  --agree-tos \
  --email your-email@example.com
```

### 5.3 Verify Certificate

```bash
ls -la /etc/letsencrypt/live/tesla-telemetry.seitor.com/

# Should show:
# - cert.pem (certificate)
# - chain.pem (intermediate certificates)
# - fullchain.pem (cert + chain)
# - privkey.pem (private key)
```

### 5.4 Test Certificate

```bash
openssl x509 -in /etc/letsencrypt/live/tesla-telemetry.seitor.com/fullchain.pem -text -noout

# Check:
# - Subject: CN = tesla-telemetry.seitor.com
# - Issuer: Let's Encrypt
# - Validity: 90 days
```

### 5.5 Automatic Renewal

Let's Encrypt certificates expire after 90 days. Set up automatic renewal:

```bash
# Test renewal (dry-run)
certbot renew --dry-run

# If successful, enable timer
systemctl enable certbot.timer
systemctl start certbot.timer
systemctl status certbot.timer
```

Certbot will automatically renew certificates 30 days before expiration.

**Add post-renewal hook** to restart Docker containers:

```bash
nano /etc/letsencrypt/renewal-hooks/deploy/restart-docker.sh
```

Content:
```bash
#!/bin/bash
docker restart fleet-telemetry
```

Make executable:
```bash
chmod +x /etc/letsencrypt/renewal-hooks/deploy/restart-docker.sh
```

---

## Step 6: Firewall Configuration (Optional but Recommended)

### 6.1 Install UFW (Uncomplicated Firewall)

```bash
apt install -y ufw
```

### 6.2 Configure Rules

```bash
# Allow SSH (important! Don't lock yourself out)
ufw allow 22/tcp

# Allow HTTPS for Fleet Telemetry
ufw allow 443/tcp

# Allow HTTP for cert renewal (optional if using standalone mode)
ufw allow 80/tcp

# Enable firewall
ufw enable

# Check status
ufw status verbose
```

**Expected output**:
```
Status: active

To                         Action      From
--                         ------      ----
22/tcp                     ALLOW       Anywhere
443/tcp                    ALLOW       Anywhere
80/tcp                     ALLOW       Anywhere
```

---

## Step 7: Prepare Directories

Create directory structure for the project:

```bash
# Create project directory
mkdir -p /opt/tesla-telemetry
cd /opt/tesla-telemetry

# Create subdirectories
mkdir -p certs config scripts logs

# Set permissions
chmod 755 /opt/tesla-telemetry
```

---

## Step 8: Network Configuration

### 8.1 Verify Container Networking

```bash
# Check IP address
ip addr show

# Check default gateway
ip route show

# Test internet connectivity
ping -c 4 8.8.8.8

# Test DNS resolution
nslookup google.com
```

### 8.2 Configure Static IP (if using DHCP)

If the container is using DHCP, set a static IP:

```bash
nano /etc/netplan/00-installer-config.yaml
```

Content:
```yaml
network:
  version: 2
  ethernets:
    eth0:
      addresses:
        - 192.168.5.105/24
      routes:
        - to: default
          via: 192.168.5.1
      nameservers:
        addresses:
          - 8.8.8.8
          - 8.8.4.4
```

Apply:
```bash
netplan apply
```

---

## Step 9: Validation Checklist

Before proceeding, verify:

- ✅ Proxmox LXC container created and running
- ✅ Docker installed and working
- ✅ DNS record created (tesla-telemetry.seitor.com → public IP)
- ✅ DNS resolves correctly from outside network
- ✅ Port 443 forwarded to container
- ✅ SSL certificate generated (/etc/letsencrypt/live/...)
- ✅ Automatic certificate renewal configured
- ✅ Firewall rules configured
- ✅ Project directories created (/opt/tesla-telemetry)

---

## Troubleshooting

### DNS not resolving

**Problem**: `nslookup tesla-telemetry.seitor.com` fails

**Solutions**:
1. Wait 5-10 minutes for DNS propagation
2. Check DNS record at registrar/Cloudflare
3. Try different DNS server: `nslookup tesla-telemetry.seitor.com 8.8.8.8`
4. Clear local DNS cache

### Port 443 not accessible

**Problem**: Cannot connect to port 443 from outside

**Solutions**:
1. Verify port forwarding rule on router
2. Check if router has public IP: https://whatismyipaddress.com/
3. Test from mobile hotspot (not same network)
4. Check ISP doesn't block port 443
5. Verify firewall allows 443: `ufw status`

### Certificate generation fails

**Problem**: Certbot errors during generation

**Solutions**:
1. Ensure DNS points to your public IP
2. Check port 80 is accessible (for standalone mode)
3. Verify no other service using port 80/443
4. Check logs: `journalctl -u certbot`
5. Try webroot mode instead of standalone

### Docker not starting in LXC

**Problem**: Docker service fails to start

**Solutions**:
1. Ensure nesting enabled: `features: nesting=1` in `/etc/pve/lxc/105.conf`
2. Add: `lxc.apparmor.profile: unconfined`
3. Reboot container: `pct reboot 105`
4. Check logs: `journalctl -u docker`

---

## Next Steps

Infrastructure is ready! Proceed to:

**[03 - Tesla Developer Setup →](03_tesla_developer_setup.md)**

This will guide you through creating a Tesla Developer account, generating cryptographic keys, and registering your application.
