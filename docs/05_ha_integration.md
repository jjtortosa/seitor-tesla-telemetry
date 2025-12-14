# Home Assistant Integration

This guide covers installing and configuring the custom Home Assistant integration to consume Tesla telemetry data via MQTT.

## Prerequisites

- ✅ Fleet Telemetry server running and publishing to MQTT
- ✅ MQTT broker (Mosquitto add-on) installed and configured in HA
- ✅ Home Assistant instance running
- ✅ Access to Home Assistant configuration directory

**Estimated time**: 15-30 minutes

---

## Overview

The custom integration consists of:

1. **MQTT Client**: Subscribes to Tesla telemetry topics via HA's built-in MQTT integration
2. **Entity Manager**: Creates and updates Home Assistant entities:
   - `device_tracker` for GPS location
   - `sensor` for speed, battery, range, etc.
   - `binary_sensor` for driving state, charging state, connectivity

**Data flow**:
```
MQTT Broker → HA MQTT Integration → Tesla Telemetry Local → Entity Updates → Automations
```

---

## Step 1: Install MQTT (if not already done)

### 1.1 Install Mosquitto Add-on

1. Go to **Settings → Add-ons → Add-on Store**
2. Search for "Mosquitto broker"
3. Click **Install**
4. Start the add-on

### 1.2 Configure MQTT Integration

1. Go to **Settings → Devices & Services**
2. Click **Add Integration**
3. Search for "MQTT"
4. Follow the setup wizard (usually auto-discovers Mosquitto)

### 1.3 Verify MQTT is Working

```bash
# From HA terminal or SSH
mosquitto_sub -h localhost -t "tesla/#" -v
```

You should see messages when your Tesla is sending data.

---

## Step 2: Copy Integration Files

### 2.1 Clone Repository to Home Assistant

**On Home Assistant host**:

```bash
cd /config  # Or wherever your HA config directory is

# Clone repository
git clone https://github.com/jjtortosa/seitor-tesla-telemetry.git
```

### 2.2 Copy Integration to custom_components

```bash
cd /config

# Create custom_components directory if it doesn't exist
mkdir -p custom_components

# Copy integration
cp -r seitor-tesla-telemetry/ha-integration/custom_components/tesla_telemetry_local \
      custom_components/
```

### 2.3 Verify Structure

```bash
ls -la custom_components/tesla_telemetry_local/
```

**Expected files**:
```
__init__.py           # Integration setup
manifest.json         # Metadata and dependencies
config_flow.py        # Config Flow UI
device_tracker.py     # Location entity
sensor.py             # Sensors (speed, battery, etc.)
binary_sensor.py      # Binary sensors (driving, charging)
mqtt_client.py        # MQTT subscription handler
const.py              # Constants
strings.json          # UI strings
translations/         # Translations
```

---

## Step 3: Add Integration via UI

### 3.1 Restart Home Assistant

```bash
ha core restart
```

### 3.2 Add Integration

1. Go to **Settings → Devices & Services**
2. Click **Add Integration**
3. Search for "Tesla Fleet Telemetry Local"
4. Enter configuration:
   - **MQTT Topic Base**: `tesla` (must match server config)
   - **Vehicle VIN**: Your 17-character VIN
   - **Vehicle Name**: Friendly name (e.g., "MelanY")

### 3.3 Verify Setup

After adding, you should see the integration with 13 entities.

---

## Step 4: Verify Entities Created

### 4.1 Check Devices & Services

Go to **Settings → Devices & Services → Tesla Fleet Telemetry Local**

**Expected entities (13 total)**:

#### Device Tracker
- `device_tracker.VEHICLENAME_location` - GPS location

#### Sensors (8)
- `sensor.VEHICLENAME_speed` - Speed (km/h)
- `sensor.VEHICLENAME_shift_state` - Current gear (P/D/R/N)
- `sensor.VEHICLENAME_battery` - Battery level (%)
- `sensor.VEHICLENAME_range` - Estimated range (km)
- `sensor.VEHICLENAME_charging_state` - Charging status
- `sensor.VEHICLENAME_charger_voltage` - Charger voltage (V)
- `sensor.VEHICLENAME_charger_current` - Charger current (A)
- `sensor.VEHICLENAME_odometer` - Vehicle odometer (km)

#### Binary Sensors (4)
- `binary_sensor.VEHICLENAME_driving` - Driving state (on/off)
- `binary_sensor.VEHICLENAME_charging` - Charging state (on/off)
- `binary_sensor.VEHICLENAME_charge_port_open` - Charge port open (on/off)
- `binary_sensor.VEHICLENAME_connected` - Vehicle connectivity (on/off)

### 4.2 Check Entity States

Go to: **Developer Tools → States**

Search for your vehicle name and verify values are updating.

---

## Step 5: Test Real-Time Updates

### 5.1 Drive Vehicle

1. Start your Tesla and shift to Drive
2. Move the vehicle a few meters

### 5.2 Monitor Entity Updates in HA

**Via Developer Tools → States**:

