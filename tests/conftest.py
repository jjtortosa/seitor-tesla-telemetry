"""Pytest fixtures for Tesla Fleet Telemetry Local tests."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

# Mock Home Assistant components
@pytest.fixture
def mock_hass():
    """Return a mock Home Assistant instance."""
    hass = MagicMock()
    hass.data = {}
    hass.config_entries = MagicMock()
    return hass


@pytest.fixture
def mock_config_entry():
    """Return a mock config entry."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.data = {
        "mqtt_topic_base": "tesla",
        "vehicle_vin": "5YJ3E1EA1MF000000",
        "vehicle_name": "Test Tesla",
    }
    entry.options = {}
    return entry


@pytest.fixture
def mock_mqtt_client():
    """Return a mock MQTT client."""
    client = MagicMock()
    client.register_callback = MagicMock()
    client.subscribe = AsyncMock()
    return client


@pytest.fixture
def sample_telemetry_data():
    """Return sample telemetry data."""
    return {
        "VehicleSpeed": {"value": 65.5, "timestamp": "2024-01-15T10:30:00Z"},
        "Soc": {"value": 78.0, "timestamp": "2024-01-15T10:30:00Z"},
        "EstBatteryRange": {"value": 285.5, "timestamp": "2024-01-15T10:30:00Z"},
        "InsideTemp": {"value": 22.5, "timestamp": "2024-01-15T10:30:00Z"},
        "OutsideTemp": {"value": 15.0, "timestamp": "2024-01-15T10:30:00Z"},
        "TpmsPressureFl": {"value": 2.9, "timestamp": "2024-01-15T10:30:00Z"},
        "TpmsPressureFr": {"value": 2.9, "timestamp": "2024-01-15T10:30:00Z"},
        "TpmsPressureRl": {"value": 2.8, "timestamp": "2024-01-15T10:30:00Z"},
        "TpmsPressureRr": {"value": 2.8, "timestamp": "2024-01-15T10:30:00Z"},
        "Location": {"latitude": 41.3851, "longitude": 2.1734, "timestamp": "2024-01-15T10:30:00Z"},
        "Gear": {"value": "D", "timestamp": "2024-01-15T10:30:00Z"},
        "ChargeState": {"value": "Disconnected", "timestamp": "2024-01-15T10:30:00Z"},
    }


@pytest.fixture
def valid_vin():
    """Return a valid VIN."""
    return "5YJ3E1EA1MF000000"


@pytest.fixture
def invalid_vins():
    """Return a list of invalid VINs."""
    return [
        "",  # Empty
        "123",  # Too short
        "12345678901234567890",  # Too long
        "5YJ3E1EA1MF00000I",  # Contains I
        "5YJ3E1EA1MF00000O",  # Contains O
        "5YJ3E1EA1MF00000Q",  # Contains Q
    ]
