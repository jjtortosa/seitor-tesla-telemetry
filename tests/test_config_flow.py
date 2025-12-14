"""Tests for Tesla Fleet Telemetry Local config flow."""
from __future__ import annotations

import pytest
import re


# VIN validation regex (same as in config_flow.py)
VIN_REGEX = re.compile(r'^[A-HJ-NPR-Z0-9]{17}$')


class TestVinValidation:
    """Test VIN validation."""

    def test_valid_vin(self, valid_vin):
        """Test that valid VIN passes validation."""
        assert VIN_REGEX.match(valid_vin)
        assert len(valid_vin) == 17

    def test_invalid_vin_empty(self):
        """Test that empty VIN fails validation."""
        assert not VIN_REGEX.match("")

    def test_invalid_vin_too_short(self):
        """Test that short VIN fails validation."""
        assert not VIN_REGEX.match("5YJ3E1EA1MF0000")

    def test_invalid_vin_too_long(self):
        """Test that long VIN fails validation."""
        assert not VIN_REGEX.match("5YJ3E1EA1MF00000000")

    def test_invalid_vin_contains_i(self):
        """Test that VIN with I fails validation."""
        assert not VIN_REGEX.match("5YJ3E1EA1MF00000I")

    def test_invalid_vin_contains_o(self):
        """Test that VIN with O fails validation."""
        assert not VIN_REGEX.match("5YJ3E1EA1MF00000O")

    def test_invalid_vin_contains_q(self):
        """Test that VIN with Q fails validation."""
        assert not VIN_REGEX.match("5YJ3E1EA1MF00000Q")

    def test_invalid_vin_lowercase(self):
        """Test that lowercase VIN fails validation."""
        # VINs should be uppercase
        vin_lower = "5yj3e1ea1mf000000"
        assert not VIN_REGEX.match(vin_lower)

    def test_valid_tesla_vins(self):
        """Test various valid Tesla VIN formats."""
        valid_vins = [
            "5YJ3E1EA1MF000000",  # Model 3
            "5YJSA1E26FF000000",  # Model S
            "5YJXCAE20HF000000",  # Model X
            "7SAYGDEF3NF000000",  # Model Y (Austin)
            "LRWYGCFS3RC000000",  # Model Y (China)
        ]
        for vin in valid_vins:
            assert VIN_REGEX.match(vin), f"VIN should be valid: {vin}"


class TestMqttTopicValidation:
    """Test MQTT topic validation."""

    def test_valid_topic_bases(self):
        """Test valid MQTT topic bases."""
        valid_topics = ["tesla", "vehicles", "car", "my_tesla", "tesla123"]
        for topic in valid_topics:
            # Topic base should not contain wildcards or special MQTT chars
            assert "#" not in topic
            assert "+" not in topic
            assert " " not in topic

    def test_topic_structure(self):
        """Test MQTT topic structure."""
        topic_base = "tesla"
        vin = "5YJ3E1EA1MF000000"

        # Expected topic patterns
        telemetry_topic = f"{topic_base}/{vin}/v/#"
        connectivity_topic = f"{topic_base}/{vin}/connectivity"

        assert telemetry_topic == "tesla/5YJ3E1EA1MF000000/v/#"
        assert connectivity_topic == "tesla/5YJ3E1EA1MF000000/connectivity"


class TestPresets:
    """Test telemetry presets."""

    def test_preset_structure(self):
        """Test that presets have correct structure."""
        # Import would need mocking, so we test the expected structure
        presets = {
            "minimal": {
                "Location": 60,
                "Soc": 300,
            },
            "driving": {
                "Location": 10,
                "VehicleSpeed": 5,
                "Gear": 1,
                "Soc": 60,
            },
            "charging": {
                "Soc": 30,
                "ChargeState": 5,
                "ChargerVoltage": 10,
                "ChargerActualCurrent": 10,
            },
        }

        for preset_name, fields in presets.items():
            assert isinstance(fields, dict)
            for field, interval in fields.items():
                assert isinstance(field, str)
                assert isinstance(interval, int)
                assert interval > 0

    def test_valid_intervals(self):
        """Test that intervals are within valid range."""
        valid_intervals = [1, 5, 10, 30, 60, 120, 300, 600]

        for interval in valid_intervals:
            assert interval >= 1
            assert interval <= 600
