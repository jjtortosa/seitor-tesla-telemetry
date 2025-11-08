# Real-World Testing Guide - HA Test Deployment

This guide covers testing the Tesla Fleet Telemetry integration on your **Home Assistant Test instance** with the server stack running on the same machine.

## Overview

**Deployment Architecture**:
```
┌─────────────────────────────────────────────┐
│     HA Test (Proxmox Container)             │
│                                             │
│  ┌──────────────────────────────────────┐  │
│  │  Home Assistant                      │  │
│  │  - Custom Integration                │  │
│  │  - Connects to localhost:9092        │  │
│  └──────────────────────────────────────┘  │
│                                             │
│  ┌──────────────────────────────────────┐  │
│  │  Docker Stack (localhost)            │  │
│  │  - Kafka (port 9092)                 │  │
│  │  - Tesla Fleet Telemetry             │  │
│  │  - Nginx (HTTPS proxy)               │  │
│  └──────────────────────────────────────┘  │
│                                             │
│  Internet ← tesla-telemetry.seitor.com     │
└─────────────────────────────────────────────┘
```

**Why this approach?**
- ✅ Simple setup (everything in one place)
- ✅ Fast iteration (easy to restart/debug)
- ✅ Safe testing environment (separate from production HA)
- ✅ Easy migration to Ubuntu Server later if needed

---

## Prerequisites

### Required Information
- [ ] Tesla VIN: `_______________________` (17 characters)
- [ ] Domain: `tesla-telemetry.seitor.com` (configured in DNS)
- [ ] SSL Certificate: Ready or will use Let's Encrypt
- [ ] HA Test IP: `_______________________`
- [ ] Tesla Developer Account: ✅ Configured
- [ ] Virtual Key: ✅ Paired with vehicle

### Required Access
- [ ] SSH/Console access to HA Test container
- [ ] Docker installed on HA Test
- [ ] Git installed on HA Test
- [ ] Ports 9092 (Kafka) and 443 (HTTPS) available

---

## Phase 1: Deploy Server Stack (1-2 hours)

### Step 1.1: Access HA Test Container

```bash
# From Proxmox host
pct enter <CONTAINER_ID>

# Or via SSH
ssh root@<HA_TEST_IP>
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
cd /opt  # or /root, your choice

# Clone repository
git clone https://github.com/jjtortosa/seitor-tesla-telemetry.git
cd seitor-tesla-telemetry
```

### Step 1.4: Configure Server

```bash
cd server

# Review docker-compose.yml
cat docker-compose.yml

# Review config.json (Tesla Fleet Telemetry config)
cat config.json
```

**Important**: Verify `config.json` contains:
- Correct hostname: `tesla-telemetry.seitor.com`
- Correct Kafka broker: `kafka:9092` (internal Docker network)
- SSL certificate paths are correct

### Step 1.5: Prepare SSL Certificates

**Option A: Existing Certificate**
```bash
# Copy your SSL certificate files to server/certs/
mkdir -p certs
cp /path/to/your/cert.pem certs/
cp /path/to/your/key.pem certs/
```

**Option B: Let's Encrypt (Certbot)**
```bash
# Install certbot
apt-get install -y certbot

# Generate certificate
certbot certonly --standalone -d tesla-telemetry.seitor.com

# Copy to server directory
mkdir -p certs
cp /etc/letsencrypt/live/tesla-telemetry.seitor.com/fullchain.pem certs/cert.pem
cp /etc/letsencrypt/live/tesla-telemetry.seitor.com/privkey.pem certs/key.pem
```

### Step 1.6: Start Docker Stack

```bash
# Start all services
docker-compose up -d

# Verify all containers are running
docker-compose ps

# Expected output:
# NAME                STATUS
# kafka               Up
# fleet-telemetry     Up
# nginx               Up (or similar names)
```

### Step 1.7: Verify Services

```bash
# Check Kafka is listening
netstat -tuln | grep 9092
# Expected: LISTEN on 0.0.0.0:9092

# Check HTTPS endpoint
curl -k https://localhost/status
# or
curl https://tesla-telemetry.seitor.com/status

# Check logs
docker-compose logs -f fleet-telemetry
# Should show: "Server started on port 443" or similar
```

### Step 1.8: Test Kafka Connectivity

```bash
# From inside HA Test container
nc -zv localhost 9092

# Expected output:
# Connection to localhost 9092 port [tcp/*] succeeded!
```

