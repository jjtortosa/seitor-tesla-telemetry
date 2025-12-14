# Tesla Fleet Telemetry Local - Home Assistant Integration

Custom Home Assistant integration for consuming Tesla Fleet Telemetry data via MQTT.

## Features

- **Real-time updates**: <1-5 second latency for location, speed, shift state
- **Device Tracker**: GPS location entity with zone detection
- **Sensors**: Speed, battery, range, shift state, charging status, charger voltage/current
- **Binary Sensors**: Driving state, charging state, charge port, connectivity
- **No polling**: Push-based updates via MQTT (no Tesla API rate limits)
- **Local control**: All data stays in your network (privacy)
- **Config Flow**: Easy setup via Home Assistant UI

## Requirements

- Home Assistant 2024.1.0 or newer
- Self-hosted Tesla Fleet Telemetry server publishing to MQTT
- MQTT integration configured in Home Assistant (Mosquitto add-on recommended)

## Installation

### Manual Installation

1. **Copy integration files**:

```bash
cd /config  # Your Home Assistant config directory

# Clone repository
git clone https://github.com/jjtortosa/seitor-tesla-telemetry.git

# Copy integration
cp -r seitor-tesla-telemetry/ha-integration/custom_components/tesla_telemetry_local \
      custom_components/
```

2. **Restart Home Assistant**

3. **Add integration via UI**:
   - Go to **Settings → Devices & Services**
   - Click **Add Integration**
   - Search for "Tesla Fleet Telemetry Local"
   - Follow the setup wizard

## Configuration

### Via UI (Recommended)

1. **Step 1 - MQTT Configuration**:
   - Enter MQTT topic base (default: `tesla`)
   - This must match the Fleet Telemetry server config

2. **Step 2 - Vehicle Configuration**:
   - Enter your 17-character VIN
   - Enter a friendly name for your vehicle

### Configuration Options

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `mqtt_topic_base` | No | `tesla` | MQTT topic base (e.g., `tesla` for `tesla/VIN/v/#`) |
| `vehicle_vin` | Yes | - | Tesla VIN (17 characters) |
| `vehicle_name` | No | `Tesla` | Friendly name for entities |

## Entities Created

After installation, the following entities will be created:

### Device Tracker

- `device_tracker.VEHICLENAME_location` - GPS location with zone detection

### Sensors

- `sensor.VEHICLENAME_speed` - Current speed (km/h)
- `sensor.VEHICLENAME_shift_state` - Current gear (P/D/R/N)
- `sensor.VEHICLENAME_battery` - Battery level (%)
- `sensor.VEHICLENAME_range` - Estimated range (km)
- `sensor.VEHICLENAME_charging_state` - Charging status
- `sensor.VEHICLENAME_charger_voltage` - Charger voltage (V)
- `sensor.VEHICLENAME_charger_current` - Charger current (A)
- `sensor.VEHICLENAME_odometer` - Vehicle odometer (km)

### Binary Sensors

- `binary_sensor.VEHICLENAME_driving` - Driving state (on/off)
- `binary_sensor.VEHICLENAME_charging` - Charging state (on/off)
- `binary_sensor.VEHICLENAME_charge_port_open` - Charge port open (on/off)
- `binary_sensor.VEHICLENAME_connected` - Vehicle connectivity (on/off)

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

## Troubleshooting

### Integration Won't Load

**Check logs**:
```bash
tail -f /config/home-assistant.log | grep tesla_telemetry_local
```

**Common issues**:
1. MQTT not configured: Install Mosquitto add-on and configure MQTT integration
2. Topic base mismatch: Verify topic base matches Fleet Telemetry config
3. Wrong VIN format: VIN must be exactly 17 characters

### Entities Not Updating

**Check MQTT messages**:
```bash
mosquitto_sub -h localhost -t "tesla/#" -v
```

**Enable debug logging** in `configuration.yaml`:
```yaml
logger:
  default: info
  logs:
    custom_components.tesla_telemetry_local: debug
```

### High Latency

- Verify Fleet Telemetry server is publishing to MQTT
- Check network latency to MQTT broker
- Check HA system load

## Support

- **Documentation**: https://github.com/jjtortosa/seitor-tesla-telemetry/tree/main/docs
- **Issues**: https://github.com/jjtortosa/seitor-tesla-telemetry/issues

## License

MIT License - see [LICENSE](../../LICENSE) file

## Credits

- Tesla for Fleet Telemetry API
- Home Assistant community
- Based on [tesla/fleet-telemetry](https://github.com/teslamotors/fleet-telemetry)
