"""Config flow for Tesla Fleet Telemetry Local integration."""
from __future__ import annotations

import logging
import re
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    SelectOptionDict,
)

from .const import (
    CONF_MQTT_TOPIC_BASE,
    CONF_PROXY_URL,
    CONF_TELEMETRY_CONFIG,
    CONF_TELEMETRY_PRESET,
    CONF_TESLA_TOKEN,
    CONF_VEHICLE_NAME,
    CONF_VEHICLE_VIN,
    DEFAULT_MQTT_TOPIC_BASE,
    DEFAULT_PROXY_URL,
    DEFAULT_VEHICLE_NAME,
    DOMAIN,
    TELEMETRY_FIELD_CATEGORIES,
    TELEMETRY_FIELD_DESCRIPTIONS,
    TELEMETRY_PRESETS,
    VALID_INTERVALS,
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
        self._data: dict[str, Any] = {}
        self._errors: dict[str, str] = {}
        self._tesla_client = None

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Initial step - basic settings and telemetry mode selection."""
        self._errors = {}

        if user_input is not None:
            # Store basic settings
            self._data[CONF_MQTT_TOPIC_BASE] = user_input.get(
                CONF_MQTT_TOPIC_BASE, DEFAULT_MQTT_TOPIC_BASE
            ).strip().rstrip("/")
            self._data[CONF_VEHICLE_NAME] = user_input.get(
                CONF_VEHICLE_NAME, DEFAULT_VEHICLE_NAME
            ).strip()

            # Check if user wants to configure telemetry
            if user_input.get("configure_telemetry", False):
                return await self.async_step_tesla_api()
            else:
                # Just update basic settings
                return await self._async_save_config()

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
                    vol.Optional("configure_telemetry", default=False): bool,
                }
            ),
            errors=self._errors,
            description_placeholders={
                "vehicle_vin": self._config_entry.data.get(CONF_VEHICLE_VIN, ""),
            },
        )

    async def async_step_tesla_api(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure Tesla API connection (proxy URL and token)."""
        self._errors = {}

        # If already configured, try to use existing config and skip to presets
        if user_input is None:
            saved_proxy = self._config_entry.options.get(CONF_PROXY_URL)
            saved_token = self._config_entry.options.get(CONF_TESLA_TOKEN)
            if saved_proxy and saved_token:
                # Test if existing config still works
                try:
                    from .tesla_api import TeslaAPIClient
                    vin = self._config_entry.data.get(CONF_VEHICLE_VIN)
                    client = TeslaAPIClient(
                        proxy_url=saved_proxy,
                        token=saved_token,
                        vin=vin,
                        hostname="",
                    )
                    result = await client.test_connection()
                    await client.close()
                    if result.get("success"):
                        # Existing config works, skip to presets
                        self._data[CONF_PROXY_URL] = saved_proxy
                        self._data[CONF_TESLA_TOKEN] = saved_token
                        return await self.async_step_preset_select()
                except Exception:
                    pass  # Config doesn't work, show form

        if user_input is not None:
            proxy_url = user_input.get(CONF_PROXY_URL, DEFAULT_PROXY_URL).strip()
            token = user_input.get(CONF_TESLA_TOKEN, "").strip()

            if not proxy_url:
                self._errors["base"] = "proxy_url_required"
            elif not token:
                self._errors["base"] = "token_required"
            else:
                # Test connection
                try:
                    from .tesla_api import TeslaAPIClient

                    vin = self._config_entry.data.get(CONF_VEHICLE_VIN)
                    self._tesla_client = TeslaAPIClient(
                        proxy_url=proxy_url,
                        token=token,
                        vin=vin,
                        hostname="",  # Not needed for test
                    )
                    result = await self._tesla_client.test_connection()

                    if result.get("success"):
                        self._data[CONF_PROXY_URL] = proxy_url
                        self._data[CONF_TESLA_TOKEN] = token
                        # Save proxy config immediately so it persists even if user cancels later
                        new_options = {
                            **self._config_entry.options,
                            CONF_PROXY_URL: proxy_url,
                            CONF_TESLA_TOKEN: token,
                        }
                        self.hass.config_entries.async_update_entry(
                            self._config_entry, options=new_options
                        )
                        return await self.async_step_preset_select()
                    else:
                        self._errors["base"] = "connection_failed"

                except Exception as err:
                    _LOGGER.error("Tesla API connection test failed: %s", err)
                    self._errors["base"] = "connection_failed"
                finally:
                    if self._tesla_client:
                        await self._tesla_client.close()
                        self._tesla_client = None

        # Try to auto-detect proxy URL from HA internal URL
        current_proxy = self._config_entry.options.get(CONF_PROXY_URL, "")
        if not current_proxy:
            # Try to get HA's internal URL and replace port with 4443
            try:
                internal_url = self.hass.config.internal_url
                if internal_url:
                    from urllib.parse import urlparse
                    parsed = urlparse(internal_url)
                    current_proxy = f"https://{parsed.hostname}:4443"
                else:
                    current_proxy = DEFAULT_PROXY_URL
            except Exception:
                current_proxy = DEFAULT_PROXY_URL

        # Try to auto-detect token from tesla_fleet integration
        current_token = self._config_entry.options.get(CONF_TESLA_TOKEN, "")

        if not current_token:
            try:
                from .tesla_api import get_tesla_token_from_fleet_integration
                detected_token = await get_tesla_token_from_fleet_integration(self.hass)
                if detected_token:
                    current_token = detected_token
            except Exception as err:
                _LOGGER.debug("Failed to auto-detect Tesla token: %s", err)

        return self.async_show_form(
            step_id="tesla_api",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PROXY_URL, default=current_proxy): str,
                    vol.Required(CONF_TESLA_TOKEN, default=current_token): str,
                }
            ),
            errors=self._errors,
            description_placeholders={
                "default_proxy": DEFAULT_PROXY_URL,
            },
        )

    async def async_step_preset_select(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select a telemetry preset or custom configuration."""
        self._errors = {}

        if user_input is not None:
            preset = user_input.get(CONF_TELEMETRY_PRESET, "complete")
            self._data[CONF_TELEMETRY_PRESET] = preset

            if preset == "custom":
                return await self.async_step_custom_fields()
            else:
                # Apply preset directly
                return await self._async_apply_and_save(preset)

        # Build preset options with translations
        preset_options = [
            SelectOptionDict(
                value=key,
                label=f"{info['name']} - {info['description']}",
            )
            for key, info in TELEMETRY_PRESETS.items()
        ]

        current_preset = self._config_entry.options.get(CONF_TELEMETRY_PRESET, "complete")

        return self.async_show_form(
            step_id="preset_select",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_TELEMETRY_PRESET, default=current_preset): SelectSelector(
                        SelectSelectorConfig(
                            options=preset_options,
                            mode=SelectSelectorMode.LIST,
                            translation_key="preset_options",
                        )
                    ),
                }
            ),
            errors=self._errors,
        )

    async def async_step_custom_fields(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure individual field intervals."""
        self._errors = {}

        if user_input is not None:
            # Build custom config from user input
            custom_fields = {}
            for field_name in TELEMETRY_FIELD_DESCRIPTIONS:
                interval_key = f"interval_{field_name}"
                if interval_key in user_input:
                    interval_val = int(user_input[interval_key])
                    if interval_val > 0:
                        custom_fields[field_name] = {
                            "interval_seconds": interval_val
                        }

            if not custom_fields:
                self._errors["base"] = "no_fields_selected"
            else:
                self._data[CONF_TELEMETRY_CONFIG] = custom_fields
                return await self._async_apply_and_save("custom", custom_fields)

        # Build schema with all fields grouped by category
        schema_dict = {}
        current_config = self._config_entry.options.get(CONF_TELEMETRY_CONFIG, {})

        # Get current config from Tesla if available
        if not current_config:
            try:
                from .tesla_api import TeslaAPIClient

                vin = self._config_entry.data.get(CONF_VEHICLE_VIN)
                proxy_url = self._data.get(CONF_PROXY_URL, DEFAULT_PROXY_URL)
                token = self._data.get(CONF_TESLA_TOKEN, "")

                if proxy_url and token:
                    client = TeslaAPIClient(
                        proxy_url=proxy_url,
                        token=token,
                        vin=vin,
                        hostname="",
                    )
                    try:
                        result = await client.get_telemetry_config()
                        if result and result.get("config"):
                            current_config = result["config"].get("fields", {})
                    finally:
                        await client.close()
            except Exception as err:
                _LOGGER.debug("Failed to get current config: %s", err)

        # Create interval selector options
        interval_options = [
            SelectOptionDict(value="0", label="Desactivat"),
        ] + [
            SelectOptionDict(value=str(i), label=f"{i} segons")
            for i in VALID_INTERVALS
        ]

        for field_name, description in TELEMETRY_FIELD_DESCRIPTIONS.items():
            current_interval = "0"
            if field_name in current_config:
                interval_val = current_config[field_name].get("interval_seconds", 0)
                # Find closest valid interval
                if interval_val not in VALID_INTERVALS and interval_val != 0:
                    interval_val = min(VALID_INTERVALS, key=lambda x: abs(x - interval_val))
                current_interval = str(interval_val)

            schema_dict[
                vol.Optional(f"interval_{field_name}", default=current_interval)
            ] = SelectSelector(
                SelectSelectorConfig(
                    options=interval_options,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            )

        return self.async_show_form(
            step_id="custom_fields",
            data_schema=vol.Schema(schema_dict),
            errors=self._errors,
            description_placeholders={
                "field_descriptions": "\n".join(
                    f"- {field}: {desc}"
                    for field, desc in TELEMETRY_FIELD_DESCRIPTIONS.items()
                ),
            },
        )

    async def _async_apply_and_save(
        self, preset: str, custom_fields: dict | None = None
    ) -> FlowResult:
        """Apply telemetry config to Tesla and save to HA."""
        try:
            from .tesla_api import (
                TeslaAPIClient,
                get_ca_certificate_from_current_config,
            )

            vin = self._config_entry.data.get(CONF_VEHICLE_VIN)
            proxy_url = self._data.get(CONF_PROXY_URL, DEFAULT_PROXY_URL)
            token = self._data.get(CONF_TESLA_TOKEN, "")

            # Get CA certificate from current config
            ca_cert = await get_ca_certificate_from_current_config(
                proxy_url, token, vin
            )

            # Get hostname from current config
            hostname = "tesla-telemetry.seitor.com"  # Default
            try:
                temp_client = TeslaAPIClient(proxy_url, token, vin, "")
                current = await temp_client.get_telemetry_config()
                if current and current.get("config"):
                    hostname = current["config"].get("hostname", hostname)
                await temp_client.close()
            except Exception:
                pass

            # Create client and apply config
            client = TeslaAPIClient(
                proxy_url=proxy_url,
                token=token,
                vin=vin,
                hostname=hostname,
                ca_certificate=ca_cert,
            )

            try:
                if preset == "custom" and custom_fields:
                    result = await client.set_telemetry_config(custom_fields)
                else:
                    result = await client.apply_preset(preset)

                if result:
                    _LOGGER.info(
                        "Telemetry config applied: preset=%s, synced=%s",
                        preset,
                        result.get("synced", False),
                    )
                    self._data[CONF_TELEMETRY_PRESET] = preset
                    if custom_fields:
                        self._data[CONF_TELEMETRY_CONFIG] = custom_fields
                    return await self._async_save_config()
                else:
                    self._errors["base"] = "apply_failed"
                    return await self.async_step_preset_select()

            finally:
                await client.close()

        except Exception as err:
            _LOGGER.error("Failed to apply telemetry config: %s", err)
            self._errors["base"] = "apply_failed"
            return await self.async_step_preset_select()

    async def _async_save_config(self) -> FlowResult:
        """Save configuration to config entry."""
        # Update config entry data
        new_data = {
            **self._config_entry.data,
            CONF_MQTT_TOPIC_BASE: self._data.get(
                CONF_MQTT_TOPIC_BASE,
                self._config_entry.data.get(CONF_MQTT_TOPIC_BASE, DEFAULT_MQTT_TOPIC_BASE),
            ),
            CONF_VEHICLE_NAME: self._data.get(
                CONF_VEHICLE_NAME,
                self._config_entry.data.get(CONF_VEHICLE_NAME, DEFAULT_VEHICLE_NAME),
            ),
        }

        # Update options
        new_options = {
            **self._config_entry.options,
        }

        # Add Tesla API config if configured
        if CONF_PROXY_URL in self._data:
            new_options[CONF_PROXY_URL] = self._data[CONF_PROXY_URL]
        if CONF_TESLA_TOKEN in self._data:
            new_options[CONF_TESLA_TOKEN] = self._data[CONF_TESLA_TOKEN]
        if CONF_TELEMETRY_PRESET in self._data:
            new_options[CONF_TELEMETRY_PRESET] = self._data[CONF_TELEMETRY_PRESET]
        if CONF_TELEMETRY_CONFIG in self._data:
            new_options[CONF_TELEMETRY_CONFIG] = self._data[CONF_TELEMETRY_CONFIG]

        # Update data (VIN, name, etc.) directly - options will be set by create_entry
        self.hass.config_entries.async_update_entry(
            self._config_entry,
            data=new_data,
        )

        # In OptionsFlow, data passed to create_entry becomes the new options
        return self.async_create_entry(title="", data=new_options)
