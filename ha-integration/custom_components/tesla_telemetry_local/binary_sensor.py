"""Support for Tesla vehicle binary sensors."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

# Using ConfigEntry directly
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


# Binary sensor definitions: (key, name, device_class, icon_on, icon_off, depends_on)
BINARY_SENSOR_DEFINITIONS: list[tuple[str, str, BinarySensorDeviceClass, str, str, list[str]]] = [
    ("driving", "Driving", BinarySensorDeviceClass.MOVING, "mdi:car-speed-limiter", "mdi:car-parking", ["Gear", "VehicleSpeed"]),
    ("charging", "Charging", BinarySensorDeviceClass.BATTERY_CHARGING, "mdi:battery-charging", "mdi:battery", ["ChargingState", "ChargeState"]),
    ("charge_port_open", "Charge Port", BinarySensorDeviceClass.DOOR, "mdi:ev-plug-type2", "mdi:ev-plug-type2", ["ChargePortDoorOpen"]),
    ("connected", "Connected", BinarySensorDeviceClass.CONNECTIVITY, "mdi:wifi", "mdi:wifi-off", []),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tesla binary sensors from a config entry."""
    data = entry.runtime_data
    vehicle_name = data.vehicle_name
    vehicle_vin = data.vehicle_vin
    device_info = data.device_info
    mqtt_client = data.mqtt_client

    _LOGGER.info("Setting up Tesla binary sensors for %s", vehicle_name)

    # Create binary sensor entities
    entities: list[TeslaBinarySensor] = []
    for key, name, device_class, icon_on, icon_off, depends_on in BINARY_SENSOR_DEFINITIONS:
        entity = TeslaBinarySensor(
            vehicle_name=vehicle_name,
            vehicle_vin=vehicle_vin,
            device_info=device_info,
            sensor_key=key,
            sensor_name=name,
            device_class=device_class,
            icon_on=icon_on,
            icon_off=icon_off,
            depends_on=depends_on,
        )
        entities.append(entity)

    async_add_entities(entities)

    # Register callbacks with MQTT client
    for entity in entities:
        for field in entity.depends_on:
            mqtt_client.register_callback(field, entity.update_value)
        # Also register for connectivity updates
        if entity._sensor_key == "connected":
            mqtt_client.register_callback("connectivity", entity.update_value)


class TeslaBinarySensor(BinarySensorEntity):
    """Representation of a Tesla vehicle binary sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        vehicle_name: str,
        vehicle_vin: str,
        device_info: dict[str, Any],
        sensor_key: str,
        sensor_name: str,
        device_class: BinarySensorDeviceClass,
        icon_on: str,
        icon_off: str,
        depends_on: list[str],
    ) -> None:
        """Initialize the binary sensor."""
        self._vehicle_name = vehicle_name
        self._vehicle_vin = vehicle_vin
        self._sensor_key = sensor_key
        self._depends_on = depends_on
        self._icon_on = icon_on
        self._icon_off = icon_off
        self._state: bool = False
        self._data_cache: dict[str, Any] = {}
        self._last_updated: str | None = None

        # Entity properties
        self._attr_unique_id = f"{vehicle_vin}_{sensor_key}"
        self._attr_translation_key = sensor_key
        self._attr_name = sensor_name
        self._attr_device_class = device_class
        self._attr_device_info = device_info

        _LOGGER.debug("Initialized Tesla binary sensor: %s", self._attr_name)

    @property
    def depends_on(self) -> list[str]:
        """Return the list of fields this sensor depends on."""
        return self._depends_on

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        return self._state

    @property
    def icon(self) -> str:
        """Return the icon to use in the frontend."""
        return self._icon_on if self._state else self._icon_off

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        attrs: dict[str, Any] = {
            "detection_method": self._get_detection_method(),
        }
        if self._last_updated:
            attrs["last_updated"] = self._last_updated
        return attrs

    @callback
    def update_value(self, value: Any, data: dict[str, Any]) -> None:
        """Update binary sensor value from Kafka message."""
        try:
            # Cache all relevant data
            for field in self._depends_on:
                if field in data:
                    self._data_cache[field] = data[field]

            # Calculate state based on sensor type
            if self._sensor_key == "driving":
                self._state = self._calculate_driving_state()

            elif self._sensor_key == "charging":
                self._state = self._calculate_charging_state()

            elif self._sensor_key == "charge_port_open":
                self._state = self._calculate_charge_port_state()

            elif self._sensor_key == "connected":
                self._state = True  # If we receive any data, we're connected

            self._last_updated = data.get("timestamp")

            _LOGGER.debug(
                "Updated binary sensor %s: %s",
                self._attr_name,
                "on" if self._state else "off",
            )

            # Trigger state update in Home Assistant
            self.async_write_ha_state()

        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Error updating binary sensor %s: %s", self._attr_name, err)

    def _calculate_driving_state(self) -> bool:
        """Calculate if vehicle is driving."""
        # Check Gear field first
        gear = self._data_cache.get("Gear", "")
        if isinstance(gear, str):
            gear = gear.lower()
            if gear in ["d", "r", "n"]:
                return True

        # Fallback to speed
        speed = self._data_cache.get("VehicleSpeed", 0)
        try:
            return float(speed) > 1
        except (ValueError, TypeError):
            return False

    def _calculate_charging_state(self) -> bool:
        """Calculate if vehicle is charging."""
        # Check both possible field names
        for field in ["ChargingState", "ChargeState"]:
            state = self._data_cache.get(field, "")
            if isinstance(state, str) and state.lower() == "charging":
                return True
        return False

    def _calculate_charge_port_state(self) -> bool:
        """Calculate if charge port is open."""
        charge_port_open = self._data_cache.get("ChargePortDoorOpen", False)

        if isinstance(charge_port_open, bool):
            return charge_port_open

        if isinstance(charge_port_open, str):
            return charge_port_open.lower() in ["true", "1", "open"]

        return bool(charge_port_open)

    def _get_detection_method(self) -> str:
        """Get human-readable detection method."""
        if self._sensor_key == "driving":
            gear = self._data_cache.get("Gear", "")
            if isinstance(gear, str) and gear.upper() in ["D", "R", "N"]:
                return f"Shift state: {gear.upper()}"
            speed = self._data_cache.get("VehicleSpeed", 0)
            try:
                if float(speed) > 1:
                    return f"Speed: {speed} km/h"
            except (ValueError, TypeError):
                pass
            return "Parked"

        elif self._sensor_key == "charging":
            for field in ["ChargingState", "ChargeState"]:
                state = self._data_cache.get(field)
                if state:
                    return f"State: {state}"
            return "Unknown"

        elif self._sensor_key == "charge_port_open":
            return "Port door sensor"

        elif self._sensor_key == "connected":
            return "Telemetry stream"

        return "Unknown"

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        # Connected sensor is always available
        if self._sensor_key == "connected":
            return True
        # Other sensors need at least one data point
        return len(self._data_cache) > 0 or self._last_updated is not None