---

## Phase 2: Install HA Integration (30 minutes)

### Step 2.1: Access Home Assistant Container

```bash
# If HA is also running in Docker on HA Test
docker exec -it homeassistant bash

# Or if HA is the main process, just navigate to /config
cd /config
```

### Step 2.2: Copy Integration Files

```bash
# Navigate to config directory
cd /config

# Clone repository (if not already cloned)
git clone https://github.com/jjtortosa/seitor-tesla-telemetry.git

# Copy custom component
mkdir -p custom_components
cp -r seitor-tesla-telemetry/ha-integration/custom_components/tesla_telemetry_local \
      custom_components/

# Verify files
ls -la custom_components/tesla_telemetry_local/
# Should see: __init__.py, manifest.json, kafka_consumer.py, etc.
```

### Step 2.3: Install Python Dependencies

```bash
# Still inside HA container
pip3 install kafka-python==2.0.2 protobuf>=5.27.0

# Verify installation
pip3 list | grep -E "kafka|protobuf"
# Expected:
# kafka-python    2.0.2
# protobuf        6.33.0 (or >=5.27.0)
```

### Step 2.4: Configure Integration

Edit `/config/configuration.yaml`:

```yaml
# Add at the end of the file
tesla_telemetry_local:
  kafka_broker: "localhost:9092"          # Kafka is on same machine
  kafka_topic: "tesla_telemetry"          # Default topic
  vehicle_vin: "YOUR_TESLA_VIN_HERE"      # Replace with your VIN
  vehicle_name: "MelanY"                  # Your vehicle name

# Enable debug logging
logger:
  default: info
  logs:
    custom_components.tesla_telemetry_local: debug
```

**IMPORTANT**: Replace `YOUR_TESLA_VIN_HERE` with your actual Tesla VIN (17 characters).

### Step 2.5: Restart Home Assistant

```bash
# Exit from HA container
exit

# Restart Home Assistant
ha core restart

# Or if using Docker directly:
docker restart homeassistant
```

### Step 2.6: Verify Integration Loaded

```bash
# Wait ~30 seconds for HA to restart

# Check logs
docker exec -it homeassistant tail -f /config/home-assistant.log | grep tesla_telemetry_local

# Expected logs:
# "Setting up tesla_telemetry_local"
# "Connecting to Kafka broker: localhost:9092"
# "Successfully connected to Kafka broker"
```

---

## Phase 3: Validate Connection (1 hour)

### Step 3.1: Monitor Kafka Messages

**Terminal 1**: Monitor Kafka from tools
```bash
cd /opt/seitor-tesla-telemetry/tools/testing

# Install dependencies if needed
pip3 install kafka-python protobuf>=5.27.0

# Start debugger
python3 kafka_debugger.py --broker localhost:9092 --from-beginning
```

**Expected**:
- If no messages yet: "Waiting for messages..."
- If vehicle is sending: See Protobuf parsed messages

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
docker exec -it homeassistant tail -f /config/home-assistant.log | grep tesla_telemetry_local
```

**Expected logs when messages arrive**:
```
[tesla_telemetry_local] Received telemetry message: offset=0, fields=['Location', 'VehicleSpeed', 'Gear', 'Soc', ...]
[tesla_telemetry_local] Updated device_tracker.melany_location: (41.3874, 2.1686)
[tesla_telemetry_local] Updated sensor.melany_speed: 0
[tesla_telemetry_local] Updated sensor.melany_battery: 80
```

### Step 3.4: Check Entities in Home Assistant

```bash
# List all entities
ha state list | grep melany

