"""Support for Tesla vehicle location tracking."""
import logging
from typing import Any, Dict, Optional

from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from . import DOMAIN, CONF_VEHICLE_NAME, CONF_VEHICLE_VIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: Optional[DiscoveryInfoType] = None,
) -> None:
    """Set up the Tesla device tracker platform."""
    if discovery_info is None:
        return

    vehicle_name = discovery_info.get(CONF_VEHICLE_NAME, "Tesla")
    vehicle_vin = discovery_info.get(CONF_VEHICLE_VIN)

    _LOGGER.info("Setting up Tesla device tracker for %s", vehicle_name)

    # Create device tracker entity
    entity = TeslaDeviceTracker(
        hass=hass,
        vehicle_name=vehicle_name,
        vehicle_vin=vehicle_vin,
    )

    async_add_entities([entity], True)

    # Register with Kafka consumer
    consumer = hass.data[DOMAIN]["consumer"]
    consumer.register_callback("Location", entity.update_location)
    consumer.register_callback("Latitude", entity.update_location)
    consumer.register_callback("Longitude", entity.update_location)


class TeslaDeviceTracker(TrackerEntity):
    """Representation of a Tesla vehicle device tracker."""

    def __init__(
        self,
        hass: HomeAssistant,
        vehicle_name: str,
        vehicle_vin: str,
    ) -> None:
        """Initialize the device tracker."""
        self._hass = hass
        self._vehicle_name = vehicle_name
        self._vehicle_vin = vehicle_vin
        self._latitude: Optional[float] = None
        self._longitude: Optional[float] = None
        self._accuracy: int = 10  # GPS accuracy in meters
        self._attributes: Dict[str, Any] = {}

        # Generate unique ID from VIN
        self._attr_unique_id = f"tesla_{vehicle_vin.lower()}_location"
        self._attr_name = f"{vehicle_name} Location"

        _LOGGER.debug("Initialized Tesla device tracker: %s", self._attr_name)

    @property
    def latitude(self) -> Optional[float]:
        """Return latitude value of the device."""
        return self._latitude

    @property
    def longitude(self) -> Optional[float]:
        """Return longitude value of the device."""
        return self._longitude

    @property
    def location_accuracy(self) -> int:
        """Return the location accuracy of the device.

        Value in meters.
        """
        return self._accuracy

    @property
    def source_type(self) -> SourceType:
        """Return the source type of the device tracker."""
        return SourceType.GPS

    @property
    def icon(self) -> str:
        """Return the icon to use in the frontend."""
        return "mdi:car-electric"

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return entity specific state attributes."""
        return self._attributes

    @callback
    async def update_location(self, value: Any, data: Dict[str, Any]) -> None:
        """Update location from Kafka message."""
        try:
            # Extract latitude and longitude from data
            if "Latitude" in data and "Longitude" in data:
                self._latitude = float(data["Latitude"])
                self._longitude = float(data["Longitude"])

                _LOGGER.debug(
                    "Updated location: lat=%.6f, lon=%.6f",
                    self._latitude,
                    self._longitude,
                )

            # Extract heading if available
            if "Heading" in data:
                self._attributes["heading"] = data["Heading"]

            # Extract speed if available (for reference)
            if "Speed" in data:
                self._attributes["speed"] = data["Speed"]

            # Extract GPS accuracy if available
            if "GpsAccuracy" in data:
                self._accuracy = int(data["GpsAccuracy"])
                self._attributes["gps_accuracy"] = self._accuracy

            # Trigger state update in Home Assistant
            self.async_write_ha_state()

        except (ValueError, TypeError, KeyError) as err:
            _LOGGER.error("Error updating location: %s", err)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        # Entity is available if we have valid coordinates
        return self._latitude is not None and self._longitude is not None

    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device information for this entity."""
        return {
            "identifiers": {(DOMAIN, self._vehicle_vin)},
            "name": self._vehicle_name,
            "manufacturer": "Tesla",
            "model": "Model Y",  # Could be extracted from VIN or data
            "sw_version": None,  # Could be populated from telemetry data
        }
