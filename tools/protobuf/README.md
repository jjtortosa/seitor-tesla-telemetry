# Tesla Fleet Telemetry Protobuf Compilation

This directory contains tools for compiling Tesla's official Protobuf schema for use in the Home Assistant custom integration.

## Overview

Tesla Fleet Telemetry uses Protocol Buffers (Protobuf) to encode vehicle data messages sent via Kafka. This ensures efficient binary encoding and strong typing of telemetry data.

## Files

- **`vehicle_data.proto`**: Tesla's official Protobuf schema (downloaded from [tesla/fleet-telemetry](https://github.com/teslamotors/fleet-telemetry))
- **`vehicle_data_pb2.py`**: Compiled Python bindings (generated file, do not edit)
- **`compile_proto.sh`**: Compilation script to generate Python bindings
- **`README.md`**: This file

## Requirements

### System Requirements

- **macOS**: `brew install protobuf`
- **Ubuntu/Debian**: `sudo apt-get install protobuf-compiler`
- **Other**: Install `protoc` from [protobuf releases](https://github.com/protocolbuffers/protobuf/releases)

### Python Requirements

No Python packages are required for compilation (only `protoc` binary is needed).

For **runtime** (Home Assistant integration):
- `protobuf==4.25.1` (already specified in `manifest.json`)

## Compilation

### Quick Start

Run the compilation script:

```bash
cd tools/protobuf
./compile_proto.sh
```

This will:
1. Verify `vehicle_data.proto` exists
2. Check for `protoc` compiler
3. Compile the `.proto` file to Python bindings
4. Copy the generated `vehicle_data_pb2.py` to the HA integration directory

### Manual Compilation

If you prefer to compile manually:

```bash
cd tools/protobuf

# Compile proto file
protoc --python_out=. vehicle_data.proto

# Copy to integration
cp vehicle_data_pb2.py ../../ha-integration/custom_components/tesla_telemetry_local/
```

## Updating the Schema

Tesla may update the Protobuf schema in future firmware versions. To update:

1. **Download the latest schema**:
   ```bash
   curl -L -o vehicle_data.proto \
     https://raw.githubusercontent.com/teslamotors/fleet-telemetry/main/protos/vehicle_data.proto
   ```

2. **Recompile**:
   ```bash
   ./compile_proto.sh
   ```

3. **Test the integration**:
   - Restart Home Assistant
   - Check logs for Protobuf parsing errors
   - Verify entity updates are working

4. **Update version** (if needed):
   - Update `version` in `ha-integration/custom_components/tesla_telemetry_local/manifest.json`
   - Document breaking changes

## Protobuf Message Structure

### Payload Structure

```
Payload
├── data: [Datum]           # Array of field/value pairs
│   ├── key: Field          # Enum (e.g., Location, VehicleSpeed, Soc)
│   └── value: Value        # Union type (string, int, float, location, etc.)
├── created_at: Timestamp   # Message creation time
├── vin: string             # Vehicle VIN
└── is_resend: bool         # Indicates if message is a resend
```

### Field Types

The `Field` enum contains 258+ field definitions including:
- **Location data**: `Location`, `GpsHeading`, `GpsState`
- **Battery**: `Soc`, `EstBatteryRange`, `PackVoltage`, `PackCurrent`
- **Charging**: `ChargeState`, `ChargingCableType`, `ChargerVoltage`
- **Drive state**: `Gear`, `VehicleSpeed`, `Odometer`
- **Climate**: `InsideTemp`, `OutsideTemp`, `HvacPower`
- **Doors/Windows**: `DoorState`, `Locked`, `FdWindow`, etc.
- **Many more**: See `vehicle_data.proto` for full list

### Value Types

The `Value` message uses a `oneof` union with these types:
- **Primitives**: `string`, `int`, `long`, `float`, `double`, `boolean`
- **Enums**: `ChargingState`, `ShiftState`, `SentryModeState`, etc.
- **Complex**: `LocationValue`, `Doors`, `TireLocation`, `Time`

## Integration Usage

The compiled Protobuf is used in `kafka_consumer.py`:

```python
from . import vehicle_data_pb2

# Parse binary message from Kafka
payload = vehicle_data_pb2.Payload()
payload.ParseFromString(raw_bytes)

# Extract fields
for datum in payload.data:
    field_name = vehicle_data_pb2.Field.Name(datum.key)
    value = extract_value(datum.value)
    # Process field...
```

## Troubleshooting

### Compilation Errors

**Error**: `protoc: command not found`
- **Solution**: Install Protocol Buffers compiler (see Requirements)

**Error**: `google/protobuf/timestamp.proto: File not found`
- **Solution**: Ensure `protoc` is properly installed with standard includes

### Runtime Errors

**Error**: `ModuleNotFoundError: No module named 'google.protobuf'`
- **Solution**: Install `protobuf` package in Home Assistant:
  ```bash
  docker exec -it homeassistant pip3 install protobuf==4.25.1
  ```

**Error**: `Failed to parse Protobuf message`
- **Cause**: Message format changed or corrupted data
- **Solution**:
  1. Check Home Assistant logs for details
  2. Verify Kafka messages are valid
  3. Update schema if Tesla changed format
  4. Enable debug logging: `custom_components.tesla_telemetry_local: debug`

### Version Compatibility

| Protobuf Version | Python Version | Notes |
|-----------------|----------------|-------|
| 4.25.1 | 3.9+ | Current version, tested |
| 5.x | 3.10+ | Not tested, may work |
| 3.x | Any | Deprecated, not recommended |

## Development

### Testing Protobuf Parsing

You can test Protobuf parsing in Python:

```python
from custom_components.tesla_telemetry_local import vehicle_data_pb2

# Create test payload
payload = vehicle_data_pb2.Payload()
payload.vin = "5YJ3E1EA1MF000000"

# Add a field (e.g., vehicle speed)
datum = payload.data.add()
datum.key = vehicle_data_pb2.Field.VehicleSpeed
datum.value.int_value = 65

# Serialize
binary_data = payload.SerializeToString()
print(f"Binary size: {len(binary_data)} bytes")

# Deserialize
parsed_payload = vehicle_data_pb2.Payload()
parsed_payload.ParseFromString(binary_data)
print(f"VIN: {parsed_payload.vin}")
print(f"Speed: {parsed_payload.data[0].value.int_value}")
```

### Field Mapping Reference

Common fields and their value types:

| Field | Value Type | Example |
|-------|-----------|---------|
| `Location` | `location_value` | `{latitude: 41.3874, longitude: 2.1686}` |
| `VehicleSpeed` | `int_value` | `65` (km/h) |
| `Soc` | `int_value` | `80` (percent) |
| `Gear` | `shift_state_value` | `ShiftStateD`, `ShiftStateP` |
| `ChargeState` | `charging_value` | `ChargeStateCharging` |
| `InsideTemp` | `float_value` | `22.5` (°C) |
| `Odometer` | `float_value` | `12345.6` (km) |

## References

- [Tesla Fleet Telemetry GitHub](https://github.com/teslamotors/fleet-telemetry)
- [Protocol Buffers Documentation](https://protobuf.dev/)
- [Protocol Buffers Python Tutorial](https://protobuf.dev/getting-started/pythontutorial/)

## License

The `vehicle_data.proto` schema is provided by Tesla under their repository license.

This compilation tooling is part of the seitor-tesla-telemetry project (MIT License).
