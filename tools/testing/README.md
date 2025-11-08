# Tesla Fleet Telemetry - Testing Tools

Tools for testing and debugging the Tesla Fleet Telemetry integration before and during real-world deployment.

## Overview

This directory contains utilities to help you:
1. **Generate mock data** - Test the integration without a real Tesla vehicle
2. **Debug Kafka messages** - Inspect real telemetry messages from your vehicle
3. **Validate the integration** - Ensure everything works before going live

## Tools

### 1. Mock Message Generator (`generate_mock_message.py`)

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
- **`--output file.bin`**: Binary Protobuf format (for sending to Kafka)
- **No flags**: Hexadecimal output to stdout

#### Examples

```bash
# View message details
python3 generate_mock_message.py --scenario charging --json

# Save binary message
python3 generate_mock_message.py --scenario driving --output test_driving.bin

# Custom VIN
python3 generate_mock_message.py --vin 5YJSA1E14HF123456 --scenario parked
```

---

### 2. Kafka Debugger (`kafka_debugger.py`)

Connect to your Kafka broker and inspect Tesla telemetry messages in real-time.

#### Prerequisites

```bash
# Install dependencies
pip3 install kafka-python protobuf>=5.27.0
```

#### Usage

**Monitor latest messages**:
```bash
python3 kafka_debugger.py --broker 192.168.5.105:9092
```

**Read from beginning**:
```bash
python3 kafka_debugger.py --broker 192.168.5.105:9092 --from-beginning
```

**Filter by VIN**:
```bash
python3 kafka_debugger.py --broker 192.168.5.105:9092 --vin 5YJ3E1EA1MF000000
```

**Read only 10 messages**:
```bash
python3 kafka_debugger.py --broker 192.168.5.105:9092 --max 10
```

**Show raw data**:
```bash
python3 kafka_debugger.py --broker 192.168.5.105:9092 --raw
```

#### Output Example

```
Message #1
  VIN: 5YJ3E1EA1MF000000
  Timestamp: 2025-11-08 18:30:15
  Resend: False
  Fields: 15

  Key Fields:
    Location: {'lat': 41.3874, 'lon': 2.1686}
    VehicleSpeed: 65
    Gear: ShiftStateD
    Soc: 80
    EstBatteryRange: 320.5
    ChargeState: ChargeStateDisconnected
    Odometer: 12345.6
    InsideTemp: 22.5
    Locked: True

  Other Fields (6):
    GpsHeading: 45
    OutsideTemp: 18.0
    ...
```

---

## Testing Workflows

### Workflow 1: Test with Mock Data (No Vehicle Required)

Test the integration without a real Tesla vehicle.

**Step 1: Generate mock message**
```bash
cd tools/testing
python3 generate_mock_message.py --scenario driving --output /tmp/test_message.bin
```

**Step 2: Send to Kafka** (requires Kafka CLI tools)
```bash
# Using kafkacat (kcat)
kcat -P -b 192.168.5.105:9092 -t tesla_telemetry < /tmp/test_message.bin

# Or using kafka-console-producer
cat /tmp/test_message.bin | kafka-console-producer --broker-list 192.168.5.105:9092 --topic tesla_telemetry
```

**Step 3: Verify in Home Assistant**
```bash
# Check HA logs
tail -f /config/home-assistant.log | grep tesla_telemetry_local

# Check entity states
ha state list | grep melany
```

---

### Workflow 2: Debug Real Vehicle Messages

Inspect real telemetry messages from your Tesla.

**Step 1: Start debugger**
```bash
cd tools/testing
python3 kafka_debugger.py --broker 192.168.5.105:9092 --from-beginning
```

**Step 2: Trigger vehicle activity**
- Get in your Tesla
- Turn on climate control
- Start driving
- Start charging

**Step 3: Observe messages**
- Watch the debugger output
- Verify all expected fields are present
- Check for any parsing errors

**Step 4: Save sample messages**
```bash
# Read 10 messages and inspect
python3 kafka_debugger.py --broker 192.168.5.105:9092 --max 10 > sample_messages.txt
```

