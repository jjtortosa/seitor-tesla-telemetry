"""Support for Tesla vehicle buttons."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity, ButtonDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_PROXY_URL, CONF_TESLA_TOKEN, DOMAIN

_LOGGER = logging.getLogger(__name__)

# Tesla Fleet API
TESLA_API_BASE_URL = "https://fleet-api.prd.eu.vn.cloud.tesla.com"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tesla buttons from a config entry."""
    data = entry.runtime_data
    vehicle_name = data.vehicle_name
    vehicle_vin = data.vehicle_vin
    device_info = data.device_info

    # Get API credentials from options
    proxy_url = entry.options.get(CONF_PROXY_URL)
    token = entry.options.get(CONF_TESLA_TOKEN)

    if not token:
        _LOGGER.warning("Tesla token not configured - wake up button will not be available")
        return

    _LOGGER.info("Setting up Tesla buttons for %s", vehicle_name)

    entities = [
        TeslaWakeUpButton(
            vehicle_name=vehicle_name,
            vehicle_vin=vehicle_vin,
            device_info=device_info,
            token=token,
        ),
    ]

    async_add_entities(entities)


class TeslaWakeUpButton(ButtonEntity):
    """Representation of a Tesla wake up button."""

    _attr_has_entity_name = True
    _attr_device_class = ButtonDeviceClass.RESTART
    _attr_icon = "mdi:power"

    def __init__(
        self,
        vehicle_name: str,
        vehicle_vin: str,
        device_info: dict[str, Any],
        token: str,
    ) -> None:
        """Initialize the button."""
        self._vehicle_name = vehicle_name
        self._vehicle_vin = vehicle_vin
        self._token = token
        self._vehicle_id: str | None = None

        # Entity properties
        self._attr_unique_id = f"{vehicle_vin}_wake_up"
        self._attr_name = "Wake Up"
        self._attr_device_info = device_info

    async def async_press(self) -> None:
        """Handle the button press."""
        import aiohttp
        import ssl

        _LOGGER.info("Waking up vehicle %s", self._vehicle_name)

        # Create SSL context that doesn't verify (for simplicity)
        ssl_context = ssl.create_default_context()

        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

        async with aiohttp.ClientSession(headers=headers) as session:
            try:
                # First, get vehicle ID if we don't have it
                if not self._vehicle_id:
                    url = f"{TESLA_API_BASE_URL}/api/1/vehicles"
                    async with session.get(url, ssl=ssl_context) as response:
                        if response.status == 200:
                            data = await response.json()
                            vehicles = data.get("response", [])
                            for v in vehicles:
                                if v.get("vin") == self._vehicle_vin:
                                    self._vehicle_id = str(v.get("id"))
                                    break

                if not self._vehicle_id:
                    _LOGGER.error("Could not find vehicle ID for VIN %s", self._vehicle_vin[:8])
                    return

                # Send wake up command
                url = f"{TESLA_API_BASE_URL}/api/1/vehicles/{self._vehicle_id}/wake_up"
                async with session.post(url, ssl=ssl_context) as response:
                    if response.status == 200:
                        data = await response.json()
                        state = data.get("response", {}).get("state", "unknown")
                        _LOGGER.info("Wake up sent - vehicle state: %s", state)
                    else:
                        text = await response.text()
                        _LOGGER.error("Wake up failed: %s - %s", response.status, text)

            except Exception as err:
                _LOGGER.error("Error waking up vehicle: %s", err)
