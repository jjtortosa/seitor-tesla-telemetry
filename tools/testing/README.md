# Tesla Fleet Telemetry - Testing Tools

Tools for testing and debugging the Tesla Fleet Telemetry integration.

## Overview

This directory contains utilities to help you:
1. **Generate mock data** - Test the integration without a real Tesla vehicle
2. **Validate the integration** - Ensure everything works before going live

## Tools

### Mock Message Generator (`generate_mock_message.py`)

Generate realistic Tesla telemetry messages for testing the Home Assistant integration.

#### Usage

**Generate driving scenario (default)**:
```bash
python3 generate_mock_message.py --scenario driving --json
```

**Generate charging scenario**:
```bash
python3 generate_mock_message.py --scenario charging --output charging.bin
```

**Generate parked scenario**:
```bash
python3 generate_mock_message.py --scenario parked --vin 5YJ3E1EA1MF000000
```

#### Scenarios

| Scenario | Description | Key Fields |
|----------|-------------|------------|
| `driving` | Vehicle in motion | Speed: 65 km/h, Gear: D, Location updating |
| `charging` | Charging at home | Speed: 0, Gear: P, ChargeState: Charging, 3.7kW |
| `parked` | Parked with Sentry Mode | Speed: 0, Gear: P, SentryMode: On |

#### Output Formats

- **`--json`**: Human-readable JSON format (for inspection)
- **`--output file.bin`**: Binary Protobuf format (for testing)
- **No flags**: Hexadecimal output to stdout

---

## Testing Workflows

### Workflow 1: Monitor MQTT Messages

Monitor real-time telemetry messages from your Tesla via MQTT.

**Using mosquitto_sub**:
```bash
# Subscribe to all Tesla telemetry
mosquitto_sub -h localhost -u mqtt_user -P your_password -t "tesla/#" -v

# Subscribe to specific VIN
mosquitto_sub -h localhost -u mqtt_user -P your_password -t "tesla/LRWYGCFS3RC210528/v/#" -v
```

**Using Home Assistant MQTT integration**:
- Go to Settings > Devices & Services > MQTT
- Click "Listen to a topic"
- Enter: `tesla/#`

---

### Workflow 2: Test with Mock Data

Test the integration without a real Tesla vehicle.

**Step 1: Generate mock message**
```bash
cd tools/testing
python3 generate_mock_message.py --scenario driving --json
```

**Step 2: Publish to MQTT**
```bash
# Publish battery level
mosquitto_pub -h localhost -u mqtt_user -P password -t "tesla/VIN/v/Soc" -m '{"value": 85}'

# Publish location
mosquitto_pub -h localhost -u mqtt_user -P password -t "tesla/VIN/v/Location" -m '{"latitude": 41.38, "longitude": 2.17}'

# Publish vehicle speed
mosquitto_pub -h localhost -u mqtt_user -P password -t "tesla/VIN/v/VehicleSpeed" -m '{"value": 65}'
```

**Step 3: Verify in Home Assistant**
```bash
# Check HA logs
tail -f /config/home-assistant.log | grep tesla_telemetry_local

# Check entity states via API
curl -s http://localhost:8123/api/states/sensor.melany_battery -H "Authorization: Bearer TOKEN"
```

---

### Workflow 3: Integration Testing

Complete end-to-end test of the integration.

**Prerequisites**:
- Fleet Telemetry server running
- MQTT broker accessible
- Home Assistant with integration installed
- Tesla vehicle configured

**Test Steps**:

1. **Verify MQTT connectivity**
   ```bash
   # Test connection
   mosquitto_pub -h localhost -u mqtt_user -P password -t "test" -m "hello"
   ```

2. **Monitor MQTT**
   ```bash
   # In terminal 1: Subscribe to all Tesla topics
   mosquitto_sub -h localhost -u mqtt_user -P password -t "tesla/#" -v
   ```

3. **Monitor Home Assistant**
   ```bash
   # In terminal 2: Watch HA logs
   tail -f /config/home-assistant.log | grep tesla_telemetry_local
   ```

4. **Trigger vehicle activity**
   - Open Tesla app
   - Turn on climate control
   - Check vehicle status

5. **Verify entity updates**
   - Check Home Assistant dashboard
   - Verify entities show current values
   - Test automations if configured

---

## Troubleshooting

### Mock Generator Issues

**Error**: `ModuleNotFoundError: No module named 'google'`
```bash
pip3 install protobuf>=5.27.0
```

**Error**: `Cannot find vehicle_data_pb2`
```bash
# Compile Protobuf first
cd ../../tools/protobuf
./compile_proto.sh
```

### MQTT Issues

**Error**: `Connection refused`
- Check MQTT broker is running
- Verify credentials are correct
- Check firewall allows port 1883/8883

**Problem**: No messages received
- Verify Fleet Telemetry is publishing to MQTT
- Check topic names match configuration
- Verify vehicle is online and sending data

### Integration Issues

**Problem**: Entities not updating
1. Check MQTT messages are arriving (mosquitto_sub)
2. Verify HA logs show message processing
3. Confirm entity IDs match configuration
4. Restart Home Assistant

**Problem**: Entities show "unavailable"
1. Check integration is loaded (Settings > Integrations)
2. Verify MQTT is configured in Home Assistant
3. Check topic base matches Fleet Telemetry config

---

## Resources

- [Tesla Fleet API Documentation](https://developer.tesla.com/)
- [MQTT Protocol](https://mqtt.org/)
- [Home Assistant MQTT Docs](https://www.home-assistant.io/integrations/mqtt/)
- [Home Assistant Developer Docs](https://developers.home-assistant.io/)

---

**Happy Testing!**
