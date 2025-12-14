"""Support for Tesla vehicle switches."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_PROXY_URL, CONF_TESLA_TOKEN, DOMAIN

_LOGGER = logging.getLogger(__name__)

# Tesla Fleet API
TESLA_API_BASE_URL = "https://fleet-api.prd.eu.vn.cloud.tesla.com"

# Switch definitions: (key, name, icon_on, icon_off, endpoint_on, endpoint_off, telemetry_field)
SWITCH_DEFINITIONS = [
    (
        "sentry_mode",
        "Sentry Mode",
        "mdi:shield-car",
        "mdi:shield-off",
        "/api/1/vehicles/{vehicle_id}/command/set_sentry_mode",
        "/api/1/vehicles/{vehicle_id}/command/set_sentry_mode",
        "SentryMode",
    ),
    (
        "climate",
        "Climate",
        "mdi:fan",
        "mdi:fan-off",
        "/api/1/vehicles/{vehicle_id}/command/auto_conditioning_start",
        "/api/1/vehicles/{vehicle_id}/command/auto_conditioning_stop",
        None,
    ),
    (
        "charging",
        "Charging",
        "mdi:battery-charging",
        "mdi:battery",
        "/api/1/vehicles/{vehicle_id}/command/charge_start",
        "/api/1/vehicles/{vehicle_id}/command/charge_stop",
        "ChargeState",
    ),
    (
        "locked",
        "Lock",
        "mdi:lock",
        "mdi:lock-open",
        "/api/1/vehicles/{vehicle_id}/command/door_lock",
        "/api/1/vehicles/{vehicle_id}/command/door_unlock",
        "Locked",
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tesla switches from a config entry."""
    data = entry.runtime_data
    vehicle_name = data.vehicle_name
    vehicle_vin = data.vehicle_vin
    device_info = data.device_info
    mqtt_client = data.mqtt_client

    # Get API credentials from options
    proxy_url = entry.options.get(CONF_PROXY_URL)
    token = entry.options.get(CONF_TESLA_TOKEN)

    if not token:
        _LOGGER.warning("Tesla token not configured - switches will not be available")
        return

    _LOGGER.info("Setting up Tesla switches for %s", vehicle_name)

    entities = []
    for key, name, icon_on, icon_off, endpoint_on, endpoint_off, telemetry_field in SWITCH_DEFINITIONS:
        entity = TeslaSwitch(
            vehicle_name=vehicle_name,
            vehicle_vin=vehicle_vin,
            device_info=device_info,
            token=token,
            proxy_url=proxy_url,
            switch_key=key,
            switch_name=name,
            icon_on=icon_on,
            icon_off=icon_off,
            endpoint_on=endpoint_on,
            endpoint_off=endpoint_off,
            telemetry_field=telemetry_field,
        )
        entities.append(entity)

        # Register callback for telemetry updates
        if telemetry_field:
            mqtt_client.register_callback(telemetry_field, entity.update_from_telemetry)

    async_add_entities(entities)


class TeslaSwitch(SwitchEntity):
    """Representation of a Tesla switch."""

    _attr_has_entity_name = True

    def __init__(
        self,
        vehicle_name: str,
        vehicle_vin: str,
        device_info: dict[str, Any],
        token: str,
        proxy_url: str | None,
        switch_key: str,
        switch_name: str,
        icon_on: str,
        icon_off: str,
        endpoint_on: str,
        endpoint_off: str,
        telemetry_field: str | None,
    ) -> None:
        """Initialize the switch."""
        self._vehicle_name = vehicle_name
        self._vehicle_vin = vehicle_vin
        self._token = token
        self._proxy_url = proxy_url
        self._switch_key = switch_key
        self._endpoint_on = endpoint_on
        self._endpoint_off = endpoint_off
        self._telemetry_field = telemetry_field
        self._icon_on = icon_on
        self._icon_off = icon_off
        self._vehicle_id: str | None = None
        self._is_on: bool = False

        # Entity properties
        self._attr_unique_id = f"{vehicle_vin}_{switch_key}"
        self._attr_name = switch_name
        self._attr_device_info = device_info

    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        return self._is_on

    @property
    def icon(self) -> str:
        """Return the icon."""
        return self._icon_on if self._is_on else self._icon_off

    @callback
    def update_from_telemetry(self, value: Any, data: dict[str, Any]) -> None:
        """Update switch state from telemetry."""
        try:
            if self._switch_key == "sentry_mode":
                # SentryMode values: "SentryModeStateOff", "SentryModeStateOn", etc.
                if isinstance(value, str):
                    self._is_on = "on" in value.lower() or "armed" in value.lower()
                else:
                    self._is_on = bool(value)

            elif self._switch_key == "charging":
                # ChargeState values: "Charging", "Complete", "Disconnected", "Stopped", etc.
                if isinstance(value, str):
                    self._is_on = value.lower() == "charging"
                else:
                    self._is_on = bool(value)

            elif self._switch_key == "locked":
                # Locked: true/false
                self._is_on = bool(value)

            _LOGGER.debug("Switch %s updated from telemetry: %s", self._switch_key, self._is_on)
            self.async_write_ha_state()

        except Exception as err:
            _LOGGER.error("Error updating switch %s from telemetry: %s", self._switch_key, err)

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

    async def _send_command(self, endpoint: str, body: dict | None = None) -> bool:
        """Send command to Tesla API."""
        import aiohttp
        import ssl

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
                    return False

                endpoint = endpoint.format(vehicle_id=vehicle_id)

                # Commands go through proxy
                if self._proxy_url:
                    url = f"{self._proxy_url}{endpoint}"
                else:
                    url = f"{TESLA_API_BASE_URL}{endpoint}"

                async with session.post(url, json=body or {}, ssl=ssl_context) as response:
                    if response.status == 200:
                        data = await response.json()
                        result = data.get("response", {}).get("result", False)
                        _LOGGER.info("Switch %s command: success=%s", self._switch_key, result)
                        return result
                    else:
                        text = await response.text()
                        _LOGGER.error("Switch %s command failed: %s - %s", self._switch_key, response.status, text)
                        return False

            except Exception as err:
                _LOGGER.error("Error sending command for switch %s: %s", self._switch_key, err)
                return False

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        _LOGGER.info("Turning on switch %s for %s", self._switch_key, self._vehicle_name)

        body = None
        if self._switch_key == "sentry_mode":
            body = {"on": True}

        success = await self._send_command(self._endpoint_on, body)
        if success:
            self._is_on = True
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        _LOGGER.info("Turning off switch %s for %s", self._switch_key, self._vehicle_name)

        body = None
        if self._switch_key == "sentry_mode":
            body = {"on": False}

        success = await self._send_command(self._endpoint_off, body)
        if success:
            self._is_on = False
            self.async_write_ha_state()
