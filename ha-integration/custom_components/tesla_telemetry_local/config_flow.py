"""Config flow for Tesla Fleet Telemetry Local integration."""
from __future__ import annotations

import logging
import re
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_MQTT_TOPIC_BASE,
    CONF_VEHICLE_NAME,
    CONF_VEHICLE_VIN,
    DEFAULT_MQTT_TOPIC_BASE,
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
        """Handle the initial step - MQTT configuration."""
        self._errors = {}

        # Check if MQTT is configured
        mqtt_entries = [
            entry for entry in self.hass.config_entries.async_entries()
            if entry.domain == "mqtt"
        ]
        if not mqtt_entries:
            return self.async_abort(reason="mqtt_not_configured")

        if user_input is not None:
            topic_base = user_input.get(
                CONF_MQTT_TOPIC_BASE, DEFAULT_MQTT_TOPIC_BASE
            ).strip().rstrip("/")

            self._data[CONF_MQTT_TOPIC_BASE] = topic_base
            return await self.async_step_vehicle()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_MQTT_TOPIC_BASE, default=DEFAULT_MQTT_TOPIC_BASE
                    ): str,
                }
            ),
            errors=self._errors,
            description_placeholders={
                "default_topic": DEFAULT_MQTT_TOPIC_BASE,
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
                "topic_base": self._data.get(CONF_MQTT_TOPIC_BASE, DEFAULT_MQTT_TOPIC_BASE),
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
            topic_base = user_input.get(
                CONF_MQTT_TOPIC_BASE, DEFAULT_MQTT_TOPIC_BASE
            ).strip().rstrip("/")

            # Update the config entry
            new_data = {
                **self._config_entry.data,
                CONF_MQTT_TOPIC_BASE: topic_base,
                CONF_VEHICLE_NAME: user_input.get(
                    CONF_VEHICLE_NAME, DEFAULT_VEHICLE_NAME
                ).strip(),
            }
            self.hass.config_entries.async_update_entry(
                self._config_entry, data=new_data
            )
            return self.async_create_entry(title="", data={})

        current_topic = self._config_entry.data.get(
            CONF_MQTT_TOPIC_BASE, DEFAULT_MQTT_TOPIC_BASE
        )
        current_name = self._config_entry.data.get(
            CONF_VEHICLE_NAME, DEFAULT_VEHICLE_NAME
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_MQTT_TOPIC_BASE, default=current_topic): str,
                    vol.Optional(CONF_VEHICLE_NAME, default=current_name): str,
                }
            ),
            errors=errors,
        )