Watch these entities update in real-time (<1-5 seconds):
- `sensor.VEHICLENAME_shift_state`: Changes from `P` → `D`
- `sensor.VEHICLENAME_speed`: Changes from `0` → actual speed
- `binary_sensor.VEHICLENAME_driving`: Changes from `off` → `on`
- `device_tracker.VEHICLENAME_location`: GPS coordinates update

---

## Step 6: Create Automations

Now that entities are updating in real-time, create automations!

### 6.1 Garage Door Automation (Example)

```yaml
- id: tesla_garage_door_automation
  alias: "Tesla: Open garage when arriving home"
  description: Opens garage door when Tesla enters home zone
  mode: single
  trigger:
    - platform: zone
      entity_id: device_tracker.melany_location
      zone: zone.home
      event: enter
  condition:
    - condition: time
      after: "07:45:00"
      before: "23:30:00"
  action:
    - service: cover.open_cover
      target:
        entity_id: cover.garage_door
    - service: notify.mobile_app
      data:
        title: "Garage"
        message: "Opening garage door for MelanY"
```

### 6.2 Low Battery Alert (Example)

```yaml
- id: tesla_low_battery_alert
  alias: "Tesla: Low battery warning"
  mode: single
  trigger:
    - platform: numeric_state
      entity_id: sensor.melany_battery
      below: 20
  condition:
    - condition: state
      entity_id: binary_sensor.melany_charging
      state: "off"
  action:
    - service: notify.mobile_app
      data:
        title: "Low Battery"
        message: "MelanY battery is {{ states('sensor.melany_battery') }}%. Please charge soon."
```

---

## Step 7: Create Dashboard Card

### 7.1 Entities Card

```yaml
type: entities
title: MelanY
entities:
  - entity: device_tracker.melany_location
    name: Location
  - entity: sensor.melany_shift_state
    name: Gear
  - entity: sensor.melany_speed
    name: Speed
  - entity: sensor.melany_battery
    name: Battery
    icon: mdi:battery
  - entity: sensor.melany_range
    name: Range
    icon: mdi:map-marker-distance
  - entity: binary_sensor.melany_driving
    name: Driving
  - entity: binary_sensor.melany_charging
    name: Charging
```

### 7.2 Map Card

```yaml
type: map
entities:
  - device_tracker.melany_location
hours_to_show: 24
default_zoom: 15
```

---

## Step 8: Monitoring and Troubleshooting

### 8.1 Check Integration Status

**Via Logs**:

```bash
tail -f /config/home-assistant.log | grep tesla_telemetry_local
```

**Look for**:
- ✅ `MQTT message received` (confirms messages arriving)
- ✅ `Entity updated` (confirms parsing working)
- ❌ `MQTT not configured` (MQTT integration missing)

### 8.2 Enable Debug Logging

Add to `/config/configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.tesla_telemetry_local: debug
```

Restart HA, then check logs for detailed debug info.

### 8.3 Monitor MQTT Messages

```bash
# From HA terminal
mosquitto_sub -h localhost -t "tesla/#" -v
```

Expected output:
```
tesla/LRWYGCFS3RC210528/v/BatteryLevel {"value": 78}
tesla/LRWYGCFS3RC210528/v/VehicleSpeed {"value": 0}
tesla/LRWYGCFS3RC210528/v/Location {"latitude": 41.38, "longitude": 2.17}
```

---

## Troubleshooting

### Integration not showing in Add Integration

**Problem**: "Tesla Fleet Telemetry Local" doesn't appear

**Check**:
1. Files copied correctly to `/config/custom_components/tesla_telemetry_local/`
2. Restart Home Assistant after copying files
3. Check logs for import errors

### Entities not created

**Problem**: Integration loads but no entities appear

**Check**:
1. MQTT integration is configured
2. Vehicle VIN is correct (17 characters)
3. MQTT messages are arriving (use mosquitto_sub)

### Entities not updating

**Problem**: Entities exist but values don't change

**Check**:
1. MQTT messages arriving: `mosquitto_sub -h localhost -t "tesla/#" -v`
2. Topic base matches server configuration
3. VIN matches the vehicle sending data

### High latency (updates slow)

**Problem**: Entity updates take 10+ seconds

**Possible causes**:
1. MQTT QoS settings
2. Network latency
3. HA overloaded

**Solutions**:
- Check Fleet Telemetry logs
- Verify MQTT broker is local to HA
- Increase HA resources if needed

---

## Next Steps

Integration complete! Your Home Assistant now has real-time Tesla data.

### Recommended Next Steps:

1. **Create more automations**:
   - Charging optimization based on electricity rates
   - Pre-conditioning before departure
   - Location-based scenes (arriving home, leaving work)

2. **Build advanced dashboard**:
   - Charging history graph
   - Trip tracker
   - Battery monitoring

3. **Integrate with other systems**:
   - Solar production (charge when excess solar)
   - Calendar (pre-condition before events)
   - Weather (adjust HVAC based on forecast)

### Reference Documentation:

- [Troubleshooting Guide](06_troubleshooting.md)

---

**Congratulations!** You now have a fully functional self-hosted Tesla Fleet Telemetry system with Home Assistant integration!