---

### Workflow 3: Integration Testing

Complete end-to-end test of the integration.

**Prerequisites**:
- Fleet Telemetry server running
- Kafka broker accessible
- Home Assistant with integration installed
- (Optional) Tesla vehicle configured

**Test Steps**:

1. **Verify Kafka connectivity**
   ```bash
   # Test connection
   nc -zv 192.168.5.105 9092

   # List topics
   kafka-topics --bootstrap-server 192.168.5.105:9092 --list
   ```

2. **Monitor Kafka**
   ```bash
   # In terminal 1: Start debugger
   python3 kafka_debugger.py --broker 192.168.5.105:9092
   ```

3. **Monitor Home Assistant**
   ```bash
   # In terminal 2: Watch HA logs
   tail -f /config/home-assistant.log | grep tesla_telemetry_local
   ```

4. **Send test message** (mock or real vehicle)
   - Option A: Send mock message (see Workflow 1)
   - Option B: Trigger real vehicle activity

5. **Verify entity updates**
   ```bash
   # Check entity states
   ha state get device_tracker.melany_location
   ha state get sensor.melany_speed
   ha state get sensor.melany_battery
   ha state get binary_sensor.melany_driving
   ```

6. **Check for errors**
   - Review HA logs for exceptions
   - Verify Protobuf parsing succeeded
   - Confirm entity updates are working

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

### Kafka Debugger Issues

**Error**: `Connection failed: NoBrokersAvailable`
- Check Kafka broker is running: `docker ps | grep kafka`
- Verify network connectivity: `nc -zv 192.168.5.105 9092`
- Check firewall rules

**Error**: `No messages received`
- Try `--from-beginning` to read historical messages
- Verify topic name is correct (default: `tesla_telemetry`)
- Check if vehicle is sending data

**Error**: `Protobuf parse error`
- Ensure Protobuf schema is up to date
- Check message format matches Tesla's specification
- Enable debug logging for details

### Integration Issues

**Problem**: Entities not updating
1. Check Kafka debugger shows messages
2. Verify HA logs show message processing
3. Confirm entity IDs match configuration
4. Restart Home Assistant

**Problem**: Parse errors in HA logs
1. Check Protobuf version: `pip3 show protobuf`
2. Should be `>=5.27.0`
3. Recompile Protobuf if needed
4. Check for Tesla schema updates

---

## Development

### Adding New Test Scenarios

Edit `generate_mock_message.py` to add new scenarios:

```python
def create_supercharging_message(vin: str) -> vehicle_data_pb2.Payload:
    """Create a supercharging scenario."""
    payload = vehicle_data_pb2.Payload()
    payload.vin = vin

    # Add fields...
    add_field(payload, vehicle_data_pb2.Field.FastChargerPresent, boolean_value=True)
    add_field(payload, vehicle_data_pb2.Field.DCChargingPower, int_value=150000)  # 150 kW

    return payload
```

### Customizing Debug Output

Edit `kafka_debugger.py` to modify the display format:

```python
# In format_message method, add more fields to important_fields list
important_fields = [
    'Location', 'VehicleSpeed', 'Gear', 'Soc',
    'YourCustomField',  # Add here
]
```

---

## Resources

- [Tesla Fleet API Documentation](https://developer.tesla.com/)
- [Kafka Python Client Docs](https://kafka-python.readthedocs.io/)
- [Protocol Buffers Python Tutorial](https://protobuf.dev/getting-started/pythontutorial/)
- [Home Assistant Developer Docs](https://developers.home-assistant.io/)

---

## Next Steps

After successful testing:

1. **Document your findings**
   - Record any issues encountered
   - Note which fields are actually sent by your vehicle
   - Update sensor definitions if needed

2. **Create automations**
   - Use tested entity data
   - Set up garage door opener
   - Configure charging notifications

3. **Monitor performance**
   - Check message latency
   - Verify entity update frequency
   - Monitor resource usage

4. **Share feedback**
   - Report issues on GitHub
   - Contribute improvements
   - Help other users

---

**Happy Testing!** 🚗⚡
