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
        """Parse Protobuf message from Tesla Fleet Telemetry."""
        try:
            # Import Protobuf schema (generated from vehicle_data.proto)
            from . import vehicle_data_pb2

            # Parse the Protobuf Payload message
            payload = vehicle_data_pb2.Payload()
            payload.ParseFromString(raw_data)

            # Convert Payload to a dictionary for easier handling
            data = {}

            # Extract VIN
            if payload.vin:
                data["vin"] = payload.vin

            # Extract timestamp
            if payload.HasField("created_at"):
                data["timestamp"] = payload.created_at.seconds

            # Extract all data fields
            for datum in payload.data:
                field_name = vehicle_data_pb2.Field.Name(datum.key)
                value = self._extract_value(datum.value)

                if value is not None:
                    data[field_name] = value

            return data

        except Exception as err:
            _LOGGER.error("Failed to parse Protobuf message: %s", err)
            _LOGGER.debug("Raw data: %s", raw_data[:100])  # Log first 100 bytes
            return None

    def _extract_value(self, value_msg: Any) -> Any:
        """Extract value from Protobuf Value message."""
        # The Value message has a oneof field, so we need to check which field is set
        from . import vehicle_data_pb2

        # Check which value field is set
        which = value_msg.WhichOneof("value")

        if which is None or which == "invalid":
            return None

        # String value
        if which == "string_value":
            return value_msg.string_value

        # Integer values
        if which == "int_value":
            return value_msg.int_value
        if which == "long_value":
            return value_msg.long_value

        # Float values
        if which == "float_value":
            return value_msg.float_value
        if which == "double_value":
            return value_msg.double_value

        # Boolean value
        if which == "boolean_value":
            return value_msg.boolean_value

        # Location value (GPS coordinates)
        if which == "location_value":
            return {
                "latitude": value_msg.location_value.latitude,
                "longitude": value_msg.location_value.longitude,
            }

        # Enum values (convert to string)
        if which == "charging_value":
            return vehicle_data_pb2.ChargingState.Name(value_msg.charging_value)
        if which == "shift_state_value":
            return vehicle_data_pb2.ShiftState.Name(value_msg.shift_state_value)

        # Time value
        if which == "time_value":
            return {
                "hour": value_msg.time_value.hour,
                "minute": value_msg.time_value.minute,
                "second": value_msg.time_value.second,
            }

        # Door values
        if which == "door_value":
            return {
                "driver_front": value_msg.door_value.DriverFront,
                "driver_rear": value_msg.door_value.DriverRear,
                "passenger_front": value_msg.door_value.PassengerFront,
                "passenger_rear": value_msg.door_value.PassengerRear,
                "trunk_front": value_msg.door_value.TrunkFront,
                "trunk_rear": value_msg.door_value.TrunkRear,
            }

        # Tire location (for TPMS)
        if which == "tire_location_value":
            return {
                "front_left": value_msg.tire_location_value.front_left,
                "front_right": value_msg.tire_location_value.front_right,
                "rear_left": value_msg.tire_location_value.rear_left,
                "rear_right": value_msg.tire_location_value.rear_right,
            }

        # For other enum types, try to convert to string
        try:
            # Get the enum type name and convert to string
            enum_value = getattr(value_msg, which)
            if hasattr(enum_value, "Name"):
                return enum_value.Name(enum_value)
            return int(enum_value)
        except Exception:
            pass

        # Fallback: return the raw value
        _LOGGER.debug("Unknown value type: %s", which)
        return getattr(value_msg, which, None)

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
