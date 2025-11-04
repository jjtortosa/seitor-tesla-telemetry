"""
Tesla Fleet Telemetry Local Integration for Home Assistant.

This integration connects to a self-hosted Tesla Fleet Telemetry server
via Kafka message queue and creates real-time entities for vehicle data.
"""
import asyncio
import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, Platform
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .kafka_consumer import TeslaKafkaConsumer

_LOGGER = logging.getLogger(__name__)

DOMAIN = "tesla_telemetry_local"

# Configuration keys
CONF_KAFKA_BROKER = "kafka_broker"
CONF_KAFKA_TOPIC = "kafka_topic"
CONF_VEHICLE_VIN = "vehicle_vin"
CONF_VEHICLE_NAME = "vehicle_name"

# Default values
DEFAULT_KAFKA_TOPIC = "tesla_telemetry"
DEFAULT_VEHICLE_NAME = "Tesla"

# Platforms supported by this integration
PLATFORMS = [Platform.DEVICE_TRACKER, Platform.SENSOR, Platform.BINARY_SENSOR]

# Configuration schema
CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_KAFKA_BROKER): cv.string,
                vol.Optional(CONF_KAFKA_TOPIC, default=DEFAULT_KAFKA_TOPIC): cv.string,
                vol.Required(CONF_VEHICLE_VIN): cv.string,
                vol.Optional(CONF_VEHICLE_NAME, default=DEFAULT_VEHICLE_NAME): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Tesla Telemetry Local integration."""
    if DOMAIN not in config:
        return True

    conf = config[DOMAIN]

    _LOGGER.info("Setting up Tesla Fleet Telemetry Local integration")
    _LOGGER.debug("Configuration: broker=%s, topic=%s, vin=%s",
                  conf[CONF_KAFKA_BROKER],
                  conf[CONF_KAFKA_TOPIC],
                  conf[CONF_VEHICLE_VIN][:8] + "***")  # Log partial VIN for privacy

    # Store configuration in hass.data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["config"] = conf
    hass.data[DOMAIN]["entities"] = {}

    # Initialize Kafka consumer
    consumer = TeslaKafkaConsumer(
        broker=conf[CONF_KAFKA_BROKER],
        topic=conf[CONF_KAFKA_TOPIC],
        vehicle_vin=conf[CONF_VEHICLE_VIN],
        hass=hass,
    )

    hass.data[DOMAIN]["consumer"] = consumer

    # Start consumer in background
    hass.async_create_task(consumer.start())

    # Load platforms
    for platform in PLATFORMS:
        hass.async_create_task(
            hass.helpers.discovery.async_load_platform(
                platform, DOMAIN, conf, config
            )
        )

    _LOGGER.info("Tesla Fleet Telemetry Local integration loaded successfully")

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tesla Telemetry Local from a config entry."""
    # This integration currently only supports YAML configuration
    # Config flow support can be added in future versions
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Stop Kafka consumer
    if DOMAIN in hass.data and "consumer" in hass.data[DOMAIN]:
        consumer = hass.data[DOMAIN]["consumer"]
        await consumer.stop()

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle removal of an entry."""
    # Clean up any resources
    if DOMAIN in hass.data:
        if "consumer" in hass.data[DOMAIN]:
            consumer = hass.data[DOMAIN]["consumer"]
            await consumer.stop()

        hass.data.pop(DOMAIN, None)
