"""Support for Tesla vehicle sensors."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfLength,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

# Using ConfigEntry directly
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


# Sensor definitions: (key, name, field_name, unit, device_class, icon, state_class)
SENSOR_DEFINITIONS: list[tuple[str, str, str, str | None, SensorDeviceClass | None, str | None, SensorStateClass | None]] = [
    # Basic sensors
    ("speed", "Speed", "VehicleSpeed", UnitOfSpeed.KILOMETERS_PER_HOUR, None, "mdi:speedometer", SensorStateClass.MEASUREMENT),
    ("shift_state", "Shift State", "Gear", None, None, "mdi:car-shift-pattern", None),
    ("battery", "Battery", "Soc", PERCENTAGE, SensorDeviceClass.BATTERY, None, SensorStateClass.MEASUREMENT),
    ("range", "Range", "EstBatteryRange", UnitOfLength.KILOMETERS, None, "mdi:map-marker-distance", SensorStateClass.MEASUREMENT),
    ("charging_state", "Charging State", "ChargeState", None, None, "mdi:ev-station", None),
    ("charger_voltage", "Charger Voltage", "ChargerVoltage", UnitOfElectricPotential.VOLT, SensorDeviceClass.VOLTAGE, None, SensorStateClass.MEASUREMENT),
    ("charger_current", "Charger Current", "ChargerActualCurrent", UnitOfElectricCurrent.AMPERE, SensorDeviceClass.CURRENT, None, SensorStateClass.MEASUREMENT),
    ("odometer", "Odometer", "Odometer", UnitOfLength.KILOMETERS, None, "mdi:counter", SensorStateClass.TOTAL_INCREASING),
    # Temperature sensors
    ("inside_temp", "Inside Temperature", "InsideTemp", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, "mdi:thermometer", SensorStateClass.MEASUREMENT),
    ("outside_temp", "Outside Temperature", "OutsideTemp", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, "mdi:thermometer", SensorStateClass.MEASUREMENT),
    # TPMS sensors (Tire Pressure Monitoring System)
    ("tpms_front_left", "Tire Pressure Front Left", "TpmsPressureFl", UnitOfPressure.BAR, SensorDeviceClass.PRESSURE, "mdi:car-tire-alert", SensorStateClass.MEASUREMENT),
    ("tpms_front_right", "Tire Pressure Front Right", "TpmsPressureFr", UnitOfPressure.BAR, SensorDeviceClass.PRESSURE, "mdi:car-tire-alert", SensorStateClass.MEASUREMENT),
    ("tpms_rear_left", "Tire Pressure Rear Left", "TpmsPressureRl", UnitOfPressure.BAR, SensorDeviceClass.PRESSURE, "mdi:car-tire-alert", SensorStateClass.MEASUREMENT),
    ("tpms_rear_right", "Tire Pressure Rear Right", "TpmsPressureRr", UnitOfPressure.BAR, SensorDeviceClass.PRESSURE, "mdi:car-tire-alert", SensorStateClass.MEASUREMENT),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tesla sensors from a config entry."""
    data = entry.runtime_data
    vehicle_name = data.vehicle_name
    vehicle_vin = data.vehicle_vin
    device_info = data.device_info
    mqtt_client = data.mqtt_client

    _LOGGER.info("Setting up Tesla sensors for %s", vehicle_name)

    # Create sensor entities
    entities: list[TeslaSensor] = []
    for key, name, field, unit, device_class, icon, state_class in SENSOR_DEFINITIONS:
        entity = TeslaSensor(
            vehicle_name=vehicle_name,
            vehicle_vin=vehicle_vin,
            device_info=device_info,
            sensor_key=key,
            sensor_name=name,
            field_name=field,
            unit=unit,
            device_class=device_class,
            icon=icon,
            state_class=state_class,
        )
        entities.append(entity)

    async_add_entities(entities)

    # Register callbacks with MQTT client
    for entity in entities:
        mqtt_client.register_callback(entity.field_name, entity.update_value)
        _LOGGER.debug("Registered callback for field: %s", entity.field_name)


class TeslaSensor(SensorEntity):
    """Representation of a Tesla vehicle sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        vehicle_name: str,
        vehicle_vin: str,
        device_info: dict[str, Any],
        sensor_key: str,
        sensor_name: str,
        field_name: str,
        unit: str | None,
        device_class: SensorDeviceClass | None,
        icon: str | None,
        state_class: SensorStateClass | None,
    ) -> None:
        """Initialize the sensor."""
        self._vehicle_name = vehicle_name
        self._vehicle_vin = vehicle_vin
        self._sensor_key = sensor_key
        self._field_name = field_name
        self._state: Any = None
        self._last_updated: str | None = None

        # Entity properties
        self._attr_unique_id = f"{vehicle_vin}_{sensor_key}"
        self._attr_translation_key = sensor_key
        self._attr_name = sensor_name
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_icon = icon
        self._attr_state_class = state_class
        self._attr_device_info = device_info

        _LOGGER.debug("Initialized Tesla sensor: %s", self._attr_name)

    @property
    def field_name(self) -> str:
        """Return the telemetry field name."""
        return self._field_name

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        attrs: dict[str, Any] = {}
        if self._last_updated:
            attrs["last_updated"] = self._last_updated
        return attrs

    @callback
    def update_value(self, value: Any, data: dict[str, Any]) -> None:
        """Update sensor value from MQTT message."""
        try:
            # Update state based on field type
            if self._field_name == "Gear":
                self._state = str(value).upper() if value else "P"

            elif self._field_name in ["Soc", "BatteryLevel"]:
                self._state = round(float(value), 1) if value is not None else None

            elif self._field_name == "VehicleSpeed":
                self._state = round(float(value), 1) if value is not None else 0

            elif self._field_name == "EstBatteryRange":
                self._state = round(float(value), 1) if value is not None else None

            elif self._field_name == "ChargeState":
                self._state = str(value).capitalize() if value else "Disconnected"

            elif self._field_name in ["ChargerVoltage", "ChargerActualCurrent"]:
                self._state = round(float(value), 1) if value is not None else 0

            elif self._field_name == "Odometer":
                self._state = round(float(value), 1) if value is not None else None

            elif self._field_name in ["InsideTemp", "OutsideTemp"]:
                self._state = round(float(value), 1) if value is not None else None

            elif self._field_name.startswith("TpmsPressure"):
                # TPMS values come in bar
                self._state = round(float(value), 2) if value is not None else None

            else:
                self._state = value

            self._last_updated = data.get("timestamp")

            _LOGGER.debug("Updated sensor %s: %s", self._attr_name, self._state)

            # Trigger state update in Home Assistant
            self.async_write_ha_state()

        except (ValueError, TypeError) as err:
            _LOGGER.error("Error updating sensor %s: %s", self._attr_name, err)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        if self._field_name == "Soc":
            return self._state is not None
        return True
