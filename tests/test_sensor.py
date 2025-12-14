"""Tests for Tesla sensor entities."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

# Import the module to test
import sys
sys.path.insert(0, 'custom_components/tesla_telemetry_local')

from custom_components.tesla_telemetry_local.sensor import (
    SENSOR_DEFINITIONS,
    TeslaSensor,
)


class TestSensorDefinitions:
    """Test sensor definitions."""

    def test_sensor_definitions_count(self):
        """Test that we have the expected number of sensors."""
        assert len(SENSOR_DEFINITIONS) == 14

    def test_sensor_definitions_structure(self):
        """Test that each sensor definition has the correct structure."""
        for sensor_def in SENSOR_DEFINITIONS:
            assert len(sensor_def) == 7
            key, name, field, unit, device_class, icon, state_class = sensor_def
            assert isinstance(key, str)
            assert isinstance(name, str)
            assert isinstance(field, str)

    def test_required_sensors_exist(self):
        """Test that all required sensors are defined."""
        required_keys = [
            "speed", "shift_state", "battery", "range",
            "charging_state", "charger_voltage", "charger_current", "odometer",
            "inside_temp", "outside_temp",
            "tpms_front_left", "tpms_front_right", "tpms_rear_left", "tpms_rear_right",
        ]
        defined_keys = [s[0] for s in SENSOR_DEFINITIONS]
        for key in required_keys:
            assert key in defined_keys, f"Missing sensor: {key}"


class TestTeslaSensor:
    """Test TeslaSensor entity."""

    def test_sensor_initialization(self):
        """Test sensor initialization."""
        device_info = {
            "identifiers": {("tesla_telemetry_local", "TEST_VIN")},
            "name": "Test Tesla",
            "manufacturer": "Tesla",
        }

        sensor = TeslaSensor(
            vehicle_name="Test Tesla",
            vehicle_vin="TEST_VIN",
            device_info=device_info,
            sensor_key="battery",
            sensor_name="Battery",
            field_name="Soc",
            unit="%",
            device_class=None,
            icon=None,
            state_class=None,
        )

        assert sensor._attr_unique_id == "TEST_VIN_battery"
        assert sensor._attr_name == "Battery"
        assert sensor.field_name == "Soc"

    def test_sensor_update_battery(self):
        """Test battery sensor update."""
        device_info = {"identifiers": {("tesla_telemetry_local", "TEST_VIN")}}

        sensor = TeslaSensor(
            vehicle_name="Test",
            vehicle_vin="TEST_VIN",
            device_info=device_info,
            sensor_key="battery",
            sensor_name="Battery",
            field_name="Soc",
            unit="%",
            device_class=None,
            icon=None,
            state_class=None,
        )

        # Mock async_write_ha_state
        sensor.async_write_ha_state = MagicMock()

        sensor.update_value(78.5, {"timestamp": "2024-01-15T10:30:00Z"})

        assert sensor.native_value == 78.5
        sensor.async_write_ha_state.assert_called_once()

    def test_sensor_update_speed(self):
        """Test speed sensor update."""
        device_info = {"identifiers": {("tesla_telemetry_local", "TEST_VIN")}}

        sensor = TeslaSensor(
            vehicle_name="Test",
            vehicle_vin="TEST_VIN",
            device_info=device_info,
            sensor_key="speed",
            sensor_name="Speed",
            field_name="VehicleSpeed",
            unit="km/h",
            device_class=None,
            icon="mdi:speedometer",
            state_class=None,
        )

        sensor.async_write_ha_state = MagicMock()
        sensor.update_value(120.7, {"timestamp": "2024-01-15T10:30:00Z"})

        assert sensor.native_value == 120.7

    def test_sensor_update_gear(self):
        """Test gear/shift state sensor update."""
        device_info = {"identifiers": {("tesla_telemetry_local", "TEST_VIN")}}

        sensor = TeslaSensor(
            vehicle_name="Test",
            vehicle_vin="TEST_VIN",
            device_info=device_info,
            sensor_key="shift_state",
            sensor_name="Shift State",
            field_name="Gear",
            unit=None,
            device_class=None,
            icon="mdi:car-shift-pattern",
            state_class=None,
        )

        sensor.async_write_ha_state = MagicMock()
        sensor.update_value("d", {"timestamp": "2024-01-15T10:30:00Z"})

        assert sensor.native_value == "D"

    def test_sensor_update_temperature(self):
        """Test temperature sensor update."""
        device_info = {"identifiers": {("tesla_telemetry_local", "TEST_VIN")}}

        sensor = TeslaSensor(
            vehicle_name="Test",
            vehicle_vin="TEST_VIN",
            device_info=device_info,
            sensor_key="inside_temp",
            sensor_name="Inside Temperature",
            field_name="InsideTemp",
            unit="°C",
            device_class=None,
            icon="mdi:thermometer",
            state_class=None,
        )

        sensor.async_write_ha_state = MagicMock()
        sensor.update_value(22.5, {"timestamp": "2024-01-15T10:30:00Z"})

        assert sensor.native_value == 22.5

    def test_sensor_update_tpms(self):
        """Test TPMS pressure sensor update."""
        device_info = {"identifiers": {("tesla_telemetry_local", "TEST_VIN")}}

        sensor = TeslaSensor(
            vehicle_name="Test",
            vehicle_vin="TEST_VIN",
            device_info=device_info,
            sensor_key="tpms_front_left",
            sensor_name="Tire Pressure Front Left",
            field_name="TpmsPressureFl",
            unit="bar",
            device_class=None,
            icon="mdi:car-tire-alert",
            state_class=None,
        )

        sensor.async_write_ha_state = MagicMock()
        sensor.update_value(2.85, {"timestamp": "2024-01-15T10:30:00Z"})

        assert sensor.native_value == 2.85

    def test_sensor_extra_attributes(self):
        """Test sensor extra state attributes."""
        device_info = {"identifiers": {("tesla_telemetry_local", "TEST_VIN")}}

        sensor = TeslaSensor(
            vehicle_name="Test",
            vehicle_vin="TEST_VIN",
            device_info=device_info,
            sensor_key="battery",
            sensor_name="Battery",
            field_name="Soc",
            unit="%",
            device_class=None,
            icon=None,
            state_class=None,
        )

        sensor.async_write_ha_state = MagicMock()
        sensor.update_value(78.5, {"timestamp": "2024-01-15T10:30:00Z"})

        attrs = sensor.extra_state_attributes
        assert "last_updated" in attrs
        assert attrs["last_updated"] == "2024-01-15T10:30:00Z"
