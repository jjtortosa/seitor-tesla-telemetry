# Real-World Testing Guide - HA Test Deployment

This guide covers testing the Tesla Fleet Telemetry integration on your **Home Assistant Test instance** with the server publishing directly to MQTT.

## Overview

**Deployment Architecture**:
```
┌─────────────────────────────────────────────┐
│     HA Test (Proxmox Container)             │
│                                             │
│  ┌──────────────────────────────────────┐  │
│  │  Home Assistant                      │  │
│  │  - Mosquitto Add-on (MQTT Broker)    │  │
│  │  - Custom Integration                │  │
│  │  - Subscribes to MQTT topics         │  │
│  └──────────────────────────────────────┘  │
│                                             │
│  ┌──────────────────────────────────────┐  │
│  │  Docker Stack (on server)            │  │
│  │  - Tesla Fleet Telemetry (HTTPS)     │  │
│  │  - Publishes to MQTT broker          │  │
│  └──────────────────────────────────────┘  │
│                                             │
│  Internet ← tesla-telemetry.yourdomain.com  │
└─────────────────────────────────────────────┘
```

**Why this approach?**
- ✅ Simple setup (MQTT broker already in HA)
- ✅ Fast iteration (easy to restart/debug)
- ✅ Safe testing environment (separate from production HA)
- ✅ Low resource usage (no additional services)
- ✅ Easy migration to production later

---

## Prerequisites

### Required Information
- [ ] Tesla VIN: `_______________________` (17 characters)
- [ ] Domain: `tesla-telemetry.yourdomain.com` (configured in DNS)
- [ ] SSL Certificate: Ready or will use Let's Encrypt
- [ ] HA IP Address: `_______________________`
- [ ] Tesla Developer Account: ✅ Configured
- [ ] Virtual Key: ✅ Paired with vehicle

### Required Access
- [ ] SSH/Console access to server
- [ ] Docker installed
- [ ] Git installed
- [ ] Port 443 (HTTPS) forwarded to server
- [ ] Mosquitto add-on running in Home Assistant

---

## Phase 1: Deploy Server Stack (1-2 hours)

### Step 1.1: Access Server

```bash
# SSH into your server
ssh root@your-server-ip
```

### Step 1.2: Install Prerequisites

```bash
# Check Docker is installed
docker --version

# If not installed:
apt-get update
apt-get install -y docker.io docker-compose git

# Check git
git --version
```

### Step 1.3: Clone Repository

```bash
# Navigate to appropriate location
cd /opt

# Clone repository
git clone https://github.com/jjtortosa/seitor-tesla-telemetry.git tesla-telemetry
cd tesla-telemetry/server
```

### Step 1.4: Configure Server

```bash
# Run interactive setup
./setup.sh
```

The script will prompt for:
- **Domain**: `tesla-telemetry.yourdomain.com`
- **MQTT Broker Host**: Your Home Assistant IP (e.g., `192.168.1.50`)
- **MQTT Port**: `1883`
- **MQTT Username**: Your Mosquitto username
- **MQTT Password**: Your Mosquitto password
- **MQTT Topic Base**: `tesla` (default)

**Verify configuration**:
```bash
# Check config.json
cat config.json

# Should show MQTT configuration like:
# "mqtt": {
#   "broker": "192.168.1.50:1883",
#   "username": "mqtt_user",
#   "topic_base": "tesla"
# }
```

### Step 1.5: Prepare SSL Certificates

**Option A: Existing Certificate**
```bash
# Copy your SSL certificate files to server/certs/
mkdir -p certs
cp /path/to/fullchain.pem certs/
cp /path/to/privkey.pem certs/
chmod 644 certs/fullchain.pem
chmod 600 certs/privkey.pem
```

**Option B: Let's Encrypt (Certbot)**
```bash
# Install certbot
apt-get install -y certbot

# Generate certificate (stop any service using port 443 first)
certbot certonly --standalone -d tesla-telemetry.yourdomain.com

# Copy to server directory
mkdir -p certs
cp /etc/letsencrypt/live/tesla-telemetry.yourdomain.com/fullchain.pem certs/
cp /etc/letsencrypt/live/tesla-telemetry.yourdomain.com/privkey.pem certs/
```

### Step 1.6: Start Docker Stack

```bash
# Start fleet-telemetry service
docker compose up -d

# Verify container is running
docker compose ps

# Expected output:
# NAME              STATUS         PORTS
# fleet-telemetry   Up (healthy)   0.0.0.0:443->443/tcp
```

### Step 1.7: Verify Services

```bash
# Check HTTPS endpoint
curl -k https://localhost:443/health
# Expected: {"status": "ok"}

# Check external access
curl -k https://tesla-telemetry.yourdomain.com/health

# Check logs for MQTT connection
docker compose logs -f fleet-telemetry
# Should show: "MQTT connection established" or similar
```

### Step 1.8: Test MQTT Connectivity

