# Home Assistant Integration

This guide covers installing and configuring the custom Home Assistant integration to consume Tesla telemetry data from Kafka.

## Prerequisites

- ✅ Fleet Telemetry server running and receiving data
- ✅ Kafka receiving messages (verified in previous step)
- ✅ Home Assistant instance running
- ✅ Access to Home Assistant configuration directory

**Estimated time**: 1-2 hours

---

## Overview

The custom integration consists of:

1. **Kafka Consumer**: Connects to Kafka broker, subscribes to `tesla_telemetry` topic
2. **Protobuf Parser**: Decodes binary messages using Tesla's vehicle_data.proto schema
3. **Entity Manager**: Creates and updates Home Assistant entities:
   - `device_tracker` for GPS location
   - `sensor` for speed, battery, range, etc.
   - `binary_sensor` for driving state, charging state, connectivity

**Data flow**:
```
Kafka → Kafka Consumer → Protobuf Parser → Entity Updates → HA State Machine → Automations
```

---

## Step 1: Install Python Dependencies

The integration requires Python libraries for Kafka and Protobuf.

### 1.1 Access Home Assistant Container/Host

**If running Home Assistant Container**:

```bash
docker exec -it homeassistant bash
```

**If running Home Assistant OS/Supervised**: Use terminal add-on or SSH.

**If running Home Assistant Core** (venv):

```bash
# Activate venv
source /srv/homeassistant/bin/activate
```

### 1.2 Install Dependencies

```bash
# Install kafka-python and protobuf
pip3 install kafka-python==2.0.2 protobuf>=5.27.0
```

**Verify installation**:

```bash
python3 -c "import kafka; print(kafka.__version__)"
# Should output: 2.0.2

python3 -c "import google.protobuf; print(google.protobuf.__version__)"
# Should output: 4.25.1
```

⚠️ **Note**: These dependencies will need to be reinstalled after Home Assistant updates. Consider using HACS or packaging as a proper integration with `manifest.json` requirements.

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
device_tracker.py     # Location entity
sensor.py             # Sensors (speed, battery, etc.)
binary_sensor.py      # Binary sensors (driving, charging)
kafka_consumer.py     # Kafka client
vehicle_data_pb2.py   # Compiled Protobuf schema
```

⚠️ **Note**: Since the integration is still being developed, these files will be created in future commits. For now, you'll need to create placeholder files or wait for the complete integration.

---

## Step 3: Configure Integration

### 3.1 Add to configuration.yaml

```bash
nano /config/configuration.yaml
```

**Add**:

```yaml
# Tesla Fleet Telemetry Local Integration
tesla_telemetry_local:
  kafka_broker: "192.168.5.105:9092"  # Your Kafka broker IP:port
  kafka_topic: "tesla_telemetry"
  vehicle_vin: "5YJ3E1EA1MF000000"    # Your vehicle VIN
  vehicle_name: "MelanY"               # Friendly name for device
```

**Configuration options**:
- **kafka_broker**: IP and port of Kafka broker (from Proxmox container)
- **kafka_topic**: Kafka topic name (default: `tesla_telemetry`)
- **vehicle_vin**: Your Tesla VIN (used to filter messages if multiple vehicles)
- **vehicle_name**: Friendly name used in entity IDs

### 3.2 Validate Configuration

```bash
# Check configuration syntax
ha core check
```

Expected output:
```
✅ Configuration valid
```

---

## Step 4: Restart Home Assistant

### 4.1 Restart HA

**Via UI**:
1. Settings → System → Restart
2. Wait 1-2 minutes for restart

**Via CLI**:
```bash
ha core restart
```

### 4.2 Monitor Logs

```bash
# Follow Home Assistant logs
tail -f /config/home-assistant.log

