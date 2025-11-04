# Deployment Information - Tesla Fleet Telemetry Self-Hosted

**Project**: seitor-tesla-telemetry
**Status**: Ready to deploy
**Date**: 2025-11-04

---

## Infrastructure Details

### Proxmox Server
- **URL**: https://proxmox.seitor.com/
- **LAN IP**: 192.168.5.207
- **Status**: ✅ Accessible
- **Action needed**: Create LXC container for tesla-telemetry

### Network Configuration
- **Public IP**: 83.42.50.84
- **Domain**: seitor.com
- **DNS Provider**: Cloudflare
- **Subdomain needed**: tesla-telemetry.seitor.com → 83.42.50.84

### Home Assistant
- **URL**: ha.seitor.com
- **Config directory (Mac)**: /Volumes/config
- **Config directory (HA)**: /config
- **Status**: ✅ Running

---

## Deployment Plan Overview

### Phase 1: Infrastructure Setup (2h 20min)
**Can be done today/tomorrow**

1. **Create Proxmox LXC Container** (30 min)
   - Hostname: tesla-telemetry
   - IP: 192.168.5.106 (or next available)
   - CPU: 2 cores
   - RAM: 4GB
   - Disk: 20GB
   - Enable nesting for Docker

2. **Configure DNS in Cloudflare** (5 min)
   - Type: A
   - Name: tesla-telemetry
   - IPv4: 83.42.50.84
   - Proxy: OFF (DNS only)

3. **Install Docker** (15 min)
   - Ubuntu 22.04/24.04 in container
   - Docker + Docker Compose

4. **Configure Port Forwarding** (10 min)
   - Router: 443 → 192.168.5.106:443

5. **Generate SSL Certificate** (15 min)
   - Let's Encrypt for tesla-telemetry.seitor.com
   - Certbot with auto-renewal

6. **Clone Repository** (20 min)
   - git clone to /opt/tesla-telemetry
   - Generate EC keys
   - Copy SSL certificates

7. **Host Public Key** (15 min)
   - Install Nginx
   - Serve key at .well-known/appspecific/
   - Test: curl https://tesla-telemetry.seitor.com/.well-known/appspecific/com.tesla.3p.public-key.pem

### Phase 2: Tesla Configuration (1h)
**Requires Tesla Developer account**

8. **Configure Tesla Developer** (30 min)
   - Create app at developer.tesla.com
   - Register domain: tesla-telemetry.seitor.com
   - Virtual key pairing (wait 5-30 min for sync)

9. **Deploy Docker Stack** (15 min)
   - docker compose up -d
   - Verify containers healthy

10. **Configure Telemetry Fields** (20 min)
    - Create telemetry_config.json
    - Get OAuth token
    - Send config to vehicle

### Phase 3: Testing & HA Integration (1h)
**Final steps**

11. **Test Vehicle Connection** (30 min)
    - Wake vehicle
    - Monitor logs for connection
    - Verify Kafka messages

12. **Install HA Integration** (30 min)
    - Copy custom_components to /Volumes/config/
    - Install Python dependencies
    - Configure configuration.yaml
    - Restart HA

13. **Verify & Test** (15 min)
    - Check entities created
    - Test real-time updates
    - Test garage automation

---

## Required Credentials

### For Deployment

- [ ] Proxmox login credentials
- [ ] Cloudflare login (for DNS)
- [ ] Router admin access (for port forwarding)
- [ ] Email for Let's Encrypt certificates
- [ ] Tesla account (for developer.tesla.com)

### To Be Generated During Deployment

- EC private/public keys (via scripts/generate_keys.sh)
- Tesla Developer Client ID & Secret
- Tesla OAuth access token
- Tesla Vehicle ID

---

## Pre-Deployment Checklist

### Verified Information
- ✅ Proxmox accessible at https://proxmox.seitor.com/
- ✅ Domain seitor.com managed in Cloudflare
- ✅ Public IP: 83.42.50.84
- ✅ Home Assistant at ha.seitor.com
- ✅ Config directory: /Volumes/config

