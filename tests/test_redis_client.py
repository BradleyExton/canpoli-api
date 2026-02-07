"""Tests for Redis client helpers."""

import pytest

from canpoli.config import get_settings
from canpoli import redis_client
from canpoli.redis_client import InMemoryRedis, get_redis


@pytest.mark.asyncio
async def test_inmemoryredis_basic_ops(monkeypatch):
    store = InMemoryRedis()

    monkeypatch.setattr(redis_client.time, "time", lambda: 1000.0)
    await store.set("key", "value", ex=10)
    assert await store.get("key") == "value"

    monkeypatch.setattr(redis_client.time, "time", lambda: 1011.0)
    assert await store.get("key") is None

    await store.set("counter", 0)
    assert await store.incr("counter") == 1
    assert await store.incr("counter") == 2

    monkeypatch.setattr(redis_client.time, "time", lambda: 2000.0)
    await store.expire("counter", 5)
    monkeypatch.setattr(redis_client.time, "time", lambda: 2006.0)
    assert await store.get("counter") is None

    await store.set("temp", "x")
    await store.delete("temp")
    assert await store.get("temp") is None


@pytest.mark.asyncio
async def test_get_redis_fallback(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "")
    get_settings.cache_clear()
    redis_client._redis_client = None

    client = await get_redis()
    assert isinstance(client, InMemoryRedis)


@pytest.mark.asyncio
async def test_get_redis_with_url(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    get_settings.cache_clear()
    redis_client._redis_client = None

    client = await get_redis()
    assert not isinstance(client, InMemoryRedis)
