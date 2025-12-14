#!/usr/bin/env python3
"""
Tesla Fleet Telemetry Mock Data Generator

Generates realistic MQTT messages simulating Tesla vehicle telemetry.
Useful for demos, testing, and development without a real vehicle.

Usage:
    python mock_telemetry.py --scenario driving
    python mock_telemetry.py --scenario charging --duration 300
    python mock_telemetry.py --scenario parked --continuous
"""

import argparse
import json
import random
import time
import math
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Optional
import paho.mqtt.client as mqtt


@dataclass
class VehicleState:
    """Simulated vehicle state."""
    # Location (Barcelona area)
    latitude: float = 41.3851
    longitude: float = 2.1734
    heading: float = 0.0

    # Motion
    speed: float = 0.0
    gear: str = "P"
    odometer: float = 45678.9

    # Battery
    battery_level: float = 78.0
    estimated_range: float = 285.0
    charge_limit: int = 80

    # Charging
    charge_state: str = "Disconnected"
    charger_voltage: float = 0.0
    charger_current: float = 0.0

    # Climate
    inside_temp: float = 22.5
    outside_temp: float = 18.0

    # TPMS (bar)
    tpms_fl: float = 2.9
    tpms_fr: float = 2.9
    tpms_rl: float = 2.8
    tpms_rr: float = 2.8

    # Security
    locked: bool = True
    sentry_mode: bool = False
    doors_open: bool = False
    charge_port_open: bool = False


