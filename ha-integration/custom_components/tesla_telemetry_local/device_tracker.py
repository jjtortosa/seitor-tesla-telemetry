"""Support for Tesla vehicle location tracking."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

# Using ConfigEntry directly
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tesla device tracker from a config entry."""
    data = entry.runtime_data
    vehicle_name = data.vehicle_name
    vehicle_vin = data.vehicle_vin
    device_info = data.device_info
    mqtt_client = data.mqtt_client

    _LOGGER.info("Setting up Tesla device tracker for %s", vehicle_name)

    # Create tracker entity
    tracker = TeslaDeviceTracker(
        vehicle_name=vehicle_name,
        vehicle_vin=vehicle_vin,
        device_info=device_info,
    )

    async_add_entities([tracker])

    # Register callback for location updates
    mqtt_client.register_callback("Location", tracker.update_location)
    _LOGGER.debug("Registered Location callback for device_tracker")


class TeslaDeviceTracker(TrackerEntity):
    """Representation of a Tesla vehicle location tracker."""

    _attr_has_entity_name = True

    def __init__(
        self,
        vehicle_name: str,
        vehicle_vin: str,
        device_info: dict[str, Any],
    ) -> None:
        """Initialize the tracker."""
        self._vehicle_name = vehicle_name
        self._vehicle_vin = vehicle_vin
        self._latitude: float | None = None
        self._longitude: float | None = None
        self._accuracy: int = 10
        self._speed: float | None = None
        self._last_updated: str | None = None

        # Entity properties
        self._attr_unique_id = f"{vehicle_vin}_location"
        self._attr_name = "Location"
        self._attr_icon = "mdi:car-electric"
        self._attr_device_info = device_info

        _LOGGER.debug("Initialized Tesla device tracker: %s", self._attr_name)

    @property
    def source_type(self) -> SourceType:
        """Return the source type of the tracker."""
        return SourceType.GPS

    @property
    def latitude(self) -> float | None:
        """Return latitude value of the device."""
        return self._latitude

    @property
    def longitude(self) -> float | None:
        """Return longitude value of the device."""
        return self._longitude

    @property
    def location_accuracy(self) -> int:
        """Return the location accuracy of the device."""
        return self._accuracy

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        attrs: dict[str, Any] = {}
        if self._speed is not None:
            attrs["speed"] = self._speed
        if self._last_updated:
            attrs["last_updated"] = self._last_updated
        return attrs

    @callback
    def update_location(self, value: Any, data: dict[str, Any]) -> None:
        """Update location from Kafka message."""
        try:
            lat: float | None = None
            lon: float | None = None

            # Location comes as dict with latitude/longitude from JSON format
            if isinstance(value, dict):
                lat = value.get("latitude")
                lon = value.get("longitude")

            if lat is not None and lon is not None:
                self._latitude = float(lat)
                self._longitude = float(lon)
                self._speed = data.get("VehicleSpeed")
                self._last_updated = data.get("timestamp")

                _LOGGER.debug(
                    "Updated device_tracker %s: lat=%.6f, lon=%.6f",
                    self._attr_unique_id,
                    self._latitude,
                    self._longitude,
                )

                # Trigger state update in Home Assistant
                self.async_write_ha_state()
            else:
                _LOGGER.debug("Location value missing lat/lon: %s", value)

        except (ValueError, TypeError) as err:
            _LOGGER.error("Error updating location: %s", err)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._latitude is not None and self._longitude is not None
