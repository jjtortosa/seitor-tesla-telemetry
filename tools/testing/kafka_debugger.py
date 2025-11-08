#!/usr/bin/env python3
"""
Kafka Message Debugger for Tesla Fleet Telemetry.

This tool connects to your Kafka broker and displays telemetry messages
in human-readable format, helping you debug and understand the data flow.

Usage:
    # Read latest messages
    python3 kafka_debugger.py --broker 192.168.5.105:9092

    # Read from beginning
    python3 kafka_debugger.py --broker 192.168.5.105:9092 --from-beginning

    # Filter by VIN
    python3 kafka_debugger.py --broker 192.168.5.105:9092 --vin 5YJ3E1EA1MF000000

    # Raw binary output
    python3 kafka_debugger.py --broker 192.168.5.105:9092 --raw
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path to import vehicle_data_pb2
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "ha-integration" / "custom_components" / "tesla_telemetry_local"))

try:
    import vehicle_data_pb2
    from kafka import KafkaConsumer
    from kafka.errors import KafkaError
except ImportError as e:
    print(f"Error: {e}")
    print("\nPlease install required packages:")
    print("  pip3 install kafka-python>=2.0.2 protobuf>=5.27.0")
    sys.exit(1)


class TelemetryDebugger:
    """Debug Tesla Fleet Telemetry Kafka messages."""

    def __init__(self, broker: str, topic: str, from_beginning: bool = False):
        """Initialize the debugger."""
        self.broker = broker
        self.topic = topic
        self.from_beginning = from_beginning
        self.consumer = None
        self.message_count = 0

    def connect(self):
        """Connect to Kafka broker."""
        print(f"Connecting to Kafka broker: {self.broker}")
        print(f"Topic: {self.topic}")
        print(f"Reading from: {'beginning' if self.from_beginning else 'latest'}")
        print("-" * 80)

        try:
            self.consumer = KafkaConsumer(
                self.topic,
                bootstrap_servers=[self.broker],
                auto_offset_reset='earliest' if self.from_beginning else 'latest',
                enable_auto_commit=False,
                group_id='tesla_debugger',
                value_deserializer=None,  # We'll handle Protobuf manually
                consumer_timeout_ms=10000,  # 10 second timeout
            )
            print("✓ Connected successfully\n")
        except KafkaError as e:
            print(f"✗ Connection failed: {e}")
            sys.exit(1)

    def parse_message(self, raw_data: bytes) -> dict:
        """Parse Protobuf message."""
        try:
            payload = vehicle_data_pb2.Payload()
            payload.ParseFromString(raw_data)

            # Convert to dictionary
            data = {
                'vin': payload.vin,
                'timestamp': datetime.fromtimestamp(payload.created_at.seconds),
                'is_resend': payload.is_resend,
                'fields': {}
            }

            # Extract all fields
            for datum in payload.data:
                field_name = vehicle_data_pb2.Field.Name(datum.key)
                value = self._extract_value(datum.value)
                data['fields'][field_name] = value

            return data
        except Exception as e:
            return {'error': str(e)}

    def _extract_value(self, value_msg):
        """Extract value from Protobuf Value message."""
        which = value_msg.WhichOneof('value')

        if which is None or which == 'invalid':
            return None

        if which == 'string_value':
            return value_msg.string_value
        if which == 'int_value':
            return value_msg.int_value
        if which == 'long_value':
            return value_msg.long_value
        if which == 'float_value':
            return value_msg.float_value
        if which == 'double_value':
            return value_msg.double_value
        if which == 'boolean_value':
            return value_msg.boolean_value

        if which == 'location_value':
            return {
                'lat': value_msg.location_value.latitude,
                'lon': value_msg.location_value.longitude
            }

        if which == 'charging_value':
            return vehicle_data_pb2.ChargingState.Name(value_msg.charging_value)
        if which == 'shift_state_value':
            return vehicle_data_pb2.ShiftState.Name(value_msg.shift_state_value)

        if which == 'door_value':
            return {
                'driver_front': value_msg.door_value.DriverFront,
                'driver_rear': value_msg.door_value.DriverRear,
                'passenger_front': value_msg.door_value.PassengerFront,
                'passenger_rear': value_msg.door_value.PassengerRear,
                'trunk_front': value_msg.door_value.TrunkFront,
                'trunk_rear': value_msg.door_value.TrunkRear,
            }

        # Fallback
        return str(getattr(value_msg, which, None))

    def format_message(self, data: dict, raw: bool = False) -> str:
        """Format message for display."""
        if 'error' in data:
            return f"✗ Parse error: {data['error']}"

        if raw:
            return str(data)

        # Pretty format
        lines = []
        lines.append(f"Message #{self.message_count}")
        lines.append(f"  VIN: {data['vin']}")
        lines.append(f"  Timestamp: {data['timestamp']}")
        lines.append(f"  Resend: {data['is_resend']}")
        lines.append(f"  Fields: {len(data['fields'])}")

        # Show important fields
        important_fields = [
            'Location', 'VehicleSpeed', 'Gear', 'Soc', 'EstBatteryRange',
            'ChargeState', 'Odometer', 'InsideTemp', 'OutsideTemp', 'Locked'
        ]

        lines.append("\n  Key Fields:")
        for field in important_fields:
            if field in data['fields']:
                value = data['fields'][field]
                lines.append(f"    {field}: {value}")

        # Show all fields if requested
        if len(data['fields']) > len(important_fields):
            other_fields = {k: v for k, v in data['fields'].items() if k not in important_fields}
            lines.append(f"\n  Other Fields ({len(other_fields)}):")
            for field, value in sorted(other_fields.items())[:10]:  # Show first 10
                lines.append(f"    {field}: {value}")
            if len(other_fields) > 10:
                lines.append(f"    ... and {len(other_fields) - 10} more")

        return '\n'.join(lines)

    def run(self, vin_filter: str = None, raw: bool = False, max_messages: int = 0):
        """Start consuming and displaying messages."""
        print("Waiting for messages (Ctrl+C to stop)...\n")

        try:
            for message in self.consumer:
                self.message_count += 1

                # Parse message
                data = self.parse_message(message.value)

                # Filter by VIN if requested
                if vin_filter and data.get('vin') != vin_filter:
                    continue

                # Display
                print(self.format_message(data, raw))
                print("-" * 80)

                # Stop if max reached
                if max_messages > 0 and self.message_count >= max_messages:
                    break

        except KeyboardInterrupt:
            print("\n\n✓ Stopped by user")
        except Exception as e:
            print(f"\n✗ Error: {e}")
        finally:
            if self.consumer:
                self.consumer.close()
            print(f"\nTotal messages processed: {self.message_count}")


def main():
    parser = argparse.ArgumentParser(
        description="Debug Tesla Fleet Telemetry Kafka messages",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Monitor latest messages
  python3 kafka_debugger.py --broker 192.168.5.105:9092

  # Read from beginning
  python3 kafka_debugger.py --broker 192.168.5.105:9092 --from-beginning

  # Filter by VIN
  python3 kafka_debugger.py --broker 192.168.5.105:9092 --vin 5YJ3E1EA1MF000000

  # Show raw data
  python3 kafka_debugger.py --broker 192.168.5.105:9092 --raw

  # Read only 10 messages
  python3 kafka_debugger.py --broker 192.168.5.105:9092 --max 10
        """
    )

    parser.add_argument(
        '--broker', '-b',
        required=True,
        help='Kafka broker address (e.g., 192.168.5.105:9092)'
    )
    parser.add_argument(
        '--topic', '-t',
        default='tesla_telemetry',
        help='Kafka topic name (default: tesla_telemetry)'
    )
    parser.add_argument(
        '--from-beginning',
        action='store_true',
        help='Read from beginning instead of latest'
    )
    parser.add_argument(
        '--vin',
        help='Filter by specific VIN'
    )
    parser.add_argument(
        '--raw',
        action='store_true',
        help='Show raw data instead of formatted'
    )
    parser.add_argument(
        '--max', '-m',
        type=int,
        default=0,
        help='Maximum number of messages to read (0 = unlimited)'
    )

    args = parser.parse_args()

    # Create and run debugger
    debugger = TelemetryDebugger(
        broker=args.broker,
        topic=args.topic,
        from_beginning=args.from_beginning
    )
    debugger.connect()
    debugger.run(
        vin_filter=args.vin,
        raw=args.raw,
        max_messages=args.max
    )


if __name__ == '__main__':
    main()
