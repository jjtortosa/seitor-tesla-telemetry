"""Support for Tesla vehicle sensors."""
import logging
from typing import Any, Dict, Optional

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
    UnitOfSpeed,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from . import CONF_VEHICLE_NAME, CONF_VEHICLE_VIN, DOMAIN

_LOGGER = logging.getLogger(__name__)


# Sensor definitions: (name, field_name, unit, device_class, icon, state_class)
SENSOR_DEFINITIONS = [
    ("Speed", "Speed", UnitOfSpeed.KILOMETERS_PER_HOUR, None, "mdi:speedometer", SensorStateClass.MEASUREMENT),
    ("Shift State", "ShiftState", None, None, "mdi:car-shift-pattern", None),
    ("Battery", "Soc", PERCENTAGE, SensorDeviceClass.BATTERY, None, SensorStateClass.MEASUREMENT),
    ("Range", "EstBatteryRange", UnitOfLength.KILOMETERS, None, "mdi:map-marker-distance", SensorStateClass.MEASUREMENT),
    ("Charging State", "ChargingState", None, None, "mdi:ev-station", None),
    ("Charger Voltage", "ChargerVoltage", UnitOfElectricPotential.VOLT, SensorDeviceClass.VOLTAGE, None, SensorStateClass.MEASUREMENT),
    ("Charger Current", "ChargerActualCurrent", UnitOfElectricCurrent.AMPERE, SensorDeviceClass.CURRENT, None, SensorStateClass.MEASUREMENT),
    ("Odometer", "Odometer", UnitOfLength.KILOMETERS, None, "mdi:counter", SensorStateClass.TOTAL_INCREASING),
]


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: Optional[DiscoveryInfoType] = None,
) -> None:
    """Set up the Tesla sensor platform."""
    if discovery_info is None:
        return

    vehicle_name = discovery_info.get(CONF_VEHICLE_NAME, "Tesla")
    vehicle_vin = discovery_info.get(CONF_VEHICLE_VIN)

    _LOGGER.info("Setting up Tesla sensors for %s", vehicle_name)

    # Create sensor entities
    entities = []
    for name, field, unit, device_class, icon, state_class in SENSOR_DEFINITIONS:
        entity = TeslaSensor(
            hass=hass,
            vehicle_name=vehicle_name,
            vehicle_vin=vehicle_vin,
            sensor_name=name,
            field_name=field,
            unit=unit,
            device_class=device_class,
            icon=icon,
            state_class=state_class,
        )
        entities.append(entity)

    async_add_entities(entities, True)

    # Register callbacks with Kafka consumer
    consumer = hass.data[DOMAIN]["consumer"]
    for entity in entities:
        consumer.register_callback(entity._field_name, entity.update_value)


class TeslaSensor(SensorEntity):
    """Representation of a Tesla vehicle sensor."""

    def __init__(
        self,
        hass: HomeAssistant,
        vehicle_name: str,
        vehicle_vin: str,
        sensor_name: str,
        field_name: str,
        unit: Optional[str],
        device_class: Optional[SensorDeviceClass],
        icon: Optional[str],
        state_class: Optional[SensorStateClass],
    ) -> None:
        """Initialize the sensor."""
        self._hass = hass
        self._vehicle_name = vehicle_name
        self._vehicle_vin = vehicle_vin
        self._sensor_name = sensor_name
        self._field_name = field_name
        self._state: Optional[Any] = None
        self._attributes: Dict[str, Any] = {}

        # Entity properties
        self._attr_unique_id = f"tesla_{vehicle_vin.lower()}_{field_name.lower()}"
        self._attr_name = f"{vehicle_name} {sensor_name}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_icon = icon
        self._attr_state_class = state_class

        _LOGGER.debug("Initialized Tesla sensor: %s", self._attr_name)

    @property
    def native_value(self) -> Optional[Any]:
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return entity specific state attributes."""
        return self._attributes

    @callback
    async def update_value(self, value: Any, data: Dict[str, Any]) -> None:
        """Update sensor value from Kafka message."""
        try:
            # Update state based on field type
            if self._field_name == "ShiftState":
                # Convert to uppercase and handle None
                self._state = str(value).upper() if value else "P"

            elif self._field_name == "Soc":
                # Battery percentage
                self._state = round(float(value), 1) if value is not None else None

            elif self._field_name == "Speed":
                # Speed in km/h
                self._state = round(float(value), 1) if value is not None else 0

            elif self._field_name == "EstBatteryRange":
                # Range in km
                self._state = round(float(value), 1) if value is not None else None

            elif self._field_name == "ChargingState":
                # Charging state: Charging, Complete, Disconnected, etc.
                self._state = str(value).capitalize() if value else "Disconnected"

            elif self._field_name in ["ChargerVoltage", "ChargerActualCurrent"]:
                # Charger values
                self._state = round(float(value), 1) if value is not None else 0

            elif self._field_name == "Odometer":
                # Odometer in km
                self._state = round(float(value), 1) if value is not None else None

            else:
                # Generic value
                self._state = value

            # Store raw value in attributes
            self._attributes["raw_value"] = value
            self._attributes["last_updated"] = data.get("timestamp", None)

            _LOGGER.debug(
                "Updated sensor %s: %s",
                self._attr_name,
                self._state,
            )

            # Trigger state update in Home Assistant
            self.async_write_ha_state()

        except (ValueError, TypeError) as err:
            _LOGGER.error("Error updating sensor %s: %s", self._attr_name, err)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        # Most sensors are always available even if value is None
        # Except for critical ones like battery
        if self._field_name == "Soc":
            return self._state is not None
        return True

    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device information for this entity."""
        return {
            "identifiers": {(DOMAIN, self._vehicle_vin)},
            "name": self._vehicle_name,
            "manufacturer": "Tesla",
            "model": "Model Y",
            "sw_version": None,
        }