# Or via CLI
ha core logs -f
```

**Look for**:
```
INFO (MainThread) [custom_components.tesla_telemetry_local] Loading Tesla Telemetry Local integration
INFO (MainThread) [custom_components.tesla_telemetry_local.kafka_consumer] Connecting to Kafka broker: 192.168.5.105:9092
INFO (MainThread) [custom_components.tesla_telemetry_local.kafka_consumer] Subscribed to topic: tesla_telemetry
INFO (MainThread) [custom_components.tesla_telemetry_local] Tesla Telemetry integration loaded successfully
```

---

## Step 5: Verify Entities Created

### 5.1 Check Developer Tools

1. Go to: **Settings → Devices & Services → Entities**
2. Filter by: `tesla_telemetry_local`

**Expected entities**:

#### Device Tracker
- `device_tracker.melany_location` - GPS location

#### Sensors
- `sensor.melany_shift_state` - Current gear (P/D/R/N)
- `sensor.melany_speed` - Speed (km/h)
- `sensor.melany_battery` - Battery level (%)
- `sensor.melany_range` - Estimated range (km)
- `sensor.melany_charging_state` - Charging status
- `sensor.melany_charger_voltage` - Charger voltage (V)
- `sensor.melany_charger_current` - Charger current (A)

#### Binary Sensors
- `binary_sensor.melany_driving` - Driving state (on/off)
- `binary_sensor.melany_charging` - Charging state (on/off)
- `binary_sensor.melany_charge_port_open` - Charge port open (on/off)
- `binary_sensor.melany_connected` - Vehicle connectivity (on/off)

### 5.2 Check Entity States

Go to: **Developer Tools → States**

Search for: `melany`

**Verify values are updating**:
- `device_tracker.melany_location`: Should show current zone (home, away, etc.)
- `sensor.melany_speed`: Should show current speed if driving
- `binary_sensor.melany_driving`: Should be `on` if driving, `off` if parked

---

## Step 6: Test Real-Time Updates

### 6.1 Drive Vehicle

1. Start your Tesla and shift to Drive
2. Move the vehicle a few meters

### 6.2 Monitor Entity Updates in HA

**Via Developer Tools → States**:

Watch these entities update in real-time (<1-5 seconds):
- `sensor.melany_shift_state`: Changes from `p` → `d`
- `sensor.melany_speed`: Changes from `0` → actual speed
- `binary_sensor.melany_driving`: Changes from `off` → `on`
- `device_tracker.melany_location`: GPS coordinates update

**Via Logbook**:

Go to: **History → Logbook**

Filter by: `melany`

You should see state changes as they happen:
```
10:15:32 - MelanY Shift State changed from P to D
10:15:33 - MelanY Driving changed from off to on
10:15:35 - MelanY Speed changed from 0 to 5 km/h
10:15:40 - MelanY Speed changed from 5 to 15 km/h
```

---

## Step 7: Create Automations

Now that entities are updating in real-time, create automations!

### 7.1 Garage Door Automation (Example)

Create file: `/config/automations.yaml` (or add via UI)

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
    - service: notify.mobile_app_jottie
      data:
        title: "🏠 Garage"
        message: "Opening garage door for MelanY"
```

**Test**:
1. Leave home with Tesla
2. Drive around the block
3. Return home and cross into `zone.home`
4. Garage door should open automatically! 🎉

### 7.2 Driving Notification (Example)

```yaml
- id: tesla_driving_notification
  alias: "Tesla: Notify when starts driving"
  mode: single
  trigger:
    - platform: state
      entity_id: binary_sensor.melany_driving
      from: "off"
      to: "on"
  action:
    - service: notify.mobile_app_jottie
      data:
        title: "🚗 MelanY"
        message: "Started driving. Current location: {{ states('device_tracker.melany_location') }}"
```

### 7.3 Low Battery Alert (Example)

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
    - service: notify.mobile_app_jottie
      data:
        title: "⚠️ Low Battery"
        message: "MelanY battery is {{ states('sensor.melany_battery') }}%. Please charge soon."
```

---

## Step 8: Create Dashboard Card

### 8.1 Add Tesla Card to Lovelace

Go to: **Overview (Lovelace) → Edit Dashboard → Add Card**

**Entities Card**:

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
  - entity: binary_sensor.melany_connected
    name: Connected
```

**Map Card** (for location):

```yaml
type: map
entities:
  - device_tracker.melany_location
hours_to_show: 24
default_zoom: 15
```

**Gauge Card** (for battery):

```yaml
type: gauge
entity: sensor.melany_battery
min: 0
max: 100
severity:
  green: 50
  yellow: 20
  red: 0
needle: true
```

---

## Step 9: Advanced Configuration

### 9.1 Customize Entity Names and Icons

Edit `/config/customize.yaml`:

```yaml
device_tracker.melany_location:
  friendly_name: "MelanY"
  icon: mdi:car-electric

sensor.melany_battery:
  friendly_name: "Battery"
  icon: mdi:battery-charging
  unit_of_measurement: "%"

sensor.melany_speed:
  friendly_name: "Speed"
  icon: mdi:speedometer
  unit_of_measurement: "km/h"

sensor.melany_shift_state:
  friendly_name: "Gear"
  icon: mdi:car-shift-pattern

binary_sensor.melany_driving:
  friendly_name: "Driving"
  icon: mdi:car-speed-limiter
  device_class: moving
```

### 9.2 Create Template Sensors (Optional)

For derived values, add to `/config/configuration.yaml`:

