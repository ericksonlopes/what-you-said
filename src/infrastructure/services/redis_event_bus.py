import json
import logging
from typing import Any, Dict

from src.domain.interfaces.services.i_event_bus import IEventBus
from src.infrastructure.connectors.redis_connector import RedisConnector

logger = logging.getLogger(__name__)


class RedisEventBus(IEventBus):
    """Redis-backed event bus using Pub/Sub."""

    def __init__(self):
        self._redis = RedisConnector.get_client(decode_responses=True)

    def publish(self, channel: str, message: Dict[str, Any]):
        """Publishes a JSON message to a Redis channel with UUID support."""
        import uuid

        def _json_serial(obj):
            if isinstance(obj, (uuid.UUID,)):
                return str(obj)
            raise TypeError(f"Type {type(obj)} not serializable")

        try:
            payload = json.dumps(message, default=_json_serial, ensure_ascii=False)
            self._redis.publish(channel, payload)
        except Exception as e:
            logger.error("Failed to publish event: %s", e, exc_info=True)
            try:
                self._redis.publish(channel, str(message))
            except Exception as e2:
                logger.error("Fallback publish also failed: %s", e2, exc_info=True)

    def subscribe(self, channel: str):
        """Subscribes to a Redis channel and yields messages as they arrive."""
        pubsub = self._redis.pubsub()
        pubsub.subscribe(channel)

        for message in pubsub.listen():
            if message["type"] == "message":
                yield json.loads(message["data"])
