import pytest
from unittest.mock import patch
from src.infrastructure.connectors.redis_connector import RedisConnector


@pytest.mark.RedisConnector
class TestRedisConnector:
    def test_get_pool_singleton(self):
        RedisConnector.reset_pool()
        with patch("redis.ConnectionPool") as mock_pool:
            pool1 = RedisConnector._get_pool()
            pool2 = RedisConnector._get_pool()

            assert pool1 is pool2
            assert mock_pool.call_count == 1

    def test_get_client(self):
        RedisConnector.reset_pool()
        with patch("redis.ConnectionPool"):
            with patch("redis.Redis") as mock_redis:
                RedisConnector.get_client(decode_responses=True)
                assert mock_redis.called
                # Check decode_responses
                kwargs = mock_redis.call_args[1]
                assert kwargs["decode_responses"] is True

    def test_reset_pool(self):
        RedisConnector.reset_pool()
        with patch("redis.ConnectionPool") as mock_pool:
            RedisConnector._get_pool()
            assert RedisConnector._pool is not None

            RedisConnector.reset_pool()
            assert RedisConnector._pool is None

            # Re-creating should call mock_pool again
            RedisConnector._get_pool()
            assert mock_pool.call_count == 2
