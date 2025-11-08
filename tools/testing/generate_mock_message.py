#!/usr/bin/env python3
"""
Generate mock Tesla Fleet Telemetry Protobuf messages for testing.

This script creates realistic test messages that can be used to verify
the Home Assistant integration without a real Tesla vehicle.

Usage:
    python3 generate_mock_message.py [--output message.bin]
"""

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

# Add parent directory to path to import vehicle_data_pb2
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "ha-integration" / "custom_components" / "tesla_telemetry_local"))

try:
    import vehicle_data_pb2
    from google.protobuf import timestamp_pb2
except ImportError as e:
    print(f"Error: {e}")
    print("\nPlease install protobuf:")
    print("  pip3 install protobuf>=5.27.0")
    sys.exit(1)


def create_driving_message(vin: str = "5YJ3E1EA1MF000000") -> vehicle_data_pb2.Payload:
    """Create a mock message simulating a driving Tesla."""
    payload = vehicle_data_pb2.Payload()
    payload.vin = vin

    # Set timestamp
    ts = timestamp_pb2.Timestamp()
    ts.GetCurrentTime()
    payload.created_at.CopyFrom(ts)

    # Location (Barcelona, Spain)
    add_field(payload, vehicle_data_pb2.Field.Location,
              location=(41.3874, 2.1686))

    # GPS heading (45 degrees, northeast)
    add_field(payload, vehicle_data_pb2.Field.GpsHeading, int_value=45)

    # Vehicle speed (65 km/h)
    add_field(payload, vehicle_data_pb2.Field.VehicleSpeed, int_value=65)

    # Gear (D - Drive)
    add_field(payload, vehicle_data_pb2.Field.Gear,
              shift_state=vehicle_data_pb2.ShiftState.ShiftStateD)

    # Battery state of charge (80%)
    add_field(payload, vehicle_data_pb2.Field.Soc, int_value=80)

    # Estimated battery range (320 km)
    add_field(payload, vehicle_data_pb2.Field.EstBatteryRange, float_value=320.5)

    # Odometer (12,345 km)
    add_field(payload, vehicle_data_pb2.Field.Odometer, float_value=12345.6)

    # Inside temperature (22.5°C)
    add_field(payload, vehicle_data_pb2.Field.InsideTemp, float_value=22.5)

    # Outside temperature (18.0°C)
    add_field(payload, vehicle_data_pb2.Field.OutsideTemp, float_value=18.0)

    # Not charging
    add_field(payload, vehicle_data_pb2.Field.ChargeState,
              charging=vehicle_data_pb2.ChargingState.ChargeStateDisconnected)

    # Doors locked
    add_field(payload, vehicle_data_pb2.Field.Locked, boolean_value=True)

    # All doors closed
    add_field(payload, vehicle_data_pb2.Field.DoorState,
              doors=(False, False, False, False, False, False))

    return payload


def create_charging_message(vin: str = "5YJ3E1EA1MF000000") -> vehicle_data_pb2.Payload:
    """Create a mock message simulating a charging Tesla at home."""
    payload = vehicle_data_pb2.Payload()
    payload.vin = vin

    # Set timestamp
    ts = timestamp_pb2.Timestamp()
    ts.GetCurrentTime()
    payload.created_at.CopyFrom(ts)

    # Location (home)
    add_field(payload, vehicle_data_pb2.Field.Location,
              location=(41.3850, 2.1700))

    # Vehicle stationary
    add_field(payload, vehicle_data_pb2.Field.VehicleSpeed, int_value=0)

    # Gear (P - Park)
    add_field(payload, vehicle_data_pb2.Field.Gear,
              shift_state=vehicle_data_pb2.ShiftState.ShiftStateP)

    # Battery state of charge (45%)
    add_field(payload, vehicle_data_pb2.Field.Soc, int_value=45)

    # Estimated battery range (180 km)
    add_field(payload, vehicle_data_pb2.Field.EstBatteryRange, float_value=180.0)

    # Charging
    add_field(payload, vehicle_data_pb2.Field.ChargeState,
              charging=vehicle_data_pb2.ChargingState.ChargeStateCharging)

    # Charger voltage (230V)
    add_field(payload, vehicle_data_pb2.Field.ChargerVoltage, int_value=230)

    # Charge amps (16A)
    add_field(payload, vehicle_data_pb2.Field.ChargeAmps, int_value=16)

    # AC charging power (3.7 kW)
    add_field(payload, vehicle_data_pb2.Field.ACChargingPower, int_value=3700)

    # Time to full charge (4.5 hours)
    add_field(payload, vehicle_data_pb2.Field.TimeToFullCharge, float_value=4.5)

    # Charge limit SOC (80%)
    add_field(payload, vehicle_data_pb2.Field.ChargeLimitSoc, int_value=80)

    # Doors locked
    add_field(payload, vehicle_data_pb2.Field.Locked, boolean_value=True)

    return payload


