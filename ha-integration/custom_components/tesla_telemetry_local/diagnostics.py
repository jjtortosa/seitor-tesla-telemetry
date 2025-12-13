"""Diagnostics support for Tesla Fleet Telemetry Local."""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.redact import async_redact_data

from .const import (
    CONF_KAFKA_BROKER,
    CONF_KAFKA_TOPIC,
    CONF_VEHICLE_NAME,
    CONF_VEHICLE_VIN,
)

# Keys to redact from diagnostics
TO_REDACT = {CONF_VEHICLE_VIN}
TO_REDACT_PARTIAL = {CONF_KAFKA_BROKER}


def _redact_broker(broker: str) -> str:
    """Redact IP address from broker but keep port."""
    if ":" in broker:
        host, port = broker.rsplit(":", 1)
        # Redact most of the host but keep structure
        parts = host.split(".")
        if len(parts) == 4:  # IPv4
            return f"{parts[0]}.***.***.{parts[3]}:{port}"
        return f"***:{port}"
    return "***"


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
    if CONF_KAFKA_BROKER in config_data:
        config_data[CONF_KAFKA_BROKER] = _redact_broker(config_data[CONF_KAFKA_BROKER])

    # Get consumer state
    consumer_state = "unknown"
    consumer_info: dict[str, Any] = {}
    if data and data.consumer:
        consumer = data.consumer
        consumer_state = "running" if consumer._running else "stopped"
        consumer_info = {
            "reconnect_attempts": consumer._reconnect_attempts,
            "callbacks_registered": len(consumer._callbacks),
            "callback_types": list(consumer._callbacks.keys()),
        }

    return {
        "config": config_data,
        "consumer": {
            "state": consumer_state,
            **consumer_info,
        },
        "integration_version": "1.0.0",
    }
