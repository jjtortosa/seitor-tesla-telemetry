"""Config flow for Tesla Fleet Telemetry Local integration."""
from __future__ import annotations

import asyncio
import logging
import re
import socket
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_KAFKA_BROKER,
    CONF_KAFKA_TOPIC,
    CONF_VEHICLE_NAME,
    CONF_VEHICLE_VIN,
    DEFAULT_KAFKA_PORT,
    DEFAULT_KAFKA_TOPIC,
    DEFAULT_VEHICLE_NAME,
    DOMAIN,
    VIN_LENGTH,
)

_LOGGER = logging.getLogger(__name__)

# VIN validation regex (basic validation)
VIN_REGEX = re.compile(r"^[A-HJ-NPR-Z0-9]{17}$")


def validate_vin(vin: str) -> str | None:
    """Validate VIN format. Returns error key or None if valid."""
    if not vin:
        return "vin_required"
    vin = vin.upper().strip()
    if len(vin) != VIN_LENGTH:
        return "vin_invalid_length"
    if not VIN_REGEX.match(vin):
        return "vin_invalid_format"
    return None


async def test_kafka_connection(broker: str, timeout: float = 5.0) -> str | None:
    """Test connection to Kafka broker. Returns error key or None if successful."""
    try:
        # Parse broker address
        if ":" in broker:
            host, port_str = broker.rsplit(":", 1)
            try:
                port = int(port_str)
            except ValueError:
                return "broker_invalid_port"
        else:
            host = broker
            port = DEFAULT_KAFKA_PORT

        # Test TCP connection
        loop = asyncio.get_event_loop()
        try:
            await asyncio.wait_for(
                loop.run_in_executor(
                    None, lambda: socket.create_connection((host, port), timeout=timeout)
                ),
                timeout=timeout + 1,
            )
            return None  # Connection successful
        except (socket.timeout, socket.error, OSError) as err:
            _LOGGER.debug("Kafka connection test failed: %s", err)
            return "broker_connection_failed"
        except asyncio.TimeoutError:
            return "broker_timeout"

    except Exception as err:  # noqa: BLE001
        _LOGGER.exception("Unexpected error testing Kafka connection: %s", err)
        return "broker_connection_failed"


class TeslaTelemetryConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tesla Fleet Telemetry Local."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data: dict[str, Any] = {}
        self._errors: dict[str, str] = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler."""
        return TeslaTelemetryOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - Kafka broker configuration."""
        self._errors = {}

        if user_input is not None:
            broker = user_input[CONF_KAFKA_BROKER].strip()

            # Test Kafka connection
            error = await test_kafka_connection(broker)
            if error:
                self._errors["base"] = error
            else:
                self._data[CONF_KAFKA_BROKER] = broker
                self._data[CONF_KAFKA_TOPIC] = user_input.get(
                    CONF_KAFKA_TOPIC, DEFAULT_KAFKA_TOPIC
                ).strip()
                return await self.async_step_vehicle()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_KAFKA_BROKER): str,
                    vol.Optional(CONF_KAFKA_TOPIC, default=DEFAULT_KAFKA_TOPIC): str,
                }
            ),
            errors=self._errors,
            description_placeholders={
                "default_topic": DEFAULT_KAFKA_TOPIC,
            },
        )

    async def async_step_vehicle(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the vehicle configuration step."""
        self._errors = {}

        if user_input is not None:
            vin = user_input[CONF_VEHICLE_VIN].upper().strip()

            # Validate VIN
            error = validate_vin(vin)
            if error:
                self._errors["base"] = error
            else:
                # Check if this VIN is already configured
                await self.async_set_unique_id(vin)
                self._abort_if_unique_id_configured()

                self._data[CONF_VEHICLE_VIN] = vin
                self._data[CONF_VEHICLE_NAME] = user_input.get(
                    CONF_VEHICLE_NAME, DEFAULT_VEHICLE_NAME
                ).strip()

                return self.async_create_entry(
                    title=f"{self._data[CONF_VEHICLE_NAME]} ({vin[:8]}...)",
                    data=self._data,
                )

        return self.async_show_form(
            step_id="vehicle",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_VEHICLE_VIN): str,
                    vol.Optional(CONF_VEHICLE_NAME, default=DEFAULT_VEHICLE_NAME): str,
                }
            ),
            errors=self._errors,
            description_placeholders={
                "broker": self._data.get(CONF_KAFKA_BROKER, ""),
            },
        )


class TeslaTelemetryOptionsFlow(OptionsFlow):
    """Handle options flow for Tesla Fleet Telemetry Local."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            broker = user_input[CONF_KAFKA_BROKER].strip()

            # Test Kafka connection if broker changed
            if broker != self._config_entry.data.get(CONF_KAFKA_BROKER):
                error = await test_kafka_connection(broker)
                if error:
                    errors["base"] = error

            if not errors:
                # Update the config entry
                new_data = {
                    **self._config_entry.data,
                    CONF_KAFKA_BROKER: broker,
                    CONF_KAFKA_TOPIC: user_input.get(
                        CONF_KAFKA_TOPIC, DEFAULT_KAFKA_TOPIC
                    ).strip(),
                    CONF_VEHICLE_NAME: user_input.get(
                        CONF_VEHICLE_NAME, DEFAULT_VEHICLE_NAME
                    ).strip(),
                }
                self.hass.config_entries.async_update_entry(
                    self._config_entry, data=new_data
                )
                return self.async_create_entry(title="", data={})

        current_broker = self._config_entry.data.get(CONF_KAFKA_BROKER, "")
        current_topic = self._config_entry.data.get(CONF_KAFKA_TOPIC, DEFAULT_KAFKA_TOPIC)
        current_name = self._config_entry.data.get(CONF_VEHICLE_NAME, DEFAULT_VEHICLE_NAME)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_KAFKA_BROKER, default=current_broker): str,
                    vol.Optional(CONF_KAFKA_TOPIC, default=current_topic): str,
                    vol.Optional(CONF_VEHICLE_NAME, default=current_name): str,
                }
            ),
            errors=errors,
        )