def create_parked_message(vin: str = "5YJ3E1EA1MF000000") -> vehicle_data_pb2.Payload:
    """Create a mock message simulating a parked Tesla (not charging)."""
    payload = vehicle_data_pb2.Payload()
    payload.vin = vin

    # Set timestamp
    ts = timestamp_pb2.Timestamp()
    ts.GetCurrentTime()
    payload.created_at.CopyFrom(ts)

    # Location
    add_field(payload, vehicle_data_pb2.Field.Location,
              location=(41.3900, 2.1750))

    # Vehicle stationary
    add_field(payload, vehicle_data_pb2.Field.VehicleSpeed, int_value=0)

    # Gear (P - Park)
    add_field(payload, vehicle_data_pb2.Field.Gear,
              shift_state=vehicle_data_pb2.ShiftState.ShiftStateP)

    # Battery state of charge (75%)
    add_field(payload, vehicle_data_pb2.Field.Soc, int_value=75)

    # Not charging
    add_field(payload, vehicle_data_pb2.Field.ChargeState,
              charging=vehicle_data_pb2.ChargingState.ChargeStateDisconnected)

    # Sentry mode active
    add_field(payload, vehicle_data_pb2.Field.SentryMode, boolean_value=True)

    # Doors locked
    add_field(payload, vehicle_data_pb2.Field.Locked, boolean_value=True)

    return payload


def add_field(payload, field_key, **kwargs):
    """Helper to add a field to the payload."""
    datum = payload.data.add()
    datum.key = field_key

    if 'string_value' in kwargs:
        datum.value.string_value = kwargs['string_value']
    elif 'int_value' in kwargs:
        datum.value.int_value = kwargs['int_value']
    elif 'long_value' in kwargs:
        datum.value.long_value = kwargs['long_value']
    elif 'float_value' in kwargs:
        datum.value.float_value = kwargs['float_value']
    elif 'double_value' in kwargs:
        datum.value.double_value = kwargs['double_value']
    elif 'boolean_value' in kwargs:
        datum.value.boolean_value = kwargs['boolean_value']
    elif 'location' in kwargs:
        lat, lon = kwargs['location']
        datum.value.location_value.latitude = lat
        datum.value.location_value.longitude = lon
    elif 'charging' in kwargs:
        datum.value.charging_value = kwargs['charging']
    elif 'shift_state' in kwargs:
        datum.value.shift_state_value = kwargs['shift_state']
    elif 'doors' in kwargs:
        df, dr, pf, pr, tf, tr = kwargs['doors']
        datum.value.door_value.DriverFront = df
        datum.value.door_value.DriverRear = dr
        datum.value.door_value.PassengerFront = pf
        datum.value.door_value.PassengerRear = pr
        datum.value.door_value.TrunkFront = tf
        datum.value.door_value.TrunkRear = tr


def main():
    parser = argparse.ArgumentParser(
        description="Generate mock Tesla Fleet Telemetry messages"
    )
    parser.add_argument(
        '--scenario',
        choices=['driving', 'charging', 'parked'],
        default='driving',
        help='Scenario to simulate (default: driving)'
    )
    parser.add_argument(
        '--vin',
        default='5YJ3E1EA1MF000000',
        help='Vehicle VIN (default: 5YJ3E1EA1MF000000)'
    )
    parser.add_argument(
        '--output', '-o',
        help='Output file path (default: stdout as hex)'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON (human-readable)'
    )

    args = parser.parse_args()

    # Create message based on scenario
    if args.scenario == 'driving':
        payload = create_driving_message(args.vin)
        print(f"Generated DRIVING scenario for VIN: {args.vin}", file=sys.stderr)
    elif args.scenario == 'charging':
        payload = create_charging_message(args.vin)
        print(f"Generated CHARGING scenario for VIN: {args.vin}", file=sys.stderr)
    else:  # parked
        payload = create_parked_message(args.vin)
        print(f"Generated PARKED scenario for VIN: {args.vin}", file=sys.stderr)

    # Serialize to binary
    binary_data = payload.SerializeToString()
    print(f"Message size: {len(binary_data)} bytes", file=sys.stderr)
    print(f"Fields: {len(payload.data)}", file=sys.stderr)

    # Output
    if args.json:
        # Human-readable output
        print("\n=== Message Details ===", file=sys.stderr)
        print(f"VIN: {payload.vin}")
        print(f"Timestamp: {datetime.fromtimestamp(payload.created_at.seconds)}")
        print(f"\nFields:")
        for datum in payload.data:
            field_name = vehicle_data_pb2.Field.Name(datum.key)
            which = datum.value.WhichOneof('value')
            value = getattr(datum.value, which)
            print(f"  {field_name}: {value}")
    elif args.output:
        # Write to file
        with open(args.output, 'wb') as f:
            f.write(binary_data)
        print(f"\n✓ Written to: {args.output}", file=sys.stderr)
    else:
        # Output as hex to stdout
        print("\n=== Binary Data (hex) ===")
        print(binary_data.hex())


if __name__ == '__main__':
    main()
