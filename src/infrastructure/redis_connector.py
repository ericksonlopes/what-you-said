from typing import Optional

import redis

from src.config.settings import settings


class RedisConnector:
    """Centralized Redis connection pool to avoid creating multiple independent connections."""

    _pool: Optional[redis.ConnectionPool] = None

    @classmethod
    def _get_pool(cls) -> redis.ConnectionPool:
        if cls._pool is None:
            cls._pool = redis.ConnectionPool(
                host=settings.redis.host,
                port=settings.redis.port,
                db=settings.redis.db,
                password=settings.redis.password,
            )
        return cls._pool

    @classmethod
    def get_client(cls, decode_responses: bool = True) -> redis.Redis:
        """Get a Redis client using the shared connection pool."""
        return redis.Redis(
            connection_pool=cls._get_pool(),
            decode_responses=decode_responses,
        )

    @classmethod
    def reset_pool(cls) -> None:
        """Reset the connection pool (useful for testing)."""
        if cls._pool is not None:
            cls._pool.disconnect()
            cls._pool = None
