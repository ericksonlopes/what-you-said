import json
from unittest.mock import MagicMock, patch

import pytest

from src.infrastructure.services.redis_event_bus import RedisEventBus


@pytest.mark.RedisEventBus
class TestRedisEventBus:
    @patch("redis.Redis")
    def test_init(self, mock_redis_cls):
        bus = RedisEventBus()
        assert mock_redis_cls.called
        assert bus._redis is not None

    @patch("redis.Redis")
    def test_publish(self, mock_redis_cls):
        mock_redis = MagicMock()
        mock_redis_cls.return_value = mock_redis

        bus = RedisEventBus()
        message = {"event": "test"}
        bus.publish("test_channel", message)

        mock_redis.publish.assert_called_once_with("test_channel", json.dumps(message))

    @patch("redis.Redis")
    def test_subscribe(self, mock_redis_cls):
        mock_redis = MagicMock()
        mock_redis_cls.return_value = mock_redis

        mock_pubsub = MagicMock()
        mock_redis.pubsub.return_value = mock_pubsub

        # Mock pubsub.listen() to return one message then stop
        mock_pubsub.listen.return_value = [
            {"type": "message", "data": json.dumps({"hello": "world"})},
            {"type": "subscribe", "data": 1},  # Should be ignored
        ]

        bus = RedisEventBus()
        messages = list(bus.subscribe("test_channel"))

        assert len(messages) == 1
        assert messages[0] == {"hello": "world"}
        mock_pubsub.subscribe.assert_called_once_with("test_channel")
