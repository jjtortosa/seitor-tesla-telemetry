"""Support for Tesla vehicle binary sensors."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Timeout for considering vehicle asleep (no telemetry received)
AWAKE_TIMEOUT_MINUTES = 5


# Binary sensor definitions: (key, name, device_class, icon_on, icon_off, depends_on)
BINARY_SENSOR_DEFINITIONS: list[tuple[str, str, BinarySensorDeviceClass, str, str, list[str]]] = [
    ("driving", "Driving", BinarySensorDeviceClass.MOVING, "mdi:car-speed-limiter", "mdi:car-parking", ["Gear", "VehicleSpeed"]),
    ("charging", "Charging", BinarySensorDeviceClass.BATTERY_CHARGING, "mdi:battery-charging", "mdi:battery", ["ChargingState", "ChargeState"]),
    ("charge_port_open", "Charge Port", BinarySensorDeviceClass.DOOR, "mdi:ev-plug-type2", "mdi:ev-plug-type2", ["ChargePortDoorOpen"]),
    ("locked", "Locked", BinarySensorDeviceClass.LOCK, "mdi:car-key", "mdi:car-key", ["Locked"]),
    ("sentry_mode", "Sentry Mode", None, "mdi:cctv", "mdi:cctv-off", ["SentryMode"]),
    ("doors_open", "Doors", BinarySensorDeviceClass.DOOR, "mdi:car-door", "mdi:car-door", ["DoorState"]),
    ("awake", "Awake", BinarySensorDeviceClass.CONNECTIVITY, "mdi:sleep-off", "mdi:sleep", []),
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
    awake_entity: TeslaBinarySensor | None = None

    for key, name, device_class, icon_on, icon_off, depends_on in BINARY_SENSOR_DEFINITIONS:
        entity = TeslaBinarySensor(
            hass=hass,
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
        if key == "awake":
            awake_entity = entity

    async_add_entities(entities)

    # Register callbacks with MQTT client
    for entity in entities:
        for field in entity.depends_on:
            mqtt_client.register_callback(field, entity.update_value)
        # Register awake sensor for any telemetry data
        if entity._sensor_key == "awake":
            mqtt_client.register_callback("any", entity.update_value)

    # Set up periodic check for awake timeout
    if awake_entity:
        async def check_awake_timeout(now: datetime) -> None:
            """Check if vehicle should be marked as asleep."""
            awake_entity.check_timeout()

        # Check every minute
        entry.async_on_unload(
            async_track_time_interval(hass, check_awake_timeout, timedelta(minutes=1))
        )


class TeslaBinarySensor(BinarySensorEntity):
    """Representation of a Tesla vehicle binary sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        hass: HomeAssistant,
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
        self._hass = hass
        self._vehicle_name = vehicle_name
        self._vehicle_vin = vehicle_vin
        self._sensor_key = sensor_key
        self._depends_on = depends_on
        self._icon_on = icon_on
        self._icon_off = icon_off
        self._state: bool = False
        self._data_cache: dict[str, Any] = {}
        self._last_updated: str | None = None
        self._last_message_time: datetime | None = None

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
        """Update binary sensor value from MQTT message."""
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

            elif self._sensor_key == "locked":
                self._state = self._calculate_locked_state()

            elif self._sensor_key == "sentry_mode":
                self._state = self._calculate_sentry_mode_state()

            elif self._sensor_key == "doors_open":
                self._state = self._calculate_doors_state()

            elif self._sensor_key == "awake":
                # If we receive any data, vehicle is awake
                self._state = True
                self._last_message_time = datetime.now()

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

    @callback
    def check_timeout(self) -> None:
        """Check if awake sensor should timeout to asleep."""
        if self._sensor_key != "awake":
            return

        if self._last_message_time is None:
            # No message ever received
            if self._state:
                self._state = False
                self.async_write_ha_state()
            return

        time_since_last = datetime.now() - self._last_message_time
        if time_since_last > timedelta(minutes=AWAKE_TIMEOUT_MINUTES):
            if self._state:
                _LOGGER.debug(
                    "Vehicle %s marked as asleep (no data for %s minutes)",
                    self._vehicle_name,
                    AWAKE_TIMEOUT_MINUTES,
                )
                self._state = False
                self.async_write_ha_state()

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

    def _calculate_locked_state(self) -> bool:
        """Calculate if vehicle is locked."""
        locked = self._data_cache.get("Locked", False)

        if isinstance(locked, bool):
            return locked

        if isinstance(locked, str):
            return locked.lower() in ["true", "1", "locked"]

        return bool(locked)

    def _calculate_sentry_mode_state(self) -> bool:
        """Calculate if sentry mode is active."""
        sentry = self._data_cache.get("SentryMode", False)

        if isinstance(sentry, bool):
            return sentry

        if isinstance(sentry, str):
            return sentry.lower() in ["true", "1", "on", "active"]

        return bool(sentry)

    def _calculate_doors_state(self) -> bool:
        """Calculate if any door is open."""
        door_state = self._data_cache.get("DoorState", "closed")

        if isinstance(door_state, str):
            # Door is open if state is anything other than "closed"
            return door_state.lower() != "closed"

        if isinstance(door_state, bool):
            return door_state

        return bool(door_state)

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

        elif self._sensor_key == "locked":
            locked = self._data_cache.get("Locked")
            return f"Locked: {locked}" if locked is not None else "Unknown"

        elif self._sensor_key == "sentry_mode":
            sentry = self._data_cache.get("SentryMode")
            return f"Sentry: {sentry}" if sentry is not None else "Unknown"

        elif self._sensor_key == "doors_open":
            door_state = self._data_cache.get("DoorState", "Unknown")
            return f"Door state: {door_state}"

        elif self._sensor_key == "awake":
            if self._last_message_time:
                return f"Last data: {self._last_message_time.strftime('%H:%M:%S')}"
            return "No data received"

        return "Unknown"

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        # Awake sensor is always available
        if self._sensor_key == "awake":
            return True
        # Other sensors need at least one data point
        return len(self._data_cache) > 0 or self._last_updated is not None
