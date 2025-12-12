"""Support for Tesla vehicle location tracking using device_tracker.see service."""
import logging
from typing import Any, Dict, Optional

from homeassistant.components.device_tracker import DOMAIN as DT_DOMAIN
from homeassistant.components.device_tracker.const import SourceType
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from . import DOMAIN, CONF_VEHICLE_NAME, CONF_VEHICLE_VIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_scanner(
    hass: HomeAssistant,
    config: ConfigType,
    async_see,
    discovery_info: Optional[DiscoveryInfoType] = None,
) -> bool:
    """Set up the Tesla device tracker scanner."""
    _LOGGER.info("Tesla device_tracker async_setup_scanner called")

    if discovery_info is None:
        _LOGGER.warning("Tesla device_tracker: discovery_info is None")
        return False

    vehicle_name = discovery_info.get(CONF_VEHICLE_NAME, "Tesla")
    vehicle_vin = discovery_info.get(CONF_VEHICLE_VIN)

    if not vehicle_vin:
        _LOGGER.error("Tesla device_tracker: vehicle_vin is missing!")
        return False

    _LOGGER.info("Setting up Tesla device tracker for %s (VIN: %s***)", vehicle_name, vehicle_vin[:8])

    # Create tracker instance
    tracker = TeslaLocationTracker(hass, async_see, vehicle_name, vehicle_vin)

    # Register with Kafka consumer
    consumer = hass.data[DOMAIN]["consumer"]
    consumer.register_callback("Location", tracker.update_location)
    _LOGGER.info("Registered Location callback for device_tracker")

    return True


class TeslaLocationTracker:
    """Tesla location tracker using device_tracker.see service."""

    def __init__(
        self,
        hass: HomeAssistant,
        async_see,
        vehicle_name: str,
        vehicle_vin: str,
    ) -> None:
        """Initialize the tracker."""
        self._hass = hass
        self._async_see = async_see
        self._vehicle_name = vehicle_name
        self._vehicle_vin = vehicle_vin
        self._dev_id = f"tesla_{vehicle_vin.lower()}"

        _LOGGER.debug("Initialized Tesla location tracker: %s", self._dev_id)

    @callback
    def update_location(self, value: Any, data: Dict[str, Any]) -> None:
        """Update location from Kafka message."""
        try:
            lat = None
            lon = None

            # Location comes as dict with latitude/longitude from JSON format
            if isinstance(value, dict):
                lat = value.get("latitude")
                lon = value.get("longitude")

            if lat is not None and lon is not None:
                _LOGGER.debug(
                    "Updating device_tracker %s: lat=%.6f, lon=%.6f",
                    self._dev_id,
                    float(lat),
                    float(lon),
                )

                # Use async_see to update device tracker
                self._hass.async_create_task(
                    self._async_see(
                        dev_id=self._dev_id,
                        host_name=self._vehicle_name,
                        gps=(float(lat), float(lon)),
                        gps_accuracy=10,
                        source_type=SourceType.GPS,
                        icon="mdi:car-electric",
                        attributes={
                            "friendly_name": f"{self._vehicle_name} Location",
                            "last_updated": data.get("timestamp"),
                            "speed": data.get("VehicleSpeed"),
                        },
                    )
                )
            else:
                _LOGGER.debug("Location value not a dict or missing lat/lon: %s", value)

        except (ValueError, TypeError) as err:
            _LOGGER.error("Error updating location: %s", err)