```yaml
template:
  - sensor:
      - name: "MelanY Charging Power"
        unique_id: melany_charging_power
        unit_of_measurement: "kW"
        state: >
          {% set voltage = states('sensor.melany_charger_voltage') | float(0) %}
          {% set current = states('sensor.melany_charger_current') | float(0) %}
          {{ (voltage * current / 1000) | round(2) }}
        availability: >
          {{ states('binary_sensor.melany_charging') == 'on' }}

      - name: "MelanY Time to Home"
        unique_id: melany_time_to_home
        unit_of_measurement: "min"
        state: >
          {% set speed = states('sensor.melany_speed') | float(0) %}
          {% set dist = distance('device_tracker.melany_location', 'zone.home') | float(0) %}
          {% if speed > 5 %}
            {{ ((dist / speed) * 60) | round(0) }}
          {% else %}
            unknown
          {% endif %}
```

---

## Step 10: Monitoring and Troubleshooting

### 10.1 Check Integration Status

**Via Logs**:

```bash
tail -f /config/home-assistant.log | grep tesla_telemetry_local
```

**Look for**:
- ✅ `Kafka message received` (confirms messages arriving)
- ✅ `Entity updated: sensor.melany_speed` (confirms parsing working)
- ❌ `Kafka connection error` (Kafka unreachable)
- ❌ `Protobuf decode error` (message parsing failed)

### 10.2 Enable Debug Logging

Add to `/config/configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.tesla_telemetry_local: debug
    kafka: debug
```

Restart HA, then check logs for detailed debug info.

### 10.3 Manual Kafka Test from HA

**From HA container/host**:

```bash
# Test Kafka connectivity
python3 -c "
from kafka import KafkaConsumer
consumer = KafkaConsumer(
    'tesla_telemetry',
    bootstrap_servers=['192.168.5.105:9092'],
    auto_offset_reset='latest'
)
print('✅ Kafka connection successful')
for msg in consumer:
    print(f'Message received: offset={msg.offset}')
    break
"
```

Expected output:
```
✅ Kafka connection successful
Message received: offset=1234
```

---

## Step 11: Validation Checklist

Before considering the setup complete, verify:

- ✅ Integration loaded without errors (check logs)
- ✅ All entities created in HA
- ✅ Entities update in real-time (<5 seconds)
- ✅ Device tracker location updates correctly
- ✅ Sensors show correct values (speed, battery, etc.)
- ✅ Binary sensors toggle correctly (driving on/off)
- ✅ Automations trigger reliably
- ✅ Dashboard cards display data
- ✅ No errors in HA logs

---

## Troubleshooting

### Entities not created

**Problem**: Integration loads but no entities appear

**Check**:
1. Integration configuration in `configuration.yaml` correct
2. Vehicle VIN matches what's in config
3. Check logs: `grep -i tesla_telemetry_local /config/home-assistant.log`

**Solution**:
- Verify VIN: Check `/config/configuration.yaml`
- Check entity registry: Developer Tools → Entities
- Restart HA: `ha core restart`

### Entities not updating

**Problem**: Entities exist but values don't change

**Check**:
1. Kafka messages arriving: `docker exec -it kafka kafka-console-consumer ...`
2. Kafka broker reachable from HA: `ping 192.168.5.105`
3. Check logs for Kafka connection errors

**Solution**:
- Test Kafka connectivity (see 10.3)
- Verify broker IP in config
- Check firewall not blocking port 9092

### High latency (updates slow)

**Problem**: Entity updates take 10+ seconds

**Possible causes**:
1. Kafka consumer lag
2. Protobuf parsing slow
3. HA overloaded (too many integrations)

**Solutions**:
- Check Kafka UI for consumer lag
- Enable debug logging to measure parsing time
- Increase HA resources (CPU/RAM)

### Protobuf decode errors

**Problem**: Logs show "Protobuf decode error"

**Cause**: Mismatched Protobuf schema or corrupted message

**Solution**:
1. Verify `vehicle_data_pb2.py` is correctly compiled
2. Check Tesla hasn't updated Protobuf schema
3. Recompile Protobuf: `protoc --python_out=. vehicle_data.proto`

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
   - Battery degradation monitoring

3. **Integrate with other systems**:
   - Solar production (charge when excess solar)
   - Calendar (pre-condition before events)
   - Weather (adjust HVAC based on forecast)

### Reference Documentation:

- [Automation Examples](../examples/automation_garage.yaml)
- [Dashboard Examples](../examples/dashboard.yaml)
- [Troubleshooting Guide](06_troubleshooting.md)

---

**Congratulations!** 🎉 You now have a fully functional self-hosted Tesla Fleet Telemetry system with Home Assistant integration!
