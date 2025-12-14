"""Tesla Fleet API client for telemetry configuration."""
from __future__ import annotations

import asyncio
import logging
import ssl
from typing import Any

import aiohttp

from .const import (
    CONF_PROXY_URL,
    CONF_TESLA_TOKEN,
    DEFAULT_PROXY_URL,
    TELEMETRY_PRESETS,
)

_LOGGER = logging.getLogger(__name__)

# Tesla Fleet API endpoints
# GET goes directly to Tesla (proxy doesn't handle GET well)
TESLA_API_BASE_URL = "https://fleet-api.prd.eu.vn.cloud.tesla.com"
ENDPOINT_GET_TELEMETRY_CONFIG = "/api/1/vehicles/{vin}/fleet_telemetry_config"
# POST goes through proxy (needs request signing)
ENDPOINT_SET_TELEMETRY_CONFIG = "/api/1/vehicles/fleet_telemetry_config"


class TeslaAPIError(Exception):
    """Base exception for Tesla API errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        """Initialize the exception."""
        super().__init__(message)
        self.status_code = status_code


class TeslaAPIConnectionError(TeslaAPIError):
    """Exception for connection errors."""


class TeslaAPIAuthError(TeslaAPIError):
    """Exception for authentication errors."""


class TeslaAPIClient:
    """Client for Tesla Fleet API via vehicle-command HTTP proxy."""

    def __init__(
        self,
        proxy_url: str,
        token: str,
        vin: str,
        hostname: str,
        ca_certificate: str | None = None,
        verify_ssl: bool = False,
    ) -> None:
        """Initialize the Tesla API client.

        Args:
            proxy_url: URL of the vehicle-command HTTP proxy
            token: Tesla OAuth access token
            vin: Vehicle Identification Number
            hostname: Fleet telemetry server hostname (e.g., tesla-telemetry.seitor.com)
            ca_certificate: CA certificate for the telemetry server (PEM format)
            verify_ssl: Whether to verify SSL certificates (False for self-signed proxy)
        """
        self._proxy_url = proxy_url.rstrip("/")
        self._token = token
        self._vin = vin
        self._hostname = hostname
        self._ca_certificate = ca_certificate
        self._verify_ssl = verify_ssl
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp session for proxy (no SSL verify)."""
        if self._session is None or self._session.closed:
            # Create SSL context that doesn't verify certificates (for self-signed proxy)
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            connector = aiohttp.TCPConnector(ssl=ssl_context)

            self._session = aiohttp.ClientSession(
                connector=connector,
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Content-Type": "application/json",
                },
            )
        return self._session

    async def _get_direct_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp session for direct Tesla API (with SSL verify)."""
        if not hasattr(self, "_direct_session") or self._direct_session is None or self._direct_session.closed:
            self._direct_session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Content-Type": "application/json",
                },
            )
        return self._direct_session

    async def close(self) -> None:
        """Close all aiohttp sessions."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
        if hasattr(self, "_direct_session") and self._direct_session and not self._direct_session.closed:
            await self._direct_session.close()
            self._direct_session = None

    async def test_connection(self) -> dict[str, Any]:
        """Test connection to the proxy and Tesla API.

        Returns:
            Dict with connection status and current config if successful

        Raises:
            TeslaAPIConnectionError: If proxy is unreachable
            TeslaAPIAuthError: If token is invalid
            TeslaAPIError: For other errors
        """
        # First test proxy is reachable
        try:
            session = await self._get_session()
            async with session.get(f"{self._proxy_url}/health") as response:
                if response.status != 200:
                    raise TeslaAPIConnectionError(
                        f"Proxy health check failed: {response.status}"
                    )
                _LOGGER.debug("Proxy health check: OK")
        except aiohttp.ClientConnectorError as err:
            raise TeslaAPIConnectionError(
                f"Cannot connect to proxy at {self._proxy_url}: {err}"
            ) from err

        # Then test Tesla API connection
        try:
            config = await self.get_telemetry_config()
            return {
                "success": True,
                "synced": config.get("synced", False),
                "key_paired": config.get("key_paired", False),
            }
        except TeslaAPIConnectionError:
            raise
        except TeslaAPIAuthError:
            raise
        except Exception as err:
            raise TeslaAPIError(f"Connection test failed: {err}") from err

    async def get_telemetry_config(self) -> dict[str, Any]:
        """Get current telemetry configuration from Tesla.

        Note: GET requests go directly to Tesla API (proxy only needed for POST).

        Returns:
            Current telemetry configuration dict

        Raises:
            TeslaAPIConnectionError: If Tesla API is unreachable
            TeslaAPIAuthError: If token is invalid
            TeslaAPIError: For other errors
        """
        session = await self._get_direct_session()
        # GET goes directly to Tesla API (proxy doesn't handle GET properly)
        url = f"{TESLA_API_BASE_URL}{ENDPOINT_GET_TELEMETRY_CONFIG.format(vin=self._vin)}"
        _LOGGER.debug("Getting telemetry config from: %s", url)

        try:
            async with session.get(url) as response:
                if response.status == 401:
                    raise TeslaAPIAuthError(
                        "Invalid or expired Tesla token", status_code=401
                    )
                if response.status == 404:
                    # No config set yet - return empty
                    return {"synced": False, "config": None}
                if response.status != 200:
                    text = await response.text()
                    raise TeslaAPIError(
                        f"Failed to get config: {text}", status_code=response.status
                    )

                data = await response.json()
                return data.get("response", {})

        except aiohttp.ClientConnectorError as err:
            raise TeslaAPIConnectionError(
                f"Cannot connect to proxy at {self._proxy_url}: {err}"
            ) from err
        except aiohttp.ClientError as err:
            raise TeslaAPIError(f"Request failed: {err}") from err

    async def set_telemetry_config(
        self, fields: dict[str, dict[str, int]]
    ) -> dict[str, Any]:
        """Set telemetry configuration on Tesla.

        Args:
            fields: Dict of field names to interval config
                    e.g., {"Location": {"interval_seconds": 10}, ...}

        Returns:
            Response from Tesla API

        Raises:
            TeslaAPIConnectionError: If proxy is unreachable
            TeslaAPIAuthError: If token is invalid
            TeslaAPIError: For other errors
        """
        session = await self._get_session()
        url = f"{self._proxy_url}{ENDPOINT_SET_TELEMETRY_CONFIG}"

        # Build the config payload
        config = {
            "hostname": self._hostname,
            "port": 443,
            "fields": fields,
            "alert_types": ["service"],
        }

        # Include CA certificate if provided
        if self._ca_certificate:
            config["ca"] = self._ca_certificate

        payload = {
            "vins": [self._vin],
            "config": config,
        }

        _LOGGER.debug("Setting telemetry config: %s fields", len(fields))

        try:
            async with session.post(url, json=payload) as response:
                if response.status == 401:
                    raise TeslaAPIAuthError(
                        "Invalid or expired Tesla token", status_code=401
                    )
                if response.status not in (200, 201):
                    text = await response.text()
                    raise TeslaAPIError(
                        f"Failed to set config: {text}", status_code=response.status
                    )

                data = await response.json()
                response_data = data.get("response", {})

                _LOGGER.info(
                    "Telemetry config updated: synced=%s",
                    response_data.get("synced", False),
                )

                return response_data

        except aiohttp.ClientConnectorError as err:
            raise TeslaAPIConnectionError(
                f"Cannot connect to proxy at {self._proxy_url}: {err}"
            ) from err
        except aiohttp.ClientError as err:
            raise TeslaAPIError(f"Request failed: {err}") from err

    async def apply_preset(self, preset_name: str) -> dict[str, Any]:
        """Apply a telemetry preset configuration.

        Args:
            preset_name: Name of the preset (minimal, driving, charging, complete)

        Returns:
            Response from Tesla API

        Raises:
            ValueError: If preset name is invalid
            TeslaAPIError: For API errors
        """
        if preset_name not in TELEMETRY_PRESETS:
            raise ValueError(f"Unknown preset: {preset_name}")

        if preset_name == "custom":
            raise ValueError("Use set_telemetry_config() for custom configuration")

        preset = TELEMETRY_PRESETS[preset_name]
        return await self.set_telemetry_config(preset["fields"])

    @staticmethod
    def get_preset_info(preset_name: str) -> dict[str, Any] | None:
        """Get information about a preset.

        Args:
            preset_name: Name of the preset

        Returns:
            Preset info dict or None if not found
        """
        return TELEMETRY_PRESETS.get(preset_name)

    @staticmethod
    def list_presets() -> list[dict[str, Any]]:
        """List all available presets.

        Returns:
            List of preset info dicts
        """
        return [
            {"id": key, **value}
            for key, value in TELEMETRY_PRESETS.items()
            if key != "custom"
        ]


