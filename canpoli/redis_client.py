"""Redis client with in-memory fallback."""

import asyncio
import time
from typing import Any

import redis.asyncio as redis

from canpoli.config import get_settings
from canpoli.logging_config import get_logger

logger = get_logger(__name__)


class InMemoryRedis:
    """Minimal async Redis-like client for local/testing."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._expiry: dict[str, float] = {}
        self._lock = asyncio.Lock()

    def _cleanup(self, key: str) -> None:
        expiry = self._expiry.get(key)
        if expiry is not None and expiry <= time.time():
            self._data.pop(key, None)
            self._expiry.pop(key, None)

    async def incr(self, key: str) -> int:
        async with self._lock:
            self._cleanup(key)
            value = int(self._data.get(key, 0)) + 1
            self._data[key] = value
            return value

    async def get(self, key: str) -> Any:
        async with self._lock:
            self._cleanup(key)
            return self._data.get(key)

    async def set(self, key: str, value: Any, ex: int | None = None) -> None:
        async with self._lock:
            self._data[key] = value
            if ex is not None:
                self._expiry[key] = time.time() + ex

    async def expire(self, key: str, seconds: int) -> None:
        async with self._lock:
            self._expiry[key] = time.time() + seconds

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._data.pop(key, None)
            self._expiry.pop(key, None)


_redis_client: redis.Redis | InMemoryRedis | None = None


async def get_redis() -> redis.Redis | InMemoryRedis:
    """Get a shared Redis client (or in-memory fallback)."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    settings = get_settings()
    if not settings.redis_url:
        environment = (settings.environment or "development").lower()
        if environment in {"development", "dev", "test", "testing"}:
            logger.warning("REDIS_URL not configured; using in-memory counters")
            _redis_client = InMemoryRedis()
            return _redis_client
        raise RuntimeError("REDIS_URL is required outside development/test")

    _redis_client = redis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )
    return _redis_client
