"""Constants for Tesla Fleet Telemetry Local integration."""
from typing import Final

from homeassistant.const import Platform

# Domain
DOMAIN: Final = "tesla_telemetry_local"

# Configuration keys
CONF_MQTT_TOPIC_BASE: Final = "mqtt_topic_base"
CONF_VEHICLE_VIN: Final = "vehicle_vin"
CONF_VEHICLE_NAME: Final = "vehicle_name"
CONF_PROXY_URL: Final = "proxy_url"
CONF_TESLA_TOKEN: Final = "tesla_token"
CONF_TELEMETRY_CONFIG: Final = "telemetry_config"
CONF_TELEMETRY_PRESET: Final = "telemetry_preset"

# Default values
DEFAULT_MQTT_TOPIC_BASE: Final = "tesla"
DEFAULT_VEHICLE_NAME: Final = "Tesla"
DEFAULT_PROXY_URL: Final = "https://homeassistant.local:4443"

# Valid telemetry intervals (seconds)
VALID_INTERVALS: Final = [1, 5, 10, 30, 60, 120, 300, 600]

# Telemetry field categories for UI grouping
TELEMETRY_FIELD_CATEGORIES: Final = {
    "location": {
        "name": "Location & Movement",
        "fields": ["Location", "VehicleSpeed", "Gear", "Odometer"],
    },
    "battery": {
        "name": "Battery",
        "fields": ["Soc", "BatteryLevel", "EstBatteryRange", "ChargeLimitSoc"],
    },
    "charging": {
        "name": "Charging",
        "fields": ["ChargeState", "DetailedChargeState"],
    },
    "climate": {
        "name": "Climate",
        "fields": ["InsideTemp", "OutsideTemp"],
    },
    "security": {
        "name": "Security",
        "fields": ["DoorState", "Locked", "SentryMode"],
    },
    "tires": {
        "name": "Tire Pressure",
        "fields": ["TpmsPressureFl", "TpmsPressureFr", "TpmsPressureRl", "TpmsPressureRr"],
    },
}

# All configurable telemetry fields with descriptions
TELEMETRY_FIELD_DESCRIPTIONS: Final = {
    "Location": "GPS coordinates",
    "VehicleSpeed": "Current speed",
    "Gear": "Shift state (P/R/N/D)",
    "Odometer": "Total distance driven",
    "Soc": "State of charge (%)",
    "BatteryLevel": "Battery level (%)",
    "EstBatteryRange": "Estimated range",
    "ChargeLimitSoc": "Charge limit setting",
    "ChargeState": "Charging status",
    "DetailedChargeState": "Detailed charge info",
    "InsideTemp": "Interior temperature",
    "OutsideTemp": "Exterior temperature",
    "DoorState": "Door open/closed state",
    "Locked": "Lock status",
    "SentryMode": "Sentry mode status",
    "TpmsPressureFl": "Front left tire pressure",
    "TpmsPressureFr": "Front right tire pressure",
    "TpmsPressureRl": "Rear left tire pressure",
    "TpmsPressureRr": "Rear right tire pressure",
}

# Telemetry presets
TELEMETRY_PRESETS: Final = {
    "minimal": {
        "name": "Minimal",
        "description": "Low data usage - basic location and battery",
        "fields": {
            "Location": {"interval_seconds": 60},
            "Soc": {"interval_seconds": 300},
        },
    },
    "driving": {
        "name": "Driving",
        "description": "Optimized for tracking drives",
        "fields": {
            "Location": {"interval_seconds": 10},
            "VehicleSpeed": {"interval_seconds": 5},
            "Gear": {"interval_seconds": 1},
            "Soc": {"interval_seconds": 60},
            "BatteryLevel": {"interval_seconds": 60},
            "EstBatteryRange": {"interval_seconds": 120},
            "Odometer": {"interval_seconds": 300},
        },
    },
    "charging": {
        "name": "Charging",
        "description": "Monitor charging sessions",
        "fields": {
            "Location": {"interval_seconds": 300},
            "Soc": {"interval_seconds": 30},
            "BatteryLevel": {"interval_seconds": 30},
            "ChargeState": {"interval_seconds": 5},
            "DetailedChargeState": {"interval_seconds": 10},
            "ChargeLimitSoc": {"interval_seconds": 120},
            "EstBatteryRange": {"interval_seconds": 60},
        },
    },
    "complete": {
        "name": "Complete",
        "description": "All fields with balanced intervals",
        "fields": {
            "Location": {"interval_seconds": 10},
            "VehicleSpeed": {"interval_seconds": 10},
            "Gear": {"interval_seconds": 5},
            "Soc": {"interval_seconds": 60},
            "BatteryLevel": {"interval_seconds": 60},
            "ChargeState": {"interval_seconds": 30},
            "DetailedChargeState": {"interval_seconds": 30},
            "EstBatteryRange": {"interval_seconds": 120},
            "Odometer": {"interval_seconds": 300},
            "InsideTemp": {"interval_seconds": 60},
            "OutsideTemp": {"interval_seconds": 120},
            "DoorState": {"interval_seconds": 10},
            "Locked": {"interval_seconds": 30},
            "SentryMode": {"interval_seconds": 60},
            "ChargeLimitSoc": {"interval_seconds": 120},
            "TpmsPressureFl": {"interval_seconds": 300},
            "TpmsPressureFr": {"interval_seconds": 300},
            "TpmsPressureRl": {"interval_seconds": 300},
            "TpmsPressureRr": {"interval_seconds": 300},
        },
    },
    "custom": {
        "name": "Custom",
        "description": "Configure individual field intervals",
        "fields": {},
    },
}

# Platforms
PLATFORMS: Final = [Platform.DEVICE_TRACKER, Platform.SENSOR, Platform.BINARY_SENSOR, Platform.BUTTON]

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