async def get_tesla_token_from_fleet_integration(
    hass,
) -> str | None:
    """Try to get Tesla OAuth token from tesla_fleet integration.

    Args:
        hass: Home Assistant instance

    Returns:
        Tesla access token or None if not found
    """
    try:
        # Look for tesla_fleet integration config entries
        from homeassistant.config_entries import ConfigEntry

        for entry in hass.config_entries.async_entries("tesla_fleet"):
            if "token" in entry.data:
                token_data = entry.data["token"]
                if isinstance(token_data, dict) and "access_token" in token_data:
                    _LOGGER.debug("Found Tesla token from tesla_fleet integration")
                    return token_data["access_token"]
                elif isinstance(token_data, str):
                    return token_data

        _LOGGER.debug("No tesla_fleet integration found with valid token")
        return None

    except Exception as err:
        _LOGGER.warning("Failed to get Tesla token from tesla_fleet: %s", err)
        return None


async def get_ca_certificate_from_current_config(
    proxy_url: str, token: str, vin: str
) -> str | None:
    """Get the CA certificate from current Tesla config.

    This is needed because we must include the same CA cert when updating config.

    Args:
        proxy_url: URL of the vehicle-command proxy
        token: Tesla OAuth access token
        vin: Vehicle Identification Number

    Returns:
        CA certificate in PEM format or None
    """
    try:
        client = TeslaAPIClient(
            proxy_url=proxy_url,
            token=token,
            vin=vin,
            hostname="",  # Not needed for GET
        )
        try:
            config = await client.get_telemetry_config()
            if config and config.get("config"):
                return config["config"].get("ca")
            return None
        finally:
            await client.close()
    except Exception as err:
        _LOGGER.warning("Failed to get CA certificate: %s", err)
        return None