class TelemetrySimulator:
    """Simulates Tesla telemetry data and publishes to MQTT."""

    def __init__(
        self,
        mqtt_host: str = "localhost",
        mqtt_port: int = 1883,
        mqtt_user: Optional[str] = None,
        mqtt_password: Optional[str] = None,
        topic_base: str = "tesla",
        vin: str = "DEMO0TESLA0VIN00",
    ):
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.topic_base = topic_base
        self.vin = vin
        self.state = VehicleState()

        # MQTT client (use CallbackAPIVersion for paho-mqtt 2.x)
        try:
            from paho.mqtt.client import CallbackAPIVersion
            self.client = mqtt.Client(
                callback_api_version=CallbackAPIVersion.VERSION2,
                client_id=f"tesla-mock-{vin[:8]}"
            )
        except ImportError:
            # Fallback for older paho-mqtt versions
            self.client = mqtt.Client(client_id=f"tesla-mock-{vin[:8]}")
        if mqtt_user and mqtt_password:
            self.client.username_pw_set(mqtt_user, mqtt_password)

        # Scenario handlers
        self.scenarios = {
            "parked": self._scenario_parked,
            "driving": self._scenario_driving,
            "charging": self._scenario_charging,
            "arriving_home": self._scenario_arriving_home,
            "trip": self._scenario_trip,
        }

    def connect(self) -> bool:
        """Connect to MQTT broker."""
        try:
            self.client.connect(self.mqtt_host, self.mqtt_port, 60)
            self.client.loop_start()
            print(f"✅ Connected to MQTT broker at {self.mqtt_host}:{self.mqtt_port}")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to MQTT: {e}")
            return False

    def disconnect(self):
        """Disconnect from MQTT broker."""
        self.client.loop_stop()
        self.client.disconnect()
        print("🔌 Disconnected from MQTT broker")

    def _publish(self, field: str, value: any, retain: bool = True):
        """Publish a telemetry field to MQTT."""
        topic = f"{self.topic_base}/{self.vin}/v/{field}"
        timestamp = datetime.now(timezone.utc).isoformat()

        if isinstance(value, dict):
            payload = {**value, "timestamp": timestamp}
        else:
            payload = {"value": value, "timestamp": timestamp}

        self.client.publish(topic, json.dumps(payload), retain=retain, qos=1)

    def _publish_connectivity(self, status: str = "connected"):
        """Publish connectivity status."""
        topic = f"{self.topic_base}/{self.vin}/connectivity"
        payload = {"status": status, "timestamp": datetime.now(timezone.utc).isoformat()}
        self.client.publish(topic, json.dumps(payload), retain=True, qos=1)

    def publish_full_state(self):
        """Publish all telemetry fields."""
        s = self.state

        # Location
        self._publish("Location", {"latitude": s.latitude, "longitude": s.longitude})
        self._publish("VehicleSpeed", s.speed)
        self._publish("Gear", s.gear)
        self._publish("Odometer", s.odometer)

        # Battery
        self._publish("Soc", s.battery_level)
        self._publish("BatteryLevel", s.battery_level)
        self._publish("EstBatteryRange", s.estimated_range)
        self._publish("ChargeLimitSoc", s.charge_limit)

        # Charging
        self._publish("ChargeState", s.charge_state)
        self._publish("DetailedChargeState", s.charge_state)
        self._publish("ChargerVoltage", s.charger_voltage)
        self._publish("ChargerActualCurrent", s.charger_current)

        # Climate
        self._publish("InsideTemp", s.inside_temp)
        self._publish("OutsideTemp", s.outside_temp)

        # TPMS
        self._publish("TpmsPressureFl", s.tpms_fl)
        self._publish("TpmsPressureFr", s.tpms_fr)
        self._publish("TpmsPressureRl", s.tpms_rl)
        self._publish("TpmsPressureRr", s.tpms_rr)

        # Security
        self._publish("Locked", s.locked)
        self._publish("SentryMode", s.sentry_mode)
        self._publish("DoorState", "closed" if not s.doors_open else "open")
        self._publish("ChargePortDoorOpen", s.charge_port_open)

        # Connectivity
        self._publish_connectivity("connected")

    def _scenario_parked(self, duration: int, interval: float):
        """Simulate parked vehicle."""
        print("🅿️ Scenario: PARKED")
        self.state.speed = 0
        self.state.gear = "P"
        self.state.locked = True

        elapsed = 0
        while elapsed < duration:
            # Small temperature variations
            self.state.inside_temp += random.uniform(-0.2, 0.2)
            self.state.outside_temp += random.uniform(-0.1, 0.1)

            # Occasional TPMS variations
            if random.random() < 0.1:
                for attr in ['tpms_fl', 'tpms_fr', 'tpms_rl', 'tpms_rr']:
                    current = getattr(self.state, attr)
                    setattr(self.state, attr, current + random.uniform(-0.02, 0.02))

            self.publish_full_state()
            print(f"  📍 Parked | Battery: {self.state.battery_level:.1f}% | Temp: {self.state.inside_temp:.1f}°C")

            time.sleep(interval)
            elapsed += interval

    def _scenario_driving(self, duration: int, interval: float):
        """Simulate driving."""
        print("🚗 Scenario: DRIVING")
        self.state.gear = "D"
        self.state.locked = True
        self.state.sentry_mode = False

        # Barcelona route simulation
        route_points = [
            (41.3851, 2.1734),   # Start: Barcelona center
            (41.3900, 2.1800),   # North
            (41.4000, 2.1900),   # Continue north
            (41.4100, 2.1700),   # Turn west
            (41.4050, 2.1500),   # South-west
            (41.3900, 2.1600),   # Back towards center
        ]

        elapsed = 0
        point_idx = 0

        while elapsed < duration:
            # Update position along route
            if point_idx < len(route_points) - 1:
                progress = (elapsed % 60) / 60  # Move between points every 60s
                p1 = route_points[point_idx]
                p2 = route_points[point_idx + 1]
                self.state.latitude = p1[0] + (p2[0] - p1[0]) * progress
                self.state.longitude = p1[1] + (p2[1] - p1[1]) * progress

                if progress > 0.95:
                    point_idx = (point_idx + 1) % (len(route_points) - 1)

            # Simulate speed variations (city driving)
            target_speed = random.choice([0, 30, 50, 60, 80, 50, 30, 0])
            self.state.speed += (target_speed - self.state.speed) * 0.3
            self.state.speed = max(0, min(120, self.state.speed))

            # Update gear based on speed
            if self.state.speed == 0:
                self.state.gear = "P" if random.random() < 0.3 else "D"
            else:
                self.state.gear = "D"

            # Battery consumption (more at higher speeds)
            consumption = 0.001 * (1 + self.state.speed / 100)
            self.state.battery_level = max(10, self.state.battery_level - consumption)
            self.state.estimated_range = self.state.battery_level * 3.5

            # Odometer
            self.state.odometer += self.state.speed * (interval / 3600)

            # Temperature changes
            if self.state.speed > 50:
                self.state.inside_temp = min(25, self.state.inside_temp + 0.1)

            self.publish_full_state()
            print(f"  🚗 Speed: {self.state.speed:.1f} km/h | Gear: {self.state.gear} | Battery: {self.state.battery_level:.1f}%")

            time.sleep(interval)
            elapsed += interval

    def _scenario_charging(self, duration: int, interval: float):
        """Simulate charging session."""
        print("⚡ Scenario: CHARGING")
        self.state.gear = "P"
        self.state.speed = 0
        self.state.charge_state = "Charging"
        self.state.charge_port_open = True
        self.state.charger_voltage = 230.0
        self.state.charger_current = 16.0

        elapsed = 0
        while elapsed < duration and self.state.battery_level < self.state.charge_limit:
            # Charge rate depends on battery level (slower when fuller)
            charge_rate = 0.5 * (1 - self.state.battery_level / 100)
            self.state.battery_level = min(self.state.charge_limit, self.state.battery_level + charge_rate)
            self.state.estimated_range = self.state.battery_level * 3.5

            # Voltage/current variations
            self.state.charger_voltage = 230 + random.uniform(-2, 2)
            self.state.charger_current = 16 + random.uniform(-0.5, 0.5)

            # Battery warming during charge
            self.state.inside_temp = min(30, self.state.inside_temp + 0.05)

            self.publish_full_state()
            print(f"  ⚡ Charging: {self.state.battery_level:.1f}% | {self.state.charger_voltage:.0f}V @ {self.state.charger_current:.1f}A")

            time.sleep(interval)
            elapsed += interval

        # Charging complete
        if self.state.battery_level >= self.state.charge_limit:
            self.state.charge_state = "Complete"
            self.state.charger_current = 0
            self.publish_full_state()
            print("  ✅ Charging complete!")

    def _scenario_arriving_home(self, duration: int, interval: float):
        """Simulate arriving home (triggers zone automation)."""
        print("🏠 Scenario: ARRIVING HOME")

        # Home location
        home_lat, home_lon = 41.3851, 2.1734

        # Start 2km away
        self.state.latitude = home_lat + 0.02
        self.state.longitude = home_lon + 0.02
        self.state.speed = 50
        self.state.gear = "D"

        elapsed = 0
        while elapsed < duration:
            # Move towards home
            distance_to_home = math.sqrt(
                (self.state.latitude - home_lat)**2 +
                (self.state.longitude - home_lon)**2
            )

            if distance_to_home > 0.0001:
                # Move closer
                self.state.latitude += (home_lat - self.state.latitude) * 0.1
                self.state.longitude += (home_lon - self.state.longitude) * 0.1
                self.state.speed = max(10, self.state.speed - 5)
            else:
                # Arrived
                self.state.speed = 0
                self.state.gear = "P"
                print("  🏠 ARRIVED HOME!")

            self.state.battery_level -= 0.01
            self.state.odometer += self.state.speed * (interval / 3600)

            self.publish_full_state()
            print(f"  📍 Distance to home: {distance_to_home*111:.0f}m | Speed: {self.state.speed:.0f} km/h")

            time.sleep(interval)
            elapsed += interval

    def _scenario_trip(self, duration: int, interval: float):
        """Simulate a complete trip: leave home, drive, arrive destination."""
        print("🗺️ Scenario: COMPLETE TRIP")

        # Phase 1: Leave home
        print("\n--- Phase 1: Leaving home ---")
        self.state.sentry_mode = False
        self.state.locked = False
        time.sleep(2)
        self.state.gear = "D"
        self.publish_full_state()

        # Phase 2: Drive
        print("\n--- Phase 2: Driving ---")
        self._scenario_driving(duration // 2, interval)

        # Phase 3: Arrive and park
        print("\n--- Phase 3: Arriving at destination ---")
        self.state.speed = 0
        self.state.gear = "P"
        self.state.locked = True
        self.state.sentry_mode = True
        self.publish_full_state()
        print("  ✅ Trip complete! Vehicle parked and secured.")

    def run_scenario(self, scenario: str, duration: int = 60, interval: float = 5.0):
        """Run a simulation scenario."""
        if scenario not in self.scenarios:
            print(f"❌ Unknown scenario: {scenario}")
            print(f"Available scenarios: {', '.join(self.scenarios.keys())}")
            return

        print(f"\n{'='*50}")
        print(f"🚀 Starting simulation: {scenario.upper()}")
        print(f"   Duration: {duration}s | Interval: {interval}s")
        print(f"   VIN: {self.vin}")
        print(f"   Topic: {self.topic_base}/{self.vin}/v/#")
        print(f"{'='*50}\n")

        try:
            self.scenarios[scenario](duration, interval)
        except KeyboardInterrupt:
            print("\n⚠️ Simulation interrupted by user")

        print(f"\n{'='*50}")
        print("✅ Simulation complete")
        print(f"{'='*50}")


def main():
    parser = argparse.ArgumentParser(
        description="Tesla Fleet Telemetry Mock Data Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --scenario parked
  %(prog)s --scenario driving --duration 120
  %(prog)s --scenario charging --interval 10
  %(prog)s --scenario arriving_home
  %(prog)s --scenario trip --duration 300

Scenarios:
  parked         Vehicle parked, minimal changes
  driving        Simulates city driving with speed/location changes
  charging       Simulates charging session with battery increase
  arriving_home  Vehicle approaching home zone (triggers automations)
  trip           Complete trip: leave, drive, arrive, park
        """
    )

    parser.add_argument(
        "--scenario", "-s",
        choices=["parked", "driving", "charging", "arriving_home", "trip"],
        default="parked",
        help="Simulation scenario to run"
    )
    parser.add_argument(
        "--duration", "-d",
        type=int,
        default=60,
        help="Duration in seconds (default: 60)"
    )
    parser.add_argument(
        "--interval", "-i",
        type=float,
        default=5.0,
        help="Update interval in seconds (default: 5.0)"
    )
    parser.add_argument(
        "--mqtt-host",
        default="localhost",
        help="MQTT broker host (default: localhost)"
    )
    parser.add_argument(
        "--mqtt-port",
        type=int,
        default=1883,
        help="MQTT broker port (default: 1883)"
    )
    parser.add_argument(
        "--mqtt-user",
        help="MQTT username"
    )
    parser.add_argument(
        "--mqtt-password",
        help="MQTT password"
    )
    parser.add_argument(
        "--topic-base",
        default="tesla",
        help="MQTT topic base (default: tesla)"
    )
    parser.add_argument(
        "--vin",
        default="DEMO0TESLA0VIN00",
        help="Vehicle VIN (default: DEMO0TESLA0VIN00)"
    )
    parser.add_argument(
        "--continuous", "-c",
        action="store_true",
        help="Run continuously until interrupted"
    )

    args = parser.parse_args()

    # Create simulator
    simulator = TelemetrySimulator(
        mqtt_host=args.mqtt_host,
        mqtt_port=args.mqtt_port,
        mqtt_user=args.mqtt_user,
        mqtt_password=args.mqtt_password,
        topic_base=args.topic_base,
        vin=args.vin,
    )

    # Connect to MQTT
    if not simulator.connect():
        return 1

    try:
        if args.continuous:
            print("🔄 Running continuously (Ctrl+C to stop)")
            while True:
                simulator.run_scenario(args.scenario, args.duration, args.interval)
                time.sleep(5)
        else:
            simulator.run_scenario(args.scenario, args.duration, args.interval)
    finally:
        simulator.disconnect()

    return 0


if __name__ == "__main__":
    exit(main())
