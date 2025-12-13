"""Constants for Tesla Fleet Telemetry Local integration."""
from typing import Final

from homeassistant.const import Platform

# Domain
DOMAIN: Final = "tesla_telemetry_local"

# Configuration keys
CONF_MQTT_TOPIC_BASE: Final = "mqtt_topic_base"
CONF_VEHICLE_VIN: Final = "vehicle_vin"
CONF_VEHICLE_NAME: Final = "vehicle_name"

# Default values
DEFAULT_MQTT_TOPIC_BASE: Final = "tesla"
DEFAULT_VEHICLE_NAME: Final = "Tesla"

# Platforms
PLATFORMS: Final = [Platform.DEVICE_TRACKER, Platform.SENSOR, Platform.BINARY_SENSOR]

# VIN validation
VIN_LENGTH: Final = 17

# Telemetry field mappings (Tesla → Home Assistant)
TELEMETRY_FIELDS: Final = {
    # Speed and movement
    "VehicleSpeed": "speed",
    "Gear": "shift_state",
    "Odometer": "odometer",

    # Battery
    "Soc": "battery",
    "BatteryLevel": "battery",
    "EstBatteryRange": "range",

    # Charging
    "ChargeState": "charging_state",
    "ChargingState": "charging_state",
    "ChargerVoltage": "charger_voltage",
    "ChargerActualCurrent": "charger_current",
    "ChargePortDoorOpen": "charge_port_open",

    # Location
    "Location": "location",
    "Latitude": "latitude",
    "Longitude": "longitude",
}

# Sensor configurations
SENSOR_CONFIGS: Final = {
    "speed": {
        "name": "Speed",
        "unit": "km/h",
        "icon": "mdi:speedometer",
        "device_class": None,
        "state_class": "measurement",
    },
    "shift_state": {
        "name": "Shift State",
        "unit": None,
        "icon": "mdi:car-shift-pattern",
        "device_class": None,
        "state_class": None,
    },
    "battery": {
        "name": "Battery",
        "unit": "%",
        "icon": "mdi:battery",
        "device_class": "battery",
        "state_class": "measurement",
    },
    "range": {
        "name": "Range",
        "unit": "km",
        "icon": "mdi:map-marker-distance",
        "device_class": "distance",
        "state_class": "measurement",
    },
    "charging_state": {
        "name": "Charging State",
        "unit": None,
        "icon": "mdi:ev-station",
        "device_class": None,
        "state_class": None,
    },
    "charger_voltage": {
        "name": "Charger Voltage",
        "unit": "V",
        "icon": "mdi:lightning-bolt",
        "device_class": "voltage",
        "state_class": "measurement",
    },
    "charger_current": {
        "name": "Charger Current",
        "unit": "A",
        "icon": "mdi:current-ac",
        "device_class": "current",
        "state_class": "measurement",
    },
    "odometer": {
        "name": "Odometer",
        "unit": "km",
        "icon": "mdi:counter",
        "device_class": "distance",
        "state_class": "total_increasing",
    },
}

# Binary sensor configurations
BINARY_SENSOR_CONFIGS: Final = {
    "driving": {
        "name": "Driving",
        "icon": "mdi:car",
        "device_class": "moving",
    },
    "charging": {
        "name": "Charging",
        "icon": "mdi:battery-charging",
        "device_class": "battery_charging",
    },
    "charge_port_open": {
        "name": "Charge Port",
        "icon": "mdi:ev-plug-type2",
        "device_class": "door",
    },
    "connected": {
        "name": "Connected",
        "icon": "mdi:wifi",
        "device_class": "connectivity",
    },
}
