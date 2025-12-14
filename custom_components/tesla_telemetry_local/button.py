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

# Button definitions: (key, name, icon, endpoint, method, needs_vehicle_id)
BUTTON_DEFINITIONS = [
    ("wake_up", "Wake Up", "mdi:power", "/api/1/vehicles/{vehicle_id}/wake_up", "POST", True),
    ("flash_lights", "Flash Lights", "mdi:car-light-high", "/api/1/vehicles/{vehicle_id}/command/flash_lights", "POST", True),
    ("honk_horn", "Honk Horn", "mdi:bullhorn", "/api/1/vehicles/{vehicle_id}/command/honk_horn", "POST", True),
    ("open_frunk", "Open Frunk", "mdi:car-select", "/api/1/vehicles/{vehicle_id}/command/actuate_trunk", "POST", True),
    ("open_trunk", "Open Trunk", "mdi:car-back", "/api/1/vehicles/{vehicle_id}/command/actuate_trunk", "POST", True),
    ("open_charge_port", "Open Charge Port", "mdi:ev-plug-type2", "/api/1/vehicles/{vehicle_id}/command/charge_port_door_open", "POST", True),
    ("close_charge_port", "Close Charge Port", "mdi:ev-plug-type2", "/api/1/vehicles/{vehicle_id}/command/charge_port_door_close", "POST", True),
]


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
        _LOGGER.warning("Tesla token not configured - buttons will not be available")
        return

    _LOGGER.info("Setting up Tesla buttons for %s", vehicle_name)

    entities = []
    for key, name, icon, endpoint, method, needs_vehicle_id in BUTTON_DEFINITIONS:
        entities.append(
            TeslaButton(
                vehicle_name=vehicle_name,
                vehicle_vin=vehicle_vin,
                device_info=device_info,
                token=token,
                proxy_url=proxy_url,
                button_key=key,
                button_name=name,
                button_icon=icon,
                endpoint=endpoint,
                method=method,
                needs_vehicle_id=needs_vehicle_id,
            )
        )

    async_add_entities(entities)


class TeslaButton(ButtonEntity):
    """Representation of a Tesla button."""

    _attr_has_entity_name = True

    def __init__(
        self,
        vehicle_name: str,
        vehicle_vin: str,
        device_info: dict[str, Any],
        token: str,
        proxy_url: str | None,
        button_key: str,
        button_name: str,
        button_icon: str,
        endpoint: str,
        method: str,
        needs_vehicle_id: bool,
    ) -> None:
        """Initialize the button."""
        self._vehicle_name = vehicle_name
        self._vehicle_vin = vehicle_vin
        self._token = token
        self._proxy_url = proxy_url
        self._button_key = button_key
        self._endpoint = endpoint
        self._method = method
        self._needs_vehicle_id = needs_vehicle_id
        self._vehicle_id: str | None = None

        # Entity properties
        self._attr_unique_id = f"{vehicle_vin}_{button_key}"
        self._attr_name = button_name
        self._attr_icon = button_icon
        self._attr_device_info = device_info

    async def _get_vehicle_id(self, session) -> str | None:
        """Get the vehicle ID from VIN."""
        if self._vehicle_id:
            return self._vehicle_id

        url = f"{TESLA_API_BASE_URL}/api/1/vehicles"
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                for v in data.get("response", []):
                    if v.get("vin") == self._vehicle_vin:
                        self._vehicle_id = str(v.get("id"))
                        return self._vehicle_id
        return None

    async def async_press(self) -> None:
        """Handle the button press."""
        import aiohttp
        import ssl

        _LOGGER.info("Button pressed: %s for %s", self._button_key, self._vehicle_name)

        ssl_context = ssl.create_default_context()
        if self._proxy_url:
            # Disable SSL verification for self-signed proxy
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

        async with aiohttp.ClientSession(headers=headers) as session:
            try:
                # Get vehicle ID if needed
                if self._needs_vehicle_id:
                    vehicle_id = await self._get_vehicle_id(session)
                    if not vehicle_id:
                        _LOGGER.error("Could not find vehicle ID for VIN %s", self._vehicle_vin[:8])
                        return
                    endpoint = self._endpoint.format(vehicle_id=vehicle_id)
                else:
                    endpoint = self._endpoint

                # Determine URL (proxy for commands, direct for wake_up)
                if self._button_key == "wake_up":
                    url = f"{TESLA_API_BASE_URL}{endpoint}"
                    ssl_ctx = ssl.create_default_context()
                else:
                    # Commands need to go through proxy for signing
                    if self._proxy_url:
                        url = f"{self._proxy_url}{endpoint}"
                        ssl_ctx = ssl_context
                    else:
                        url = f"{TESLA_API_BASE_URL}{endpoint}"
                        ssl_ctx = ssl.create_default_context()

                # Prepare body for specific commands
                body = {}
                if self._button_key == "open_frunk":
                    body = {"which_trunk": "front"}
                elif self._button_key == "open_trunk":
                    body = {"which_trunk": "rear"}

                # Execute request
                if self._method == "POST":
                    async with session.post(url, json=body, ssl=ssl_ctx) as response:
                        if response.status == 200:
                            data = await response.json()
                            result = data.get("response", {}).get("result", False)
                            _LOGGER.info("Button %s: success=%s", self._button_key, result)
                        else:
                            text = await response.text()
                            _LOGGER.error("Button %s failed: %s - %s", self._button_key, response.status, text)

            except Exception as err:
                _LOGGER.error("Error executing button %s: %s", self._button_key, err)
