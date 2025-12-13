"""MQTT client for Tesla Fleet Telemetry messages."""
from __future__ import annotations

import json
import logging
from typing import Any, Callable

from homeassistant.components import mqtt
from homeassistant.core import HomeAssistant, callback

_LOGGER = logging.getLogger(__name__)


class TeslaMQTTClient:
    """MQTT client for Tesla telemetry data using HA's native MQTT."""

    def __init__(
        self,
        hass: HomeAssistant,
        topic_base: str,
        vehicle_vin: str,
    ) -> None:
        """Initialize the MQTT client."""
        self._hass = hass
        self._topic_base = topic_base
        self._vehicle_vin = vehicle_vin
        self._callbacks: dict[str, list[Callable]] = {}
        self._unsubscribes: list[Callable] = []
        self._connected = False

        _LOGGER.info(
            "Initialized TeslaMQTTClient: topic_base=%s, vin=%s",
            topic_base,
            vehicle_vin[:8] + "***",
        )

    def register_callback(self, data_type: str, callback_fn: Callable) -> None:
        """Register a callback for specific data type updates."""
        if data_type not in self._callbacks:
            self._callbacks[data_type] = []
        self._callbacks[data_type].append(callback_fn)
        _LOGGER.debug("Registered callback for data_type: %s", data_type)

    async def start(self) -> None:
        """Start MQTT subscriptions."""
        _LOGGER.info("Starting Tesla MQTT subscriptions")

        # Subscribe to vehicle metrics: <topic_base>/<VIN>/v/#
        metrics_topic = f"{self._topic_base}/{self._vehicle_vin}/v/#"

        # Subscribe to connectivity: <topic_base>/<VIN>/connectivity
        connectivity_topic = f"{self._topic_base}/{self._vehicle_vin}/connectivity"

        # Subscribe to alerts: <topic_base>/<VIN>/alerts/#
        alerts_topic = f"{self._topic_base}/{self._vehicle_vin}/alerts/#"

        try:
            # Subscribe to metrics (all vehicle data fields)
            unsub_metrics = await mqtt.async_subscribe(
                self._hass,
                metrics_topic,
                self._handle_metrics_message,
                qos=1,
            )
            self._unsubscribes.append(unsub_metrics)
            _LOGGER.info("Subscribed to MQTT topic: %s", metrics_topic)

            # Subscribe to connectivity
            unsub_connectivity = await mqtt.async_subscribe(
                self._hass,
                connectivity_topic,
                self._handle_connectivity_message,
                qos=1,
            )
            self._unsubscribes.append(unsub_connectivity)
            _LOGGER.debug("Subscribed to MQTT topic: %s", connectivity_topic)

            # Subscribe to alerts
            unsub_alerts = await mqtt.async_subscribe(
                self._hass,
                alerts_topic,
                self._handle_alerts_message,
                qos=1,
            )
            self._unsubscribes.append(unsub_alerts)
            _LOGGER.debug("Subscribed to MQTT topic: %s", alerts_topic)

            self._connected = True
            _LOGGER.info("Tesla MQTT client started successfully")

        except Exception as err:
            _LOGGER.error("Failed to subscribe to MQTT topics: %s", err)
            raise

    async def stop(self) -> None:
        """Stop MQTT subscriptions."""
        _LOGGER.info("Stopping Tesla MQTT client")

        for unsub in self._unsubscribes:
            try:
                unsub()
            except Exception as err:
                _LOGGER.error("Error unsubscribing from MQTT: %s", err)

        self._unsubscribes.clear()
        self._connected = False
        _LOGGER.info("Tesla MQTT client stopped")

    @property
    def connected(self) -> bool:
        """Return True if MQTT is connected."""
        return self._connected

    @callback
    def _handle_metrics_message(self, msg: mqtt.ReceiveMessage) -> None:
        """Handle incoming metrics message from Fleet Telemetry.

        Topic format: <topic_base>/<VIN>/v/<field_name>
        Payload format: JSON with the field value
        """
        try:
            # Extract field name from topic
            # Example: tesla/LRWYGCFS3RC210528/v/VehicleSpeed -> VehicleSpeed
            topic_parts = msg.topic.split("/")
            if len(topic_parts) < 4:
                _LOGGER.warning("Invalid topic format: %s", msg.topic)
                return

            field_name = topic_parts[-1]

            # Parse JSON payload
            try:
                payload = json.loads(msg.payload)
            except json.JSONDecodeError:
                # Some values might be sent as plain text
                payload = msg.payload.decode("utf-8") if isinstance(msg.payload, bytes) else msg.payload

            # Extract value from payload
            value = self._extract_value(payload)

            _LOGGER.debug(
                "Received telemetry: field=%s, value=%s",
                field_name,
                value,
            )

            # Notify callbacks
            self._notify_callbacks(field_name, value)

        except Exception as err:
            _LOGGER.error("Error processing metrics message: %s", err)

    @callback
    def _handle_connectivity_message(self, msg: mqtt.ReceiveMessage) -> None:
        """Handle connectivity status message.

        Topic: <topic_base>/<VIN>/connectivity
        Payload: {"ConnectionId": "...", "Status": "connected/disconnected", "CreatedAt": "..."}
        """
        try:
            payload = json.loads(msg.payload)
            status = payload.get("Status", "").lower()
            is_connected = status == "connected"

            _LOGGER.debug("Vehicle connectivity: %s", status)

            # Notify connectivity callbacks
            self._notify_callbacks("connectivity", is_connected)

        except Exception as err:
            _LOGGER.error("Error processing connectivity message: %s", err)

    @callback
    def _handle_alerts_message(self, msg: mqtt.ReceiveMessage) -> None:
        """Handle alerts message.

        Topic: <topic_base>/<VIN>/alerts/<alert_name>/current or /history
        Payload: {"Name": "...", "StartedAt": "...", "EndedAt": "...", "Audiences": [...]}
        """
        try:
            payload = json.loads(msg.payload)
            alert_name = payload.get("Name", "unknown")

            _LOGGER.debug("Vehicle alert: %s", alert_name)

            # Could be used for notifications in the future

        except Exception as err:
            _LOGGER.error("Error processing alerts message: %s", err)

    def _extract_value(self, payload: Any) -> Any:
        """Extract value from MQTT payload.

        Fleet Telemetry MQTT format can be:
        - Simple value: {"value": 65}
        - Direct value: 65 or "Charging"
        - Location: {"latitude": 41.38, "longitude": 2.17}
        """
        if isinstance(payload, dict):
            # Check for "value" key (common format)
            if "value" in payload:
                return payload["value"]
            # Location format
            if "latitude" in payload and "longitude" in payload:
                return payload
            # Return the dict as-is
            return payload

        # Direct value (string, number, bool)
        return payload

    def _notify_callbacks(self, field_name: str, value: Any) -> None:
        """Notify registered callbacks with the field value."""
        if field_name in self._callbacks:
            # Create data dict with timestamp placeholder
            data = {"timestamp": None, field_name: value}

            for callback_fn in self._callbacks[field_name]:
                try:
                    callback_fn(value, data)
                except Exception as err:
                    _LOGGER.error(
                        "Error in callback for %s: %s", field_name, err
                    )
