"""Support for Tesla vehicle number controls."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
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
    """Set up Tesla number controls from a config entry."""
    data = entry.runtime_data
    vehicle_name = data.vehicle_name
    vehicle_vin = data.vehicle_vin
    device_info = data.device_info
    mqtt_client = data.mqtt_client

    # Get API credentials from options
    proxy_url = entry.options.get(CONF_PROXY_URL)
    token = entry.options.get(CONF_TESLA_TOKEN)

    if not token:
        _LOGGER.warning("Tesla token not configured - number controls will not be available")
        return

    _LOGGER.info("Setting up Tesla number controls for %s", vehicle_name)

    entities = [
        TeslaChargeLimitNumber(
            vehicle_name=vehicle_name,
            vehicle_vin=vehicle_vin,
            device_info=device_info,
            token=token,
            proxy_url=proxy_url,
        ),
    ]

    # Register callback for telemetry updates
    mqtt_client.register_callback("ChargeLimitSoc", entities[0].update_from_telemetry)

    async_add_entities(entities)


class TeslaChargeLimitNumber(NumberEntity):
    """Representation of Tesla charge limit control."""

    _attr_has_entity_name = True
    _attr_native_min_value = 50
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "%"
    _attr_mode = NumberMode.SLIDER
    _attr_icon = "mdi:battery-charging-high"

    def __init__(
        self,
        vehicle_name: str,
        vehicle_vin: str,
        device_info: dict[str, Any],
        token: str,
        proxy_url: str | None,
    ) -> None:
        """Initialize the number control."""
        self._vehicle_name = vehicle_name
        self._vehicle_vin = vehicle_vin
        self._token = token
        self._proxy_url = proxy_url
        self._vehicle_id: str | None = None
        self._value: float = 80  # Default

        # Entity properties
        self._attr_unique_id = f"{vehicle_vin}_charge_limit"
        self._attr_name = "Charge Limit"
        self._attr_device_info = device_info

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return self._value

    @callback
    def update_from_telemetry(self, value: Any, data: dict[str, Any]) -> None:
        """Update value from telemetry."""
        try:
            if value is not None:
                self._value = float(value)
                _LOGGER.debug("Charge limit updated from telemetry: %s", self._value)
                self.async_write_ha_state()
        except (ValueError, TypeError) as err:
            _LOGGER.error("Error updating charge limit from telemetry: %s", err)

    async def _get_vehicle_id(self, session) -> str | None:
        """Get the vehicle ID from VIN."""
        if self._vehicle_id:
            return self._vehicle_id

        import ssl
        ssl_ctx = ssl.create_default_context()

        url = f"{TESLA_API_BASE_URL}/api/1/vehicles"
        async with session.get(url, ssl=ssl_ctx) as response:
            if response.status == 200:
                data = await response.json()
                for v in data.get("response", []):
                    if v.get("vin") == self._vehicle_vin:
                        self._vehicle_id = str(v.get("id"))
                        return self._vehicle_id
        return None

    async def async_set_native_value(self, value: float) -> None:
        """Set the charge limit."""
        import aiohttp
        import ssl

        _LOGGER.info("Setting charge limit to %s%% for %s", value, self._vehicle_name)

        ssl_context = ssl.create_default_context()
        if self._proxy_url:
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

        async with aiohttp.ClientSession(headers=headers) as session:
            try:
                vehicle_id = await self._get_vehicle_id(session)
                if not vehicle_id:
                    _LOGGER.error("Could not find vehicle ID")
                    return

                endpoint = f"/api/1/vehicles/{vehicle_id}/command/set_charge_limit"

                # Commands go through proxy
                if self._proxy_url:
                    url = f"{self._proxy_url}{endpoint}"
                else:
                    url = f"{TESLA_API_BASE_URL}{endpoint}"

                body = {"percent": int(value)}

                async with session.post(url, json=body, ssl=ssl_context) as response:
                    if response.status == 200:
                        data = await response.json()
                        result = data.get("response", {}).get("result", False)
                        if result:
                            self._value = value
                            self.async_write_ha_state()
                            _LOGGER.info("Charge limit set to %s%%: success", value)
                        else:
                            _LOGGER.error("Charge limit command returned false")
                    else:
                        text = await response.text()
                        _LOGGER.error("Charge limit command failed: %s - %s", response.status, text)

            except Exception as err:
                _LOGGER.error("Error setting charge limit: %s", err)
