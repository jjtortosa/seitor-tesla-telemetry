"""Kafka consumer for Tesla Fleet Telemetry messages."""
import asyncio
import logging
from typing import Any, Callable, Dict, Optional

from kafka import KafkaConsumer
from kafka.errors import KafkaError

from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_call_later

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

        _LOGGER.debug(
            "Initialized TeslaKafkaConsumer: broker=%s, topic=%s",
            broker,
            topic,
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

        # Connect in a separate task to avoid blocking
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
            # Create Kafka consumer in executor to avoid blocking
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
            auto_offset_reset="latest",  # Start from latest messages
            enable_auto_commit=True,
            group_id=f"ha_tesla_{self._vehicle_vin}",
            value_deserializer=None,  # We'll handle Protobuf parsing manually
            session_timeout_ms=30000,
            heartbeat_interval_ms=10000,
        )

    async def _consume_messages(self) -> None:
        """Consume messages from Kafka."""
        if not self._consumer:
            return

        _LOGGER.info("Starting to consume messages from topic: %s", self._topic)

        while self._running and self._consumer:
            try:
                # Poll for messages (non-blocking with timeout)
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
        """Process a single Kafka message."""
        try:
            # Parse Protobuf message
            data = await self._parse_protobuf(record.value)

            if data is None:
                return

            # Log message reception
            _LOGGER.debug(
                "Received telemetry message: offset=%d, fields=%s",
                record.offset,
                list(data.keys())[:5],  # Log first 5 fields
            )

            # Notify callbacks
            await self._notify_callbacks(data)

        except Exception as err:
            _LOGGER.error("Error processing message: %s", err)

    async def _parse_protobuf(self, raw_data: bytes) -> Optional[Dict[str, Any]]:
        """Parse Protobuf message."""
        try:
            # Import Protobuf schema (generated from vehicle_data.proto)
            # For now, we'll use a simplified parser
            # In production, use: from . import vehicle_data_pb2

            # TODO: Implement proper Protobuf parsing
            # vehicle_data = vehicle_data_pb2.VehicleData()
            # vehicle_data.ParseFromString(raw_data)

            # For now, return a placeholder
            # This will be replaced with actual Protobuf parsing
            data = self._parse_simplified(raw_data)

            return data

        except Exception as err:
            _LOGGER.error("Failed to parse Protobuf message: %s", err)
            return None

    def _parse_simplified(self, raw_data: bytes) -> Dict[str, Any]:
        """Simplified parser (placeholder for Protobuf parsing)."""
        # This is a placeholder implementation
        # Real implementation will use vehicle_data_pb2.py

        # For testing, you can decode simple JSON messages
        # or return mock data

        try:
            import json
            # Try JSON first (for testing)
            data = json.loads(raw_data.decode("utf-8"))
            return data
        except Exception:
            # If not JSON, return empty dict
            # Real implementation will parse Protobuf
            _LOGGER.warning("Simplified parser used - implement Protobuf parsing")
            return {}

    async def _notify_callbacks(self, data: Dict[str, Any]) -> None:
        """Notify registered callbacks with parsed data."""
        for data_type, callbacks in self._callbacks.items():
            if data_type in data:
                value = data[data_type]
                for callback in callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(value, data)
                        else:
                            await self._hass.async_add_executor_job(
                                callback, value, data
                            )
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

        # Close existing consumer
        if self._consumer:
            try:
                await self._hass.async_add_executor_job(self._consumer.close)
            except Exception:
                pass
            self._consumer = None

        # Wait before reconnecting
        await asyncio.sleep(delay)
