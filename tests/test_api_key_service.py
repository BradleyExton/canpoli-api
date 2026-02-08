"""Tests for API key service."""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from canpoli.api_keys import hash_api_key
from canpoli.config import get_settings
from canpoli.models import ApiKey, Billing, User
from canpoli.redis_client import InMemoryRedis
from canpoli.services.api_key_service import ApiKeyService


@pytest.mark.asyncio
async def test_get_api_key_reveals_once(test_session):
    user = User(auth_provider="clerk", auth_user_id="auth-1", email="a@b.com")
    test_session.add(user)
    await test_session.flush()

    api_key = ApiKey(
        user_id=user.id,
        key_prefix="cpk_live_1234",
        key_hash="hash",
        active=True,
    )
    test_session.add(api_key)
    await test_session.commit()

    redis = InMemoryRedis()
    await redis.set(f"api_key_reveal:{user.id}", "cpk_live_secret", ex=3600)

    service = ApiKeyService(test_session, get_settings(), redis)
    response = await service.get_api_key(user.id)
    assert response.api_key == "cpk_live_secret"
    assert response.masked_key == "cpk_live_1234..."

    second = await service.get_api_key(user.id)
    assert second.api_key is None


@pytest.mark.asyncio
async def test_rotate_api_key_requires_active_subscription(test_session, monkeypatch):
    monkeypatch.setenv("API_KEY_HMAC_SECRET", "test-secret")
    get_settings.cache_clear()

    user = User(auth_provider="clerk", auth_user_id="auth-2", email="b@c.com")
    test_session.add(user)
    await test_session.flush()

    billing = Billing(user_id=user.id, status="active")
    test_session.add(billing)

    old_plaintext = "cpk_live_oldtoken"
    old_key = ApiKey(
        user_id=user.id,
        key_prefix=old_plaintext[:12],
        key_hash=hash_api_key(old_plaintext, "test-secret"),
        active=True,
    )
    test_session.add(old_key)
    await test_session.commit()

    service = ApiKeyService(test_session, get_settings(), None)
    response = await service.rotate_api_key(user.id)
    assert response.api_key.startswith("cpk_live_")

    result = await test_session.execute(select(ApiKey).where(ApiKey.user_id == user.id))
    keys = list(result.scalars().all())
    assert len(keys) == 2
    assert sum(1 for key in keys if key.active) == 1
    assert next(key for key in keys if key.id == old_key.id).active is False


@pytest.mark.asyncio
async def test_rotate_api_key_inactive_subscription_raises(test_session, monkeypatch):
    monkeypatch.setenv("API_KEY_HMAC_SECRET", "test-secret")
    get_settings.cache_clear()

    user = User(auth_provider="clerk", auth_user_id="auth-3", email="c@d.com")
    test_session.add(user)
    await test_session.flush()

    billing = Billing(user_id=user.id, status="canceled")
    test_session.add(billing)
    await test_session.commit()

    service = ApiKeyService(test_session, get_settings(), None)
    with pytest.raises(HTTPException) as excinfo:
        await service.rotate_api_key(user.id)
    assert excinfo.value.status_code == 403


@pytest.mark.asyncio
async def test_activate_or_create_for_user_creates_key(test_session, monkeypatch):
    monkeypatch.setenv("API_KEY_HMAC_SECRET", "test-secret")
    get_settings.cache_clear()

    user = User(auth_provider="clerk", auth_user_id="auth-4", email="d@e.com")
    test_session.add(user)
    await test_session.flush()

    redis = InMemoryRedis()
    service = ApiKeyService(test_session, get_settings(), redis)
    await service.activate_or_create_for_user(user.id, "active")

    result = await test_session.execute(select(ApiKey).where(ApiKey.user_id == user.id))
    api_key = result.scalar_one()
    assert api_key.active is True

    reveal = await redis.get(f"api_key_reveal:{user.id}")
    assert reveal is not None