# Check specific entities
ha state get device_tracker.melany_location
ha state get sensor.melany_speed
ha state get sensor.melany_battery
ha state get binary_sensor.melany_driving
```

**Expected output**:
```json
{
  "entity_id": "device_tracker.melany_location",
  "state": "home",
  "attributes": {
    "latitude": 41.3874,
    "longitude": 2.1686,
    "gps_accuracy": 0,
    "source_type": "gps",
    "friendly_name": "MelanY Location"
  }
}
```

---

## Phase 4: Test Scenarios (2-3 hours)

### Scenario 1: Parked (Baseline)

**Action**: Vehicle parked, locked, not charging

**Verify**:
```bash
# Check states
ha state get sensor.melany_speed              # Should be: 0
ha state get sensor.melany_shift_state        # Should be: P
ha state get binary_sensor.melany_driving     # Should be: off
ha state get binary_sensor.melany_charging    # Should be: off
ha state get sensor.melany_battery            # Should show current %
```

### Scenario 2: Driving

**Action**: Start driving the vehicle

**Verify**:
- [ ] `sensor.melany_speed` changes (matches dashboard)
- [ ] `sensor.melany_shift_state` = D (or R if reversing)
- [ ] `binary_sensor.melany_driving` = on
- [ ] `device_tracker.melany_location` updates every ~5-10 seconds
- [ ] Location appears on HA map

**Check latency**:
```bash
# Compare vehicle dashboard time vs HA state update
# Goal: <5 seconds lag
```

### Scenario 3: Charging

**Action**: Plug in charger at home

**Verify**:
```bash
ha state get binary_sensor.melany_charging        # Should be: on
ha state get sensor.melany_charging_state         # Should be: Charging
ha state get sensor.melany_charger_voltage        # Should show voltage
ha state get sensor.melany_charger_current        # Should show amperage
```

**Monitor charging progress**:
```bash
# Watch battery level increase
watch -n 10 'ha state get sensor.melany_battery'
```

### Scenario 4: Zones

**Action**: Drive to different zones (work, grocery, etc.)

**Verify**:
- [ ] `device_tracker.melany_location` state changes to zone name
- [ ] Zone enter/exit triggers work
- [ ] History shows movement between zones

---

## Phase 5: Create Automations (1 hour)

### Test Automation 1: Arrival Notification

Edit `/config/configuration.yaml`:

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

# Check HA memory/CPU
docker exec -it homeassistant top

# Check Kafka consumer lag
docker exec -it kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --group ha_tesla_YOUR_VIN \
  --describe
```

### Common Issues

**Issue 1: No messages received**
```bash
# Check Fleet Telemetry logs
docker logs -f fleet-telemetry

# Check Kafka topics
docker exec -it kafka kafka-topics --list --bootstrap-server localhost:9092

# Should see: tesla_telemetry

# Check messages in Kafka
docker exec -it kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic tesla_telemetry \
  --from-beginning \
  --max-messages 1
```

**Issue 2: Parse errors**
```bash
# Check Protobuf version
docker exec -it homeassistant pip3 show protobuf

# Should be >=5.27.0

# Re-install if needed
docker exec -it homeassistant pip3 install --upgrade protobuf
```

**Issue 3: High latency**
```bash
# Check network latency
docker exec -it homeassistant ping localhost

# Check Kafka performance
docker exec -it kafka kafka-broker-api-versions --bootstrap-server localhost:9092
```

---

## Migration to Ubuntu Server (Plan B)

If HA Test struggles with resources or you want to separate concerns:

### Quick Migration Steps

1. **Deploy to Ubuntu Server**:
   ```bash
   # On Ubuntu Server
   cd /opt
   git clone https://github.com/jjtortosa/seitor-tesla-telemetry.git
   cd seitor-tesla-telemetry/server
   docker-compose up -d
   ```

2. **Update HA configuration**:
   ```yaml
   # In HA Test configuration.yaml
   tesla_telemetry_local:
     kafka_broker: "UBUNTU_SERVER_IP:9092"  # Changed from localhost
     # rest stays the same
   ```

3. **Restart HA**:
   ```bash
   ha core restart
   ```

4. **Stop services on HA Test**:
   ```bash
   # On HA Test
   cd /opt/seitor-tesla-telemetry/server
   docker-compose down
   ```

**That's it!** The integration will now connect to Ubuntu Server instead.

---

## Success Criteria

Before considering testing complete, verify:

- [ ] ✅ Kafka receives messages from Tesla
- [ ] ✅ Protobuf parsing works without errors
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

3. **Consider migration to HA Real**:
   - Repeat Phase 2 on production HA
   - Copy tested automations
   - Monitor for 1 week

4. **Optional enhancements**:
   - Add more sensors from Protobuf fields
   - Create Lovelace dashboard
   - Set up alerts for anomalies

---

**Happy Testing!** 🚗⚡

If you encounter issues, check:
- `/config/home-assistant.log` on HA Test
- `docker-compose logs -f` for server stack
- `tools/testing/kafka_debugger.py` for raw Kafka messages