### Ready to Use
- ✅ Complete documentation (docs/01-06)
- ✅ Server Docker Compose stack
- ✅ HA custom integration code
- ✅ Utility scripts (key generation, cert validation)
- ✅ All files in GitHub

### Still Needed
- ⏳ Create Proxmox container
- ⏳ Configure DNS A record
- ⏳ Setup port forwarding
- ⏳ Generate SSL certificate
- ⏳ Tesla Developer account setup
- ⏳ Virtual key pairing

---

## Estimated Time Breakdown

| Task | Time | Blocking? | Can Skip? |
|------|------|-----------|-----------|
| **TODAY/TOMORROW** | | | |
| Create container | 30 min | Yes | No |
| DNS config | 5 min | Yes | No |
| Install Docker | 15 min | Yes | No |
| Port forwarding | 10 min | Yes | No |
| SSL certificate | 15 min | Yes | No |
| Clone repo & keys | 20 min | Yes | No |
| Host public key | 15 min | Yes | No |
| **LATER** | | | |
| Tesla Developer | 30 min | Blocks 9-10 | No |
| Deploy Docker | 15 min | No | No |
| Config telemetry | 20 min | No | No |
| Test connection | 30 min | No | Yes (can test later) |
| HA integration | 30 min | No | No |
| Final verification | 15 min | No | Yes (continuous) |

**Minimum today**: 2h 20min (tasks 1-7)
**Full deployment**: 4h 15min total

---

## Quick Start Commands

### Access Proxmox Container (after creation)
```bash
ssh root@192.168.5.106
# or from Proxmox host:
pct enter 106
```

### Navigate to Project
```bash
cd /opt/tesla-telemetry/server
```

### Check Docker Status
```bash
docker compose ps
docker compose logs -f fleet-telemetry
```

### Check Kafka Messages
```bash
docker exec -it kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic tesla_telemetry \
  --from-beginning \
  --max-messages 10
```

### HA Integration Path
```bash
# On Mac:
/Volumes/config/custom_components/tesla_telemetry_local/

# In HA:
/config/custom_components/tesla_telemetry_local/
```

---

## Documentation References

All detailed step-by-step instructions available in:

- **docs/02_infrastructure_setup.md** - Proxmox, Docker, DNS, SSL
- **docs/03_tesla_developer_setup.md** - Tesla account, keys, pairing
- **docs/04_server_deployment.md** - Deploy stack, test connection
- **docs/05_ha_integration.md** - Install integration, entities
- **docs/06_troubleshooting.md** - Debug common issues

---

## Current Project Status

- ✅ **v0.1.0** - Core implementation complete
- ✅ Documentation: 6 guides (~20k words)
- ✅ Server infrastructure: Docker Compose stack ready
- ✅ HA integration: Custom component complete (~1,500 lines)
- ⏳ Protobuf schema: Placeholder (needs compilation)
- ⏳ Real deployment: PENDING (start tomorrow)

---

## Next Session Goals

**Priority 1** (Must do):
1. Create Proxmox container
2. Configure DNS
3. Install Docker
4. Generate SSL cert
5. Clone repo & generate keys

**Priority 2** (Should do):
6. Host public key (Nginx)
7. Tesla Developer setup
8. Deploy Docker stack

**Priority 3** (Nice to have):
9. Test vehicle connection
10. Install HA integration
11. Test garage automation

---

## Notes

- **Container IP suggestion**: 192.168.5.106 (verify availability first)
- **Existing HA config**: /Volumes/config is mounted from HA
- **Vehicle**: MelanY (Model Y)
- **Current problem**: Garage doesn't open (polling too slow)
- **Expected fix**: Streaming <1s latency vs 5-15min polling

---

## Rollback Plan

If deployment fails or doesn't work:

1. **Container issues**: Delete and recreate
2. **DNS issues**: Can revert A record immediately
3. **Tesla pairing issues**: Can unpair and retry
4. **HA integration issues**: Remove custom_components/tesla_telemetry_local/
5. **Full rollback**: Keep current Tesla Fleet integration, delete container

No risk to current HA setup until Phase 3 (HA integration installation).

---

**Last updated**: 2025-11-04
**Ready to deploy**: YES
**Estimated completion**: 1-2 days (4-5 hours total work)
