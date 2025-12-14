# Tesla Fleet Telemetry - AI Assistant Context

> **For AI Assistants**: This document provides complete context for helping users set up Tesla Fleet Telemetry with Home Assistant. Read this entire document before assisting the user.

## Project Overview

**Tesla Fleet Telemetry Local** is a self-hosted solution for receiving real-time telemetry data from Tesla vehicles and integrating it with Home Assistant.

### What It Does
- Receives real-time data from Tesla vehicles (location, speed, battery, charging status, etc.)
- Publishes data to MQTT broker (Home Assistant's Mosquitto add-on)
- Creates Home Assistant entities for automation and monitoring

### Architecture

```
┌─────────────────┐     HTTPS:443      ┌─────────────────────────────────────┐
│  Tesla Vehicle  │ ──────────────────▶│  User's Server                      │
│  (sends data)   │                    │  ┌─────────────────────────────────┐│
└─────────────────┘                    │  │ Fleet Telemetry (Docker)        ││
                                       │  │ - Receives vehicle data         ││
                                       │  │ - Validates & processes         ││
                                       │  │ - Publishes to MQTT             ││
                                       │  └──────────────┬──────────────────┘│
                                       └─────────────────┼───────────────────┘
                                                         │ MQTT (1883)
                                                         ▼
                                       ┌─────────────────────────────────────┐
                                       │  Home Assistant                     │
                                       │  ┌─────────────────────────────────┐│
                                       │  │ Mosquitto MQTT Broker           ││
                                       │  │ (Add-on)                        ││
                                       │  └──────────────┬──────────────────┘│
                                       │                 │                   │
                                       │  ┌──────────────┴──────────────────┐│
                                       │  │ Tesla Telemetry Local           ││
                                       │  │ (Custom Integration)            ││
                                       │  │ - Subscribes to MQTT topics     ││
                                       │  │ - Creates HA entities           ││
                                       │  └─────────────────────────────────┘│
                                       └─────────────────────────────────────┘
```

---

## Prerequisites Checklist

Before starting, the user MUST have:

### 1. Infrastructure Requirements
- [ ] **Public Domain**: A domain name (e.g., `tesla-telemetry.example.com`)
- [ ] **DNS Access**: Ability to create DNS records pointing to their server
- [ ] **SSL Certificate**: Valid HTTPS certificate for the domain
- [ ] **Server**: Linux server with Docker (can be same machine as Home Assistant)
- [ ] **Port 443**: Open and forwarded to the server from internet
- [ ] **Home Assistant**: Running instance (Core, Supervised, or OS)
- [ ] **MQTT Broker**: Mosquitto add-on installed in Home Assistant

### 2. Tesla Requirements
- [ ] **Tesla Account**: With a vehicle on the account
- [ ] **Tesla Developer Account**: Register at https://developer.tesla.com/
- [ ] **Vehicle Firmware**: 2024.26+ (or 2023.20.6+ for legacy)

### 3. Technical Knowledge
- [ ] Basic command line usage
- [ ] Docker basics (starting/stopping containers)
- [ ] Network concepts (ports, DNS, SSL)

---

## Complete Setup Process

### Phase 1: Tesla Developer Setup (~30 minutes)

#### Step 1.1: Create Tesla Developer Account
1. Go to https://developer.tesla.com/
2. Sign in with Tesla account
3. Accept developer terms

#### Step 1.2: Create Application
1. Navigate to "Applications" in developer portal
2. Click "Create Application"
3. Fill in details:
   - **Name**: Any name (e.g., "My Home Assistant")
   - **Description**: Personal use
   - **Purpose**: Fleet Telemetry

#### Step 1.3: Generate EC Keys
On the server, run:
```bash
# Generate private key
openssl ecparam -name prime256v1 -genkey -noout -out private_key.pem

# Derive public key
openssl ec -in private_key.pem -pubout -out public_key.pem

# Create Tesla-specific filename
cp public_key.pem com.tesla.3p.public-key.pem
```

#### Step 1.4: Configure Fleet Telemetry in Developer Portal
1. In your application settings, find "Fleet Telemetry"
2. Set hostname to your domain (e.g., `tesla-telemetry.example.com`)
3. Set port to `443`

#### Step 1.5: Host Public Key
The public key MUST be accessible at:
```
https://<your-domain>/.well-known/appspecific/com.tesla.3p.public-key.pem
```

Options:
- Configure in Nginx/reverse proxy
- Use Fleet Telemetry's built-in key hosting

### Phase 2: Server Deployment (~1-2 hours)

#### Step 2.1: Clone Repository
```bash
git clone https://github.com/jjtortosa/seitor-tesla-telemetry.git
cd seitor-tesla-telemetry/server
```

#### Step 2.2: Run Setup Script
```bash
./setup.sh
```

The script will ask for:
- **Domain**: Your telemetry domain (e.g., `tesla-telemetry.example.com`)
- **MQTT Broker**: Home Assistant IP and MQTT credentials
- **MQTT Topic Base**: Usually `tesla` (default)

#### Step 2.3: SSL Certificates
Copy certificates to `certs/` directory:
```bash
certs/
├── fullchain.pem   # Certificate + intermediate chain
└── privkey.pem     # Private key
```

**Certificate Sources**:
- **Let's Encrypt**: Use certbot
- **Nginx Proxy Manager**: Export from NPM
- **Cloudflare**: Origin certificates

#### Step 2.4: Start Services
```bash
docker compose up -d
```

#### Step 2.5: Verify Services
```bash
# Check container is running
docker compose ps

# Check Fleet Telemetry logs
docker compose logs -f fleet-telemetry

# Test MQTT connection (from HA)
mosquitto_sub -h localhost -t "tesla/#" -v
```

### Phase 3: Vehicle Pairing (~15 minutes)

#### Step 3.1: Generate Partner Token
Use Tesla Fleet API to get partner authentication token.

#### Step 3.2: Register with Vehicle
Send virtual key pairing request to vehicle.

#### Step 3.3: Approve in Vehicle
1. Sit in vehicle
2. Approve the key request on center screen
3. Confirm pairing in Tesla app

#### Step 3.4: Configure Telemetry
Send fleet_telemetry_config to vehicle via API.

### Phase 4: Home Assistant Integration (~15 minutes)

#### Step 4.1: Install Mosquitto Add-on
1. Go to Settings → Add-ons → Add-on Store
2. Search for "Mosquitto broker"
3. Install and start the add-on
4. Configure MQTT integration in Settings → Integrations

#### Step 4.2: Install Tesla Integration
Copy integration files:
```bash
# From the cloned repository
cp -r ha-integration/custom_components/tesla_telemetry_local \
      /config/custom_components/
```

Or for Docker-based HA:
```bash
docker cp ha-integration/custom_components/tesla_telemetry_local \
          homeassistant:/config/custom_components/
```

#### Step 4.3: Restart Home Assistant
```bash
# For HA OS/Supervised
ha core restart

# For Docker
docker restart homeassistant
```

#### Step 4.4: Add Integration
1. Go to Settings → Devices & Services → Add Integration
2. Search for "Tesla Fleet Telemetry Local"
3. Enter configuration:
   - **MQTT Topic Base**: `tesla` (must match server config)
   - **Vehicle VIN**: Your 17-character VIN
   - **Vehicle Name**: Friendly name (e.g., "Model Y")

#### Step 4.5: Verify Entities
After configuration, you should see:
- `device_tracker.<name>_location`
- `sensor.<name>_speed`
- `sensor.<name>_battery`
- `sensor.<name>_range`
- `sensor.<name>_charging_state`
- `binary_sensor.<name>_driving`
- `binary_sensor.<name>_charging`
- And more... (13 entities total)

---

## Configuration Reference

### Server Configuration (config.json)

```json
{
  "host": "0.0.0.0",
  "port": 443,
  "log_level": "info",
  "mqtt": {
    "broker": "192.168.1.50:1883",
    "client_id": "fleet-telemetry",
    "username": "mqtt_user",
    "password": "mqtt_password",
    "topic_base": "tesla",
    "qos": 1,
    "retained": true
  },
  "records": {
    "V": ["mqtt"],
    "alerts": ["mqtt"],
    "errors": ["mqtt"]
  },
  "tls": {
    "server_cert": "/certs/fullchain.pem",
    "server_key": "/certs/privkey.pem"
  }
}
```

### Environment Variables (.env)

| Variable | Description | Example |
|----------|-------------|---------|
| `TELEMETRY_DOMAIN` | Public domain | `tesla-telemetry.example.com` |
| `MQTT_BROKER` | HA MQTT broker IP:port | `192.168.1.50:1883` |
| `MQTT_USERNAME` | MQTT username | `mqtt_user` |
| `MQTT_PASSWORD` | MQTT password | `your_password` |
| `MQTT_TOPIC_BASE` | Base topic | `tesla` |
| `LOG_LEVEL` | Verbosity | `info` |

### MQTT Topic Structure

Fleet Telemetry publishes to these topics:
```
tesla/<VIN>/v/VehicleSpeed      → {"value": 65}
tesla/<VIN>/v/BatteryLevel      → {"value": 78}
tesla/<VIN>/v/Location          → {"latitude": 41.38, "longitude": 2.17}
tesla/<VIN>/v/ChargeState       → {"value": "Charging"}
tesla/<VIN>/connectivity        → {"Status": "connected"}
tesla/<VIN>/alerts/#            → Alert messages
```

---

## Troubleshooting Guide

### Problem: Fleet Telemetry won't start

**Check 1**: Certificates
```bash
# Verify certificate is valid
openssl x509 -in certs/fullchain.pem -text -noout | grep -A2 "Validity"

# Check certificate matches domain
openssl x509 -in certs/fullchain.pem -noout -subject
```

**Check 2**: Config syntax
```bash
cat config.json | python3 -m json.tool
```

**Check 3**: Logs
```bash
docker compose logs fleet-telemetry
```

### Problem: MQTT connection failed

**Check 1**: Mosquitto is running
```bash
# In Home Assistant
ha addons info core_mosquitto
```

**Check 2**: Network connectivity
```bash
# From server
nc -zv <ha-ip> 1883
```

**Check 3**: Credentials
- Verify username/password in Home Assistant MQTT add-on configuration
- Test with mosquitto_pub from command line

### Problem: No messages in MQTT

**Check 1**: Vehicle connected
- Open Tesla app
- Check vehicle shows "Fleet Telemetry: Connected" or similar

**Check 2**: DNS resolves correctly
```bash
nslookup tesla-telemetry.example.com
```

**Check 3**: Port 443 open
```bash
# From external network
nc -zv tesla-telemetry.example.com 443
```

**Check 4**: Subscribe to MQTT
```bash
mosquitto_sub -h localhost -t "tesla/#" -v
```

### Problem: HA integration not loading

**Check 1**: MQTT integration configured
- Go to Settings → Integrations
- Verify "MQTT" integration is configured and connected

**Check 2**: Files copied correctly
```bash
ls -la /config/custom_components/tesla_telemetry_local/
```

**Check 3**: HA logs
```bash
grep "tesla_telemetry" /config/home-assistant.log
```

### Problem: Entities show "Unavailable"

**Check 1**: MQTT messages arriving
```bash
mosquitto_sub -h localhost -t "tesla/#" -v
```

**Check 2**: Topic base matches
- Ensure topic_base in server config matches HA integration config

**Check 3**: VIN matches
- Ensure VIN in HA config matches vehicle VIN exactly (17 characters)

---

## Common User Scenarios

### Scenario A: User has Nginx Proxy Manager
1. Create proxy host for domain → server:443
2. Use NPM's SSL certificate
3. Export cert as fullchain.pem + privkey.pem

### Scenario B: User has Cloudflare
1. Create DNS A record pointing to public IP
2. Use Cloudflare Origin Certificate
3. Set SSL mode to "Full (Strict)"
4. **Important**: Do NOT proxy the traffic (grey cloud, not orange)

### Scenario C: HA and server on same machine
1. Set MQTT_BROKER to `localhost:1883`
2. Use Docker network if both in containers

### Scenario D: HA in Docker, server on host
1. Set MQTT_BROKER to Docker host IP (not localhost)
2. Or use Docker network bridge IP

---

## Files Reference

```
seitor-tesla-telemetry/
├── server/
│   ├── docker-compose.yml    # Docker stack (Fleet Telemetry only)
│   ├── setup.sh              # Interactive setup
│   ├── config.json           # Fleet Telemetry config (generated)
│   ├── .env                  # Environment vars (generated)
│   ├── certs/                # SSL certificates (user provides)
│   └── keys/                 # Tesla API keys (generated)
│
├── ha-integration/
│   └── custom_components/
│       └── tesla_telemetry_local/
│           ├── __init__.py
│           ├── config_flow.py
│           ├── sensor.py
│           ├── binary_sensor.py
│           ├── device_tracker.py
│           └── manifest.json
│
└── docs/
    ├── 01_overview.md
    ├── 02_infrastructure_setup.md
    ├── 03_tesla_developer_setup.md
    ├── 04_server_deployment.md
    ├── 05_ha_integration.md
    └── 06_troubleshooting.md
```

---

## AI Assistant Instructions

When helping users:

1. **Start by assessing their setup**:
   - What infrastructure do they have? (Proxmox, Docker, bare metal?)
   - Do they already have a domain and SSL?
   - Is Home Assistant running with MQTT configured?

2. **Guide step by step**:
   - Complete one phase before moving to the next
   - Verify each step works before proceeding
   - Provide exact commands they can copy-paste

3. **Adapt to their environment**:
   - Nginx Proxy Manager vs Traefik vs direct exposure
   - Docker vs native installation
   - HA OS vs HA Core vs HA Supervised

4. **Common issues to watch for**:
   - Wrong MQTT broker address (must be reachable from server)
   - MQTT credentials incorrect
   - Certificate issues (expired, wrong domain, self-signed)
   - Firewall blocking port 443 or 1883
   - VIN mismatch between config and vehicle
   - Topic base mismatch between server and integration

5. **When troubleshooting**:
   - Always check logs first
   - Verify MQTT messages with mosquitto_sub
   - Test each component independently
   - Use the debugging commands provided

---

## User Environment Template

Ask the user to fill this out:

```
## My Environment

**Domain**: _________________________ (e.g., tesla-telemetry.mydomain.com)
**Server IP**: ______________________ (e.g., 192.168.1.100)
**Home Assistant IP**: _______________ (e.g., 192.168.1.50)
**Vehicle VIN**: ____________________ (17 characters)
**Vehicle Name**: ___________________ (e.g., Model Y)

**Infrastructure**:
- [ ] Proxmox
- [ ] Docker on Linux
- [ ] Raspberry Pi
- [ ] Other: _______________

**SSL Method**:
- [ ] Let's Encrypt (certbot)
- [ ] Nginx Proxy Manager
- [ ] Cloudflare
- [ ] Other: _______________

**MQTT Setup**:
- [ ] Mosquitto add-on installed
- [ ] MQTT integration configured
- [ ] MQTT username/password created

**Network Setup**:
- [ ] HA and server on same machine
- [ ] HA and server on same network
- [ ] HA on different network than server
```
