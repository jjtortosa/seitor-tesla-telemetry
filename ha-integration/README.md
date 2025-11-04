# Tesla Fleet Telemetry Local - Home Assistant Integration

Custom Home Assistant integration for consuming Tesla Fleet Telemetry data from a self-hosted Kafka server.

## Features

- **Real-time updates**: <1-5 second latency for location, speed, shift state
- **Device Tracker**: GPS location entity with zone detection
- **Sensors**: Speed, battery, range, shift state, charging status, charger voltage/current
- **Binary Sensors**: Driving state, charging state, charge port, connectivity
- **No polling**: Push-based updates from Kafka (no Tesla API rate limits)
- **Local control**: All data stays in your network (privacy)

## Requirements

- Home Assistant 2024.1.0 or newer
- Self-hosted Tesla Fleet Telemetry server with Kafka
- Python packages: `kafka-python==2.0.2`, `protobuf==4.25.1`

## Installation

### Option 1: Manual Installation

1. **Copy integration files**:

```bash
cd /config  # Your Home Assistant config directory

# Clone repository
git clone https://github.com/jjtortosa/seitor-tesla-telemetry.git

# Copy integration
cp -r seitor-tesla-telemetry/ha-integration/custom_components/tesla_telemetry_local \
      custom_components/
```

2. **Install Python dependencies**:

```bash
# Enter HA container
docker exec -it homeassistant bash

# Install dependencies
pip3 install kafka-python==2.0.2 protobuf==4.25.1

# Exit container
exit
```

3. **Configure in `configuration.yaml`**:

```yaml
tesla_telemetry_local:
  kafka_broker: "192.168.5.105:9092"  # Your Kafka broker IP:port
  kafka_topic: "tesla_telemetry"
  vehicle_vin: "5YJ3E1EA1MF000000"    # Your Tesla VIN
  vehicle_name: "MelanY"               # Friendly name
```

4. **Restart Home Assistant**:

```bash
ha core restart
```

### Option 2: HACS (Future)

HACS installation will be available once the integration is published.

## Entities Created

After installation and restart, the following entities will be created:

### Device Tracker

- `device_tracker.melany_location` - GPS location with zone detection

### Sensors

- `sensor.melany_speed` - Current speed (km/h)
- `sensor.melany_shift_state` - Current gear (P/D/R/N)
- `sensor.melany_battery` - Battery level (%)
- `sensor.melany_range` - Estimated range (km)
- `sensor.melany_charging_state` - Charging status
- `sensor.melany_charger_voltage` - Charger voltage (V)
- `sensor.melany_charger_current` - Charger current (A)
- `sensor.melany_odometer` - Vehicle odometer (km)

### Binary Sensors

- `binary_sensor.melany_driving` - Driving state (on/off)
- `binary_sensor.melany_charging` - Charging state (on/off)
- `binary_sensor.melany_charge_port_open` - Charge port open (on/off)
- `binary_sensor.melany_connected` - Vehicle connectivity (on/off)

## Configuration Options

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `kafka_broker` | Yes | - | Kafka broker address (IP:port) |
| `kafka_topic` | No | `tesla_telemetry` | Kafka topic name |
| `vehicle_vin` | Yes | - | Tesla VIN (17 characters) |
| `vehicle_name` | No | `Tesla` | Friendly name for entities |

## Example Automations

### Garage Door Opener

```yaml
automation:
  - alias: "Tesla: Open garage when arriving"
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
          message: "Opening for {{ state_attr('device_tracker.melany_location', 'friendly_name') }}"
```

### Driving Notification

```yaml
automation:
  - alias: "Tesla: Notify when driving"
    trigger:
      - platform: state
        entity_id: binary_sensor.melany_driving
        from: "off"
        to: "on"
    action:
      - service: notify.mobile_app
        data:
          title: "Tesla"
          message: "MelanY started driving at {{ now().strftime('%H:%M') }}"
```

### Low Battery Alert

```yaml
automation:
  - alias: "Tesla: Low battery warning"
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
          message: "MelanY battery is {{ states('sensor.melany_battery') }}%. Please charge."
```

## Dashboard Example

### Entities Card

```yaml
type: entities
title: MelanY
entities:
  - entity: device_tracker.melany_location
  - entity: sensor.melany_shift_state
  - entity: sensor.melany_speed
  - entity: sensor.melany_battery
  - entity: sensor.melany_range
  - entity: binary_sensor.melany_driving
  - entity: binary_sensor.melany_charging
```

### Map Card

```yaml
type: map
entities:
  - device_tracker.melany_location
hours_to_show: 24
default_zoom: 15
```

### Gauge Card

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

## Troubleshooting

### Integration Won't Load

**Check logs**:
```bash
tail -f /config/home-assistant.log | grep tesla_telemetry_local
```

**Common issues**:
1. Missing dependencies: `pip3 install kafka-python protobuf`
2. Wrong config format: Check `configuration.yaml` syntax
3. Kafka unreachable: Verify broker IP and port

### Entities Not Updating

**Check Kafka connectivity**:
```bash
docker exec -it homeassistant nc -zv 192.168.5.105 9092
```

**Enable debug logging** in `configuration.yaml`:
```yaml
logger:
  default: info
  logs:
    custom_components.tesla_telemetry_local: debug
```

### High Latency

- Check Kafka UI for consumer lag
- Verify network latency: `ping 192.168.5.105`
- Check HA system load: `ha core check`

## Development

### Protobuf Schema

The integration uses Tesla's `vehicle_data.proto` schema. To generate Python bindings:

```bash
# Download schema
wget https://github.com/teslamotors/fleet-telemetry/raw/main/protos/vehicle_data.proto

# Install compiler
pip install protobuf

# Compile
protoc --python_out=. vehicle_data.proto

# Copy to integration
cp vehicle_data_pb2.py custom_components/tesla_telemetry_local/
```

### Testing

Currently uses simplified JSON parser for testing. Replace with Protobuf in production.

## Support

- **Documentation**: https://github.com/jjtortosa/seitor-tesla-telemetry/tree/main/docs
- **Issues**: https://github.com/jjtortosa/seitor-tesla-telemetry/issues
- **Home Assistant Community**: https://community.home-assistant.io/

## License

MIT License - see [LICENSE](../../LICENSE) file

## Credits

- Tesla for Fleet Telemetry API
- Home Assistant community
- Based on [tesla/fleet-telemetry](https://github.com/teslamotors/fleet-telemetry)