```bash
# From Home Assistant terminal, test MQTT subscription
mosquitto_sub -h localhost -t "tesla/#" -v

# Keep this running to see messages when vehicle connects
```

---

## Phase 2: Install HA Integration (30 minutes)

### Step 2.1: Access Home Assistant

Navigate to your Home Assistant web interface.

### Step 2.2: Ensure MQTT is Configured

1. Go to **Settings → Add-ons**
2. Verify **Mosquitto broker** is installed and running
3. Go to **Settings → Devices & Services**
4. Verify **MQTT** integration is configured

### Step 2.3: Copy Integration Files

**From HA Terminal or SSH**:
```bash
# Navigate to config directory
cd /config

# Clone repository
git clone https://github.com/jjtortosa/seitor-tesla-telemetry.git

# Copy custom component
mkdir -p custom_components
cp -r seitor-tesla-telemetry/ha-integration/custom_components/tesla_telemetry_local \
      custom_components/

# Verify files
ls -la custom_components/tesla_telemetry_local/
# Should see: __init__.py, manifest.json, config_flow.py, mqtt_client.py, etc.
```

### Step 2.4: Restart Home Assistant

```bash
ha core restart
```

Or via UI: **Settings → System → Restart**

### Step 2.5: Add Integration via UI

1. Go to **Settings → Devices & Services**
2. Click **Add Integration**
3. Search for **Tesla Fleet Telemetry Local**
4. Enter configuration:
   - **MQTT Topic Base**: `tesla` (must match server config)
   - **Vehicle VIN**: Your 17-character VIN
   - **Vehicle Name**: Friendly name (e.g., "MelanY")
5. Click **Submit**

### Step 2.6: Verify Integration Loaded

Check the integration shows with 13 entities:
- 1 device_tracker
- 8 sensors
- 4 binary_sensors

Enable debug logging if needed:
```yaml
# In configuration.yaml
logger:
  default: info
  logs:
    custom_components.tesla_telemetry_local: debug
```

---

## Phase 3: Validate Connection (1 hour)

### Step 3.1: Monitor MQTT Messages

**Terminal 1**: Monitor MQTT from HA
```bash
mosquitto_sub -h localhost -t "tesla/#" -v
```

**Expected**:
- If no messages yet: "Waiting for messages..."
- If vehicle is sending: Messages like `tesla/VIN/v/BatteryLevel {"value": 78}`

### Step 3.2: Trigger Vehicle Activity

**To generate telemetry messages**:
1. Get in your Tesla
2. Turn on climate control (wake up vehicle)
3. Check phone app shows "Awake"
4. Start driving (or just shift to Drive and back to Park)

**Tesla should start sending telemetry within 1-2 minutes**.

### Step 3.3: Monitor HA Logs

**Terminal 2**: Watch Home Assistant logs
```bash
tail -f /config/home-assistant.log | grep tesla_telemetry_local
```

**Expected logs when messages arrive**:
```
[tesla_telemetry_local] MQTT message received: tesla/VIN/v/BatteryLevel
[tesla_telemetry_local] Updated sensor.melany_battery: 80
[tesla_telemetry_local] MQTT message received: tesla/VIN/v/VehicleSpeed
[tesla_telemetry_local] Updated sensor.melany_speed: 0
```

### Step 3.4: Check Entities in Home Assistant

Via **Developer Tools → States**:

Search for your vehicle name and verify:
- `device_tracker.melany_location` - Shows coordinates
- `sensor.melany_speed` - Shows speed
- `sensor.melany_battery` - Shows battery %
- `binary_sensor.melany_driving` - Shows on/off

---

## Phase 4: Test Scenarios (2-3 hours)

### Scenario 1: Parked (Baseline)

**Action**: Vehicle parked, locked, not charging

**Verify** (via Developer Tools → States):
- `sensor.melany_speed` = 0
- `sensor.melany_shift_state` = P
- `binary_sensor.melany_driving` = off
- `binary_sensor.melany_charging` = off
- `sensor.melany_battery` = current %

### Scenario 2: Driving

**Action**: Start driving the vehicle

**Verify**:
- [ ] `sensor.melany_speed` changes (matches dashboard)
- [ ] `sensor.melany_shift_state` = D (or R if reversing)
- [ ] `binary_sensor.melany_driving` = on
- [ ] `device_tracker.melany_location` updates every ~5-10 seconds
- [ ] Location appears on HA map

**Check latency**:
```
Compare vehicle dashboard time vs HA state update
Goal: <5 seconds lag
```

### Scenario 3: Charging

**Action**: Plug in charger at home

**Verify**:
- `binary_sensor.melany_charging` = on
- `sensor.melany_charging_state` = Charging
- `sensor.melany_charger_voltage` = shows voltage
- `sensor.melany_charger_current` = shows amperage

**Monitor charging progress**:
Watch battery level increase over time.

### Scenario 4: Zones

