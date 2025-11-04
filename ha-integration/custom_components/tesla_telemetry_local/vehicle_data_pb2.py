"""
Tesla Vehicle Data Protobuf Schema (Placeholder).

This file should be generated from Tesla's official vehicle_data.proto schema.

To generate this file:
1. Download vehicle_data.proto from Tesla's fleet-telemetry repository:
   https://github.com/teslamotors/fleet-telemetry/blob/main/protos/vehicle_data.proto

2. Install protobuf compiler:
   pip install protobuf

3. Compile the .proto file:
   protoc --python_out=. vehicle_data.proto

4. Replace this file with the generated vehicle_data_pb2.py

For development/testing, the kafka_consumer.py uses a simplified parser
that can handle JSON messages. Replace with proper Protobuf parsing in production.

Example usage after compilation:
    from . import vehicle_data_pb2

    vehicle_data = vehicle_data_pb2.VehicleData()
    vehicle_data.ParseFromString(raw_bytes)

    latitude = vehicle_data.location.latitude
    longitude = vehicle_data.location.longitude
    speed = vehicle_data.speed
    # etc.
"""

# PLACEHOLDER - This will be replaced with actual Protobuf generated code

# Common fields structure (for reference):
#
# VehicleData:
#   - timestamp (int64)
#   - vin (string)
#   - location:
#       - latitude (double)
#       - longitude (double)
#       - heading (int32)
#   - speed (int32)
#   - shift_state (string) - P, D, R, N
#   - soc (int32) - Battery percentage
#   - est_battery_range (double)
#   - charging_state (string)
#   - charger_voltage (int32)
#   - charger_actual_current (int32)
#   - charge_port_door_open (bool)
#   - odometer (double)
#   - ... many more fields

class VehicleData:
    """Placeholder class for Vehicle Data."""

    def ParseFromString(self, data: bytes) -> None:
        """Parse Protobuf data (placeholder)."""
        raise NotImplementedError(
            "vehicle_data_pb2.py must be generated from vehicle_data.proto. "
            "See docstring for instructions."
        )


# Note: The actual generated file will have thousands of lines
# with complete message definitions, field descriptors, and serialization code.
# This is just a placeholder to allow the integration to load.
# The kafka_consumer.py currently uses a simplified JSON parser as fallback.
