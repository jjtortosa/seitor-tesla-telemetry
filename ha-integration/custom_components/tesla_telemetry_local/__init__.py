"""
Tesla Fleet Telemetry Local Integration for Home Assistant.

This integration connects to a self-hosted Tesla Fleet Telemetry server
via Kafka message queue and creates real-time entities for vehicle data.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.device_registry import DeviceInfo

from .const import (
    CONF_KAFKA_BROKER,
    CONF_KAFKA_TOPIC,
    CONF_VEHICLE_NAME,
    CONF_VEHICLE_VIN,
    DEFAULT_KAFKA_TOPIC,
    DEFAULT_VEHICLE_NAME,
    DOMAIN,
    PLATFORMS,
)
from .kafka_consumer import TeslaKafkaConsumer

_LOGGER = logging.getLogger(__name__)

type TeslaTelemetryConfigEntry = ConfigEntry[TeslaTelemetryData]


class TeslaTelemetryData:
    """Runtime data for Tesla Telemetry integration."""

    def __init__(
        self,
        consumer: TeslaKafkaConsumer,
        vehicle_vin: str,
        vehicle_name: str,
        device_info: DeviceInfo,
    ) -> None:
        """Initialize runtime data."""
        self.consumer = consumer
        self.vehicle_vin = vehicle_vin
        self.vehicle_name = vehicle_name
        self.device_info = device_info
        self.entities: dict[str, Any] = {}


async def async_setup_entry(hass: HomeAssistant, entry: TeslaTelemetryConfigEntry) -> bool:
    """Set up Tesla Telemetry Local from a config entry."""
    broker = entry.data[CONF_KAFKA_BROKER]
    topic = entry.data.get(CONF_KAFKA_TOPIC, DEFAULT_KAFKA_TOPIC)
    vehicle_vin = entry.data[CONF_VEHICLE_VIN]
    vehicle_name = entry.data.get(CONF_VEHICLE_NAME, DEFAULT_VEHICLE_NAME)

    _LOGGER.info("Setting up Tesla Fleet Telemetry Local integration")
    _LOGGER.debug(
        "Configuration: broker=%s, topic=%s, vin=%s",
        broker,
        topic,
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

    # Initialize Kafka consumer
    consumer = TeslaKafkaConsumer(
        broker=broker,
        topic=topic,
        vehicle_vin=vehicle_vin,
        hass=hass,
    )

    # Store runtime data
    entry.runtime_data = TeslaTelemetryData(
        consumer=consumer,
        vehicle_vin=vehicle_vin,
        vehicle_name=vehicle_name,
        device_info=device_info,
    )

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Start consumer after platforms are loaded (with delay for callbacks to register)
    async def delayed_start() -> None:
        await asyncio.sleep(5)  # Wait for entities to register callbacks
        _LOGGER.info("Starting Kafka consumer after platform load delay")
        try:
            await consumer.start()
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Failed to start Kafka consumer: %s", err)

    entry.async_create_background_task(hass, delayed_start(), "kafka_consumer_start")

    # Register update listener for options
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    _LOGGER.info("Tesla Fleet Telemetry Local integration loaded successfully")
    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: TeslaTelemetryConfigEntry) -> bool:
    """Unload a config entry."""
    # Stop Kafka consumer
    if entry.runtime_data and entry.runtime_data.consumer:
        await entry.runtime_data.consumer.stop()

    # Unload platforms
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: TeslaTelemetryConfigEntry) -> None:
    """Handle removal of an entry."""
    # Clean up any resources
    if entry.runtime_data and entry.runtime_data.consumer:
        await entry.runtime_data.consumer.stop()
