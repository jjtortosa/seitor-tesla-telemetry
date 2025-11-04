"""Support for Tesla vehicle binary sensors."""
import logging
from typing import Any, Dict, Optional

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from . import CONF_VEHICLE_NAME, CONF_VEHICLE_VIN, DOMAIN

_LOGGER = logging.getLogger(__name__)


# Binary sensor definitions: (name, device_class, icon_on, icon_off, depends_on)
BINARY_SENSOR_DEFINITIONS = [
    ("Driving", BinarySensorDeviceClass.MOVING, "mdi:car-speed-limiter", "mdi:car-parking", ["ShiftState", "Speed"]),
    ("Charging", BinarySensorDeviceClass.BATTERY_CHARGING, "mdi:battery-charging", "mdi:battery", ["ChargingState"]),
    ("Charge Port Open", BinarySensorDeviceClass.DOOR, "mdi:car-door", "mdi:car-door-lock", ["ChargePortDoorOpen"]),
    ("Connected", BinarySensorDeviceClass.CONNECTIVITY, "mdi:wifi", "mdi:wifi-off", ["VehicleConnected"]),
]


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: Optional[DiscoveryInfoType] = None,
) -> None:
    """Set up the Tesla binary sensor platform."""
    if discovery_info is None:
        return

    vehicle_name = discovery_info.get(CONF_VEHICLE_NAME, "Tesla")
    vehicle_vin = discovery_info.get(CONF_VEHICLE_VIN)

    _LOGGER.info("Setting up Tesla binary sensors for %s", vehicle_name)

    # Create binary sensor entities
    entities = []
    for name, device_class, icon_on, icon_off, depends_on in BINARY_SENSOR_DEFINITIONS:
        entity = TeslaBinarySensor(
            hass=hass,
            vehicle_name=vehicle_name,
            vehicle_vin=vehicle_vin,
            sensor_name=name,
            device_class=device_class,
            icon_on=icon_on,
            icon_off=icon_off,
            depends_on=depends_on,
        )
        entities.append(entity)

    async_add_entities(entities, True)

    # Register callbacks with Kafka consumer
    consumer = hass.data[DOMAIN]["consumer"]
    for entity in entities:
        for field in entity._depends_on:
            consumer.register_callback(field, entity.update_value)


class TeslaBinarySensor(BinarySensorEntity):
    """Representation of a Tesla vehicle binary sensor."""

    def __init__(
        self,
        hass: HomeAssistant,
        vehicle_name: str,
        vehicle_vin: str,
        sensor_name: str,
        device_class: BinarySensorDeviceClass,
        icon_on: str,
        icon_off: str,
        depends_on: list[str],
    ) -> None:
        """Initialize the binary sensor."""
        self._hass = hass
        self._vehicle_name = vehicle_name
        self._vehicle_vin = vehicle_vin
        self._sensor_name = sensor_name
        self._depends_on = depends_on
        self._icon_on = icon_on
        self._icon_off = icon_off
        self._state: bool = False
        self._data_cache: Dict[str, Any] = {}
        self._attributes: Dict[str, Any] = {}

        # Entity properties
        self._attr_unique_id = f"tesla_{vehicle_vin.lower()}_{sensor_name.lower().replace(' ', '_')}"
        self._attr_name = f"{vehicle_name} {sensor_name}"
        self._attr_device_class = device_class

        _LOGGER.debug("Initialized Tesla binary sensor: %s", self._attr_name)

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        return self._state

    @property
    def icon(self) -> str:
        """Return the icon to use in the frontend."""
        return self._icon_on if self._state else self._icon_off

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return entity specific state attributes."""
        return self._attributes

    @callback
    async def update_value(self, value: Any, data: Dict[str, Any]) -> None:
        """Update binary sensor value from Kafka message."""
        try:
            # Cache all relevant data
            for field in self._depends_on:
                if field in data:
                    self._data_cache[field] = data[field]

            # Calculate state based on sensor type
            if self._sensor_name == "Driving":
                self._state = self._calculate_driving_state()

            elif self._sensor_name == "Charging":
                self._state = self._calculate_charging_state()

            elif self._sensor_name == "Charge Port Open":
                self._state = self._calculate_charge_port_state()

            elif self._sensor_name == "Connected":
                self._state = self._calculate_connected_state()

            # Update attributes with detection method
            self._attributes["detection_method"] = self._get_detection_method()
            self._attributes["last_updated"] = data.get("timestamp", None)

            _LOGGER.debug(
                "Updated binary sensor %s: %s",
                self._attr_name,
                "on" if self._state else "off",
            )

            # Trigger state update in Home Assistant
            self.async_write_ha_state()

        except Exception as err:
            _LOGGER.error("Error updating binary sensor %s: %s", self._attr_name, err)

    def _calculate_driving_state(self) -> bool:
        """Calculate if vehicle is driving."""
        shift_state = self._data_cache.get("ShiftState", "").lower()
        speed = float(self._data_cache.get("Speed", 0))

        # Vehicle is driving if:
        # - Shift state is D, R, or N (not P = Park)
        # - OR speed > 1 km/h
        return shift_state in ["d", "r", "n"] or speed > 1

    def _calculate_charging_state(self) -> bool:
        """Calculate if vehicle is charging."""
        charging_state = self._data_cache.get("ChargingState", "").lower()

        # Vehicle is charging if charging state is "charging"
        # (vs "complete", "disconnected", "stopped", etc.)
        return charging_state == "charging"

    def _calculate_charge_port_state(self) -> bool:
        """Calculate if charge port is open."""
        charge_port_open = self._data_cache.get("ChargePortDoorOpen", False)

        # Direct boolean value
        if isinstance(charge_port_open, bool):
            return charge_port_open

        # String value (true/false)
        if isinstance(charge_port_open, str):
            return charge_port_open.lower() in ["true", "1", "open"]

        # Numeric value (1 = open, 0 = closed)
        return bool(charge_port_open)

    def _calculate_connected_state(self) -> bool:
        """Calculate if vehicle is connected (has internet)."""
        # If we're receiving messages, vehicle is connected
        # This is a simple heuristic
        vehicle_connected = self._data_cache.get("VehicleConnected", True)

        if isinstance(vehicle_connected, bool):
            return vehicle_connected

        # If not explicitly provided, assume connected if we have recent data
        return True

    def _get_detection_method(self) -> str:
        """Get human-readable detection method."""
        if self._sensor_name == "Driving":
            shift_state = self._data_cache.get("ShiftState", "").upper()
            speed = float(self._data_cache.get("Speed", 0))

            if shift_state in ["D", "R", "N"]:
                return f"Shift state: {shift_state}"
            elif speed > 1:
                return f"Speed: {speed} km/h"
            else:
                return "Parked"

        elif self._sensor_name == "Charging":
            charging_state = self._data_cache.get("ChargingState", "Unknown")
            return f"State: {charging_state}"

        elif self._sensor_name == "Charge Port Open":
            return "Port door sensor"

        elif self._sensor_name == "Connected":
            return "Telemetry stream"

        return "Unknown"

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        # Binary sensors are available if we have at least one required field
        return any(field in self._data_cache for field in self._depends_on)

    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device information for this entity."""
        return {
            "identifiers": {(DOMAIN, self._vehicle_vin)},
            "name": self._vehicle_name,
            "manufacturer": "Tesla",
            "model": "Model Y",
            "sw_version": None,
        }
