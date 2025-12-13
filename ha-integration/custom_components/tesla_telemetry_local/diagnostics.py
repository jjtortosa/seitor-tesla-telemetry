"""Diagnostics support for Tesla Fleet Telemetry Local."""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_MQTT_TOPIC_BASE,
    CONF_VEHICLE_NAME,
    CONF_VEHICLE_VIN,
)


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    data = entry.runtime_data

    # Redact sensitive data from config
    config_data = dict(entry.data)
    if CONF_VEHICLE_VIN in config_data:
        vin = config_data[CONF_VEHICLE_VIN]
        config_data[CONF_VEHICLE_VIN] = f"{vin[:8]}***{vin[-4:]}" if len(vin) > 12 else "***"

    # Get MQTT client state
    mqtt_state = "unknown"
    mqtt_info: dict[str, Any] = {}
    if data and data.mqtt_client:
        mqtt_client = data.mqtt_client
        mqtt_state = "connected" if mqtt_client.connected else "disconnected"
        mqtt_info = {
            "topic_base": config_data.get(CONF_MQTT_TOPIC_BASE, ""),
            "callbacks_registered": len(mqtt_client._callbacks),
            "callback_types": list(mqtt_client._callbacks.keys()),
        }

    return {
        "config": config_data,
        "mqtt": {
            "state": mqtt_state,
            **mqtt_info,
        },
        "integration_version": "2.0.0",
    }
