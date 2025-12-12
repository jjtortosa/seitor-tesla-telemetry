"""Kafka consumer for Tesla Fleet Telemetry messages (JSON format)."""
import asyncio
import json
import logging
from typing import Any, Callable, Dict, Optional

from kafka import KafkaConsumer
from kafka.errors import KafkaError

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# Reconnection settings
RECONNECT_DELAY = 30  # seconds
MAX_RECONNECT_ATTEMPTS = 10


class TeslaKafkaConsumer:
    """Kafka consumer for Tesla telemetry data."""

    def __init__(
        self,
        broker: str,
        topic: str,
        vehicle_vin: str,
        hass: HomeAssistant,
    ) -> None:
        """Initialize the Kafka consumer."""
        self._broker = broker
        self._topic = topic
        self._vehicle_vin = vehicle_vin
        self._hass = hass
        self._consumer: Optional[KafkaConsumer] = None
        self._running = False
        self._reconnect_attempts = 0
        self._callbacks: Dict[str, list[Callable]] = {}

        _LOGGER.info(
            "Initialized TeslaKafkaConsumer: broker=%s, topic=%s, vin=%s",
            broker,
            topic,
            vehicle_vin[:8] + "***",
        )

    def register_callback(self, data_type: str, callback: Callable) -> None:
        """Register a callback for specific data type updates."""
        if data_type not in self._callbacks:
            self._callbacks[data_type] = []
        self._callbacks[data_type].append(callback)
        _LOGGER.debug("Registered callback for data_type: %s", data_type)

    async def start(self) -> None:
        """Start the Kafka consumer."""
        _LOGGER.info("Starting Tesla Kafka consumer")
        self._running = True
        asyncio.create_task(self._connect_and_consume())

    async def stop(self) -> None:
        """Stop the Kafka consumer."""
        _LOGGER.info("Stopping Tesla Kafka consumer")
        self._running = False

        if self._consumer:
            try:
                await self._hass.async_add_executor_job(self._consumer.close)
                _LOGGER.info("Kafka consumer closed successfully")
            except Exception as err:
                _LOGGER.error("Error closing Kafka consumer: %s", err)

    async def _connect_and_consume(self) -> None:
        """Connect to Kafka and start consuming messages."""
        while self._running:
            try:
                await self._connect()
                await self._consume_messages()
            except KafkaError as err:
                _LOGGER.error("Kafka error: %s", err)
                await self._handle_reconnect()
            except Exception as err:
                _LOGGER.exception("Unexpected error in Kafka consumer: %s", err)
                await self._handle_reconnect()

    async def _connect(self) -> None:
        """Connect to Kafka broker."""
        if self._consumer:
            return

        _LOGGER.info(
            "Connecting to Kafka broker: %s, topic: %s",
            self._broker,
            self._topic,
        )

        try:
            self._consumer = await self._hass.async_add_executor_job(
                self._create_consumer
            )
            _LOGGER.info("Successfully connected to Kafka broker")
            self._reconnect_attempts = 0

        except Exception as err:
            _LOGGER.error("Failed to connect to Kafka: %s", err)
            self._consumer = None
            raise

    def _create_consumer(self) -> KafkaConsumer:
        """Create Kafka consumer (runs in executor)."""
        return KafkaConsumer(
            self._topic,
            bootstrap_servers=[self._broker],
            auto_offset_reset="latest",
            enable_auto_commit=True,
            group_id=f"ha_tesla_{self._vehicle_vin}_json",
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            session_timeout_ms=30000,
            heartbeat_interval_ms=10000,
        )

    async def _consume_messages(self) -> None:
        """Consume messages from Kafka."""
        if not self._consumer:
            return

        _LOGGER.info("Starting to consume JSON messages from topic: %s", self._topic)

        while self._running and self._consumer:
            try:
                messages = await self._hass.async_add_executor_job(
                    lambda: self._consumer.poll(timeout_ms=1000)
                )

                for topic_partition, records in messages.items():
                    for record in records:
                        await self._process_message(record)

            except Exception as err:
                _LOGGER.error("Error consuming messages: %s", err)
                raise

    async def _process_message(self, record: Any) -> None:
        """Process a single Kafka message (JSON format)."""
        try:
            data = record.value  # Already parsed as JSON by deserializer

            if not data:
                return

            # Check VIN matches
            vin = data.get("vin", "")
            if vin and vin != self._vehicle_vin:
                return

            # Parse data fields
            parsed_data = self._parse_json_data(data)

            if parsed_data:
                _LOGGER.debug(
                    "Received telemetry: vin=%s, fields=%s",
                    vin[-8:] if vin else "unknown",
                    list(parsed_data.keys()),
                )
                await self._notify_callbacks(parsed_data)

        except Exception as err:
            _LOGGER.error("Error processing message: %s", err)

    def _parse_json_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse JSON telemetry data from fleet-telemetry."""
        result = {}

        # Extract VIN and timestamp
        if data.get("vin"):
            result["vin"] = data["vin"]
        if data.get("createdAt"):
            result["timestamp"] = data["createdAt"]

        # Parse data array
        for item in data.get("data", []):
            key = item.get("key")
            value_obj = item.get("value", {})

            if not key:
                continue

            # Extract the actual value based on type
            value = self._extract_value(value_obj)
            if value is not None:
                result[key] = value

        return result

    def _extract_value(self, value_obj: Dict[str, Any]) -> Any:
        """Extract value from the value object."""
        # Check each possible value type
        if "stringValue" in value_obj:
            return value_obj["stringValue"]
        if "doubleValue" in value_obj:
            return value_obj["doubleValue"]
        if "floatValue" in value_obj:
            return value_obj["floatValue"]
        if "intValue" in value_obj:
            return value_obj["intValue"]
        if "longValue" in value_obj:
            return value_obj["longValue"]
        if "booleanValue" in value_obj:
            return value_obj["booleanValue"]
        if "locationValue" in value_obj:
            loc = value_obj["locationValue"]
            return {
                "latitude": loc.get("latitude"),
                "longitude": loc.get("longitude"),
            }
        if "invalid" in value_obj:
            return None

        # Return first available value
        for key, val in value_obj.items():
            if val is not None:
                return val

        return None

    async def _notify_callbacks(self, data: Dict[str, Any]) -> None:
        """Notify registered callbacks with parsed data."""
        for data_type, callbacks in self._callbacks.items():
            if data_type in data:
                value = data[data_type]
                for callback in callbacks:
                    try:
                        callback(value, data)
                        _LOGGER.debug("Called callback for %s: %s", data_type, value)
                    except Exception as err:
                        _LOGGER.error(
                            "Error in callback for %s: %s", data_type, err
                        )

    async def _handle_reconnect(self) -> None:
        """Handle reconnection logic."""
        self._reconnect_attempts += 1

        if self._reconnect_attempts > MAX_RECONNECT_ATTEMPTS:
            _LOGGER.error(
                "Max reconnection attempts reached (%d). Stopping consumer.",
                MAX_RECONNECT_ATTEMPTS,
            )
            self._running = False
            return

        delay = RECONNECT_DELAY * self._reconnect_attempts
        _LOGGER.warning(
            "Reconnecting to Kafka in %d seconds (attempt %d/%d)",
            delay,
            self._reconnect_attempts,
            MAX_RECONNECT_ATTEMPTS,
        )

        if self._consumer:
            try:
                await self._hass.async_add_executor_job(self._consumer.close)
            except Exception:
                pass
            self._consumer = None

        await asyncio.sleep(delay)