**Action**: Drive to different zones (work, grocery, etc.)

**Verify**:
- [ ] `device_tracker.melany_location` state changes to zone name
- [ ] Zone enter/exit triggers work
- [ ] History shows movement between zones

---

## Phase 5: Create Automations (1 hour)

### Test Automation 1: Arrival Notification

Via UI: **Settings → Automations & Scenes → Create Automation**

Or YAML:
```yaml
automation:
  - alias: "Test: MelanY Arrived Home"
    trigger:
      - platform: zone
        entity_id: device_tracker.melany_location
        zone: zone.home
        event: enter
    action:
      - service: notify.persistent_notification
        data:
          title: "Tesla Arrived"
          message: "MelanY has arrived home at {{ now().strftime('%H:%M') }}"
```

**Test**:
1. Drive away from home
2. Drive back
3. Check for notification in HA

### Test Automation 2: Charging Started

```yaml
automation:
  - alias: "Test: Charging Started"
    trigger:
      - platform: state
        entity_id: binary_sensor.melany_charging
        from: 'off'
        to: 'on'
    action:
      - service: notify.persistent_notification
        data:
          title: "Tesla Charging"
          message: "MelanY started charging at {{ states('sensor.melany_battery') }}%"
```

**Test**:
1. Unplug charger
2. Plug in charger
3. Check for notification

### Test Automation 3: Low Battery Alert

```yaml
automation:
  - alias: "Test: Low Battery Warning"
    trigger:
      - platform: numeric_state
        entity_id: sensor.melany_battery
        below: 20
    condition:
      - condition: state
        entity_id: binary_sensor.melany_charging
        state: 'off'
    action:
      - service: notify.persistent_notification
        data:
          title: "Low Battery"
          message: "MelanY battery is {{ states('sensor.melany_battery') }}%. Please charge soon."
```

---

## Phase 6: Performance & Troubleshooting

### Monitor Performance

```bash
# Check Docker resource usage
docker stats

# Check MQTT message rate
mosquitto_sub -h localhost -t "tesla/#" -v | pv -l -i 10 > /dev/null
# Shows messages per second

# Check HA memory/CPU
docker exec -it homeassistant top
```

### Common Issues

**Issue 1: No messages received**
```bash
# Check Fleet Telemetry logs
docker compose logs -f fleet-telemetry

# Check MQTT connectivity from server
nc -zv 192.168.1.50 1883

# Test MQTT subscription
mosquitto_sub -h 192.168.1.50 -u mqtt_user -P mqtt_password -t "tesla/#" -v
```

**Issue 2: Integration not updating**
```bash
# Check MQTT integration in HA
# Settings → Devices & Services → MQTT → should show "Connected"

# Check integration logs
tail -f /config/home-assistant.log | grep tesla_telemetry_local

# Verify topic base matches
# Server config.json and HA integration must use same topic_base
```

**Issue 3: High latency**
```bash
# Check network latency
ping -c 10 192.168.1.50

# Check MQTT QoS setting
# QoS 1 (at least once) recommended for reliability

# Check HA system load
# Reduce other integrations or increase resources
```

---

## Migration to Production

When testing is successful on HA Test:

### Quick Migration Steps

1. **On Production HA**:
   - Install Mosquitto add-on (if not installed)
   - Copy custom component files
   - Add integration via UI

2. **Update server config** (if HA IP differs):
   ```json
   {
     "mqtt": {
       "broker": "PRODUCTION_HA_IP:1883"
     }
   }
   ```

3. **Restart Fleet Telemetry**:
   ```bash
   docker compose restart fleet-telemetry
   ```

4. **Copy automations** from HA Test to Production

---

## Success Criteria

Before considering testing complete, verify:

- [ ] ✅ MQTT receives messages from Tesla (via Fleet Telemetry)
- [ ] ✅ JSON parsing works without errors
- [ ] ✅ All 13 entities created and updating
- [ ] ✅ Latency <5 seconds
- [ ] ✅ Automations trigger correctly
- [ ] ✅ System stable for 24+ hours
- [ ] ✅ No memory leaks or resource issues

---

## Next Steps After Successful Testing

1. **Document your setup**:
   - Note any configuration tweaks
   - Record actual latency measurements
   - List which fields are most useful

2. **Create production automations**:
   - Garage door opener
   - Preconditioning triggers
   - Charging schedules
   - Location-based automations

3. **Consider migration to Production HA**:
   - Repeat Phase 2 on production HA
   - Copy tested automations
   - Monitor for 1 week

4. **Optional enhancements**:
   - Add more sensors from telemetry fields
   - Create Lovelace dashboard
   - Set up alerts for anomalies

---

**Happy Testing!** 🚗⚡

If you encounter issues, check:
- `/config/home-assistant.log` on Home Assistant
- `docker compose logs -f` for server stack
- `mosquitto_sub -h localhost -t "tesla/#" -v` for raw MQTT messages
