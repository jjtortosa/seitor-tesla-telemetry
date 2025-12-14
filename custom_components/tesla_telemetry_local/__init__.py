"""
Tesla Fleet Telemetry Local Integration for Home Assistant.

This integration connects to a self-hosted Tesla Fleet Telemetry server
via MQTT and creates real-time entities for vehicle data.
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo

from .const import (
    CONF_MQTT_TOPIC_BASE,
    CONF_VEHICLE_NAME,
    CONF_VEHICLE_VIN,
    DEFAULT_MQTT_TOPIC_BASE,
    DEFAULT_VEHICLE_NAME,
    DOMAIN,
    PLATFORMS,
)
from .mqtt_client import TeslaMQTTClient

_LOGGER = logging.getLogger(__name__)


class TeslaTelemetryData:
    """Runtime data for Tesla Telemetry integration."""

    def __init__(
        self,
        mqtt_client: TeslaMQTTClient,
        vehicle_vin: str,
        vehicle_name: str,
        device_info: DeviceInfo,
    ) -> None:
        """Initialize runtime data."""
        self.mqtt_client = mqtt_client
        self.vehicle_vin = vehicle_vin
        self.vehicle_name = vehicle_name
        self.device_info = device_info
        self.entities: dict[str, Any] = {}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tesla Telemetry Local from a config entry."""
    topic_base = entry.data.get(CONF_MQTT_TOPIC_BASE, DEFAULT_MQTT_TOPIC_BASE)
    vehicle_vin = entry.data[CONF_VEHICLE_VIN]
    vehicle_name = entry.data.get(CONF_VEHICLE_NAME, DEFAULT_VEHICLE_NAME)

    _LOGGER.info("Setting up Tesla Fleet Telemetry Local integration")
    _LOGGER.debug(
        "Configuration: topic_base=%s, vin=%s",
        topic_base,
        vehicle_vin[:8] + "***",  # Log partial VIN for privacy
    )

    # Create device info for all entities
    device_info = DeviceInfo(
        identifiers={(DOMAIN, vehicle_vin)},
        name=vehicle_name,
        manufacturer="Tesla",
        model="Vehicle",
        serial_number=vehicle_vin,
    )

    # Initialize MQTT client
    mqtt_client = TeslaMQTTClient(
        hass=hass,
        topic_base=topic_base,
        vehicle_vin=vehicle_vin,
    )

    # Store runtime data
    entry.runtime_data = TeslaTelemetryData(
        mqtt_client=mqtt_client,
        vehicle_vin=vehicle_vin,
        vehicle_name=vehicle_name,
        device_info=device_info,
    )

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Start MQTT subscriptions after platforms are loaded
    try:
        await mqtt_client.start()
    except Exception as err:
        _LOGGER.error("Failed to start MQTT client: %s", err)
        # Don't fail setup - MQTT might become available later

    # Register update listener for options
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    _LOGGER.info("Tesla Fleet Telemetry Local integration loaded successfully")
    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Stop MQTT client
    if entry.runtime_data and entry.runtime_data.mqtt_client:
        await entry.runtime_data.mqtt_client.stop()

    # Unload platforms
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle removal of an entry."""
    # Clean up any resources
    if entry.runtime_data and entry.runtime_data.mqtt_client:
        await entry.runtime_data.mqtt_client.stop()
