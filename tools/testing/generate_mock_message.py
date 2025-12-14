#!/usr/bin/env python3
"""
Generate mock Tesla Fleet Telemetry JSON messages for testing.

This script creates realistic test messages that can be published
to MQTT to verify the Home Assistant integration without a real Tesla vehicle.

Usage:
    python3 generate_mock_message.py --scenario driving
    python3 generate_mock_message.py --scenario charging --vin YOUR_VIN
    python3 generate_mock_message.py --scenario parked --publish

Examples:
    # Generate driving scenario and print MQTT commands
    python3 generate_mock_message.py --scenario driving

    # Generate and publish directly to MQTT
    python3 generate_mock_message.py --scenario charging --publish --mqtt-host 192.168.5.201
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime


def create_driving_scenario(vin: str) -> dict:
    """Create mock data simulating a driving Tesla."""
    return {
        "Location": {"latitude": 41.3874, "longitude": 2.1686},
        "GpsHeading": {"value": 45},
        "VehicleSpeed": {"value": 65},
        "Gear": {"value": "D"},
        "Soc": {"value": 80},
        "BatteryLevel": {"value": 80},
        "EstBatteryRange": {"value": 320.5},
        "Odometer": {"value": 12345.6},
        "InsideTemp": {"value": 22.5},
        "OutsideTemp": {"value": 18.0},
        "ChargeState": {"value": "Disconnected"},
        "Locked": {"value": True},
    }


def create_charging_scenario(vin: str) -> dict:
    """Create mock data simulating a charging Tesla at home."""
    return {
        "Location": {"latitude": 41.3850, "longitude": 2.1700},
        "VehicleSpeed": {"value": 0},
        "Gear": {"value": "P"},
        "Soc": {"value": 45},
        "BatteryLevel": {"value": 45},
        "EstBatteryRange": {"value": 180.0},
        "ChargeState": {"value": "Charging"},
        "ChargerVoltage": {"value": 230},
        "ChargerActualCurrent": {"value": 16},
        "ChargeAmps": {"value": 16},
        "ChargeLimitSoc": {"value": 80},
        "Locked": {"value": True},
    }


def create_parked_scenario(vin: str) -> dict:
    """Create mock data simulating a parked Tesla (not charging)."""
    return {
        "Location": {"latitude": 41.3900, "longitude": 2.1750},
        "VehicleSpeed": {"value": 0},
        "Gear": {"value": "P"},
        "Soc": {"value": 75},
        "BatteryLevel": {"value": 75},
        "EstBatteryRange": {"value": 300.0},
        "ChargeState": {"value": "Disconnected"},
        "SentryMode": {"value": True},
        "Locked": {"value": True},
    }


def generate_mqtt_commands(vin: str, data: dict, topic_base: str = "tesla") -> list:
    """Generate mosquitto_pub commands for each field."""
    commands = []
    for field, payload in data.items():
        topic = f"{topic_base}/{vin}/v/{field}"
        json_payload = json.dumps(payload)
        cmd = f'mosquitto_pub -h $MQTT_HOST -u $MQTT_USER -P $MQTT_PASS -t "{topic}" -m \'{json_payload}\''
        commands.append(cmd)
    return commands


def publish_to_mqtt(vin: str, data: dict, mqtt_host: str, mqtt_user: str, mqtt_pass: str, topic_base: str = "tesla"):
    """Publish messages directly to MQTT broker."""
    for field, payload in data.items():
        topic = f"{topic_base}/{vin}/v/{field}"
        json_payload = json.dumps(payload)

        cmd = [
            "mosquitto_pub",
            "-h", mqtt_host,
            "-u", mqtt_user,
            "-P", mqtt_pass,
            "-t", topic,
            "-m", json_payload
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True)
            print(f"  Published: {topic}")
        except subprocess.CalledProcessError as e:
            print(f"  Error publishing {topic}: {e.stderr.decode()}", file=sys.stderr)
        except FileNotFoundError:
            print("Error: mosquitto_pub not found. Install mosquitto-clients.", file=sys.stderr)
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Generate mock Tesla Fleet Telemetry JSON messages for MQTT testing"
    )
    parser.add_argument(
        '--scenario',
        choices=['driving', 'charging', 'parked'],
        default='driving',
        help='Scenario to simulate (default: driving)'
    )
    parser.add_argument(
        '--vin',
        default='LRWYGCFS3RC210528',
        help='Vehicle VIN (default: LRWYGCFS3RC210528)'
    )
    parser.add_argument(
        '--topic-base',
        default='tesla',
        help='MQTT topic base (default: tesla)'
    )
    parser.add_argument(
        '--publish',
        action='store_true',
        help='Publish directly to MQTT broker'
    )
    parser.add_argument(
        '--mqtt-host',
        default='localhost',
        help='MQTT broker host (default: localhost)'
    )
    parser.add_argument(
        '--mqtt-user',
        default='mqtt_user',
        help='MQTT username (default: mqtt_user)'
    )
    parser.add_argument(
        '--mqtt-pass',
        default='mqtt_pass',
        help='MQTT password (default: mqtt_pass)'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output raw JSON data'
    )

    args = parser.parse_args()

    # Create data based on scenario
    if args.scenario == 'driving':
        data = create_driving_scenario(args.vin)
        scenario_desc = "DRIVING (65 km/h, gear D, 80% battery)"
    elif args.scenario == 'charging':
        data = create_charging_scenario(args.vin)
        scenario_desc = "CHARGING (0 km/h, gear P, 45% battery, charging)"
    else:  # parked
        data = create_parked_scenario(args.vin)
        scenario_desc = "PARKED (0 km/h, gear P, 75% battery, sentry mode)"

    print(f"Scenario: {scenario_desc}")
    print(f"VIN: {args.vin}")
    print(f"Topic base: {args.topic_base}")
    print(f"Fields: {len(data)}")
    print()

    if args.json:
        # Output raw JSON
        print(json.dumps(data, indent=2))
    elif args.publish:
        # Publish to MQTT
        print("Publishing to MQTT...")
        publish_to_mqtt(
            args.vin, data,
            args.mqtt_host, args.mqtt_user, args.mqtt_pass,
            args.topic_base
        )
        print("\nDone! Check Home Assistant for entity updates.")
    else:
        # Output mosquitto_pub commands
        print("MQTT commands (copy/paste to publish):")
        print("=" * 60)
        print()
        print("# Set these environment variables first:")
        print("export MQTT_HOST=localhost")
        print("export MQTT_USER=mqtt_user")
        print("export MQTT_PASS=your_password")
        print()

        commands = generate_mqtt_commands(args.vin, data, args.topic_base)
        for cmd in commands:
            print(cmd)
            print()

        print("=" * 60)
        print(f"\nOr use --publish flag to publish directly:")
        print(f"  python3 {sys.argv[0]} --scenario {args.scenario} --publish --mqtt-host {args.mqtt_host}")


if __name__ == '__main__':
    main()
