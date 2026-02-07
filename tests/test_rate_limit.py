"""Tests for rate limiting helpers."""

from datetime import datetime, timezone, timedelta

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from canpoli.api_keys import hash_api_key
from canpoli.config import get_settings
from canpoli.models import ApiKey, Billing, User
from canpoli.rate_limit import (
    _apply_rate_limit,
    _client_ip,
    get_usage_count,
    increment_usage,
    is_subscription_active,
    rate_limit_dependency,
)
from canpoli import redis_client


def _make_request(headers=None, client=None) -> Request:
    scope = {
        "type": "http",
        "headers": headers or [],
        "client": client,
    }
    return Request(scope)


@pytest.fixture(autouse=True)
def _reset_redis_client():
    redis_client._redis_client = None
    yield
    redis_client._redis_client = None


def test_client_ip_forwarded_header():
    request = _make_request(headers=[(b"x-forwarded-for", b"1.1.1.1, 2.2.2.2")])
    assert _client_ip(request) == "1.1.1.1"


def test_client_ip_from_client():
    request = _make_request(client=("3.3.3.3", 1234))
    assert _client_ip(request) == "3.3.3.3"


def test_client_ip_unknown():
    request = _make_request()
    assert _client_ip(request) == "unknown"


def test_is_subscription_active():
    assert is_subscription_active("active") is True
    assert is_subscription_active("trialing") is True
    assert is_subscription_active("canceled") is False
    assert is_subscription_active(None) is False


@pytest.mark.asyncio
async def test_apply_rate_limit_exceeded():
    await _apply_rate_limit(identity="ip:1.2.3.4", limit=1)
    with pytest.raises(HTTPException) as excinfo:
        await _apply_rate_limit(identity="ip:1.2.3.4", limit=1)
    assert excinfo.value.status_code == 429


@pytest.mark.asyncio
async def test_rate_limit_dependency_api_key_sets_state(test_session, monkeypatch):
    monkeypatch.setenv("API_KEY_HMAC_SECRET", "test-secret")
    get_settings.cache_clear()

    user = User(auth_provider="clerk", auth_user_id="auth-1", email="a@b.com")
    test_session.add(user)
    await test_session.flush()

    period_start = datetime.now(timezone.utc) - timedelta(days=1)
    period_end = datetime.now(timezone.utc) + timedelta(days=30)

    billing = Billing(
        user_id=user.id,
        status="active",
        current_period_start=period_start,
        current_period_end=period_end,
    )
    test_session.add(billing)

    plaintext = "cpk_live_testtoken"
    api_key = ApiKey(
        user_id=user.id,
        key_prefix=plaintext[:12],
        key_hash=hash_api_key(plaintext, "test-secret"),
        active=True,
    )
    test_session.add(api_key)
    await test_session.commit()

    request = _make_request(client=("9.9.9.9", 4444))

    await rate_limit_dependency(
        request=request,
        session=test_session,
        api_key=plaintext,
    )

    assert request.state.api_key_id == api_key.id
    assert request.state.usage_period_start == period_start
    assert request.state.usage_period_end == period_end


@pytest.mark.asyncio
async def test_increment_usage_and_get_usage_count():
    request = _make_request(client=("4.4.4.4", 1234))
    request.state.api_key_id = "key-1"
    period_start = datetime.now(timezone.utc) - timedelta(days=2)
    request.state.usage_period_start = period_start
    request.state.usage_period_end = datetime.now(timezone.utc) + timedelta(days=2)

    await increment_usage(request)
    await increment_usage(request)

    count = await get_usage_count("key-1", period_start)
    assert count == 2


@pytest.mark.asyncio
async def test_get_usage_count_missing_returns_zero():
    period_start = datetime.now(timezone.utc)
    count = await get_usage_count("missing", period_start)
    assert count == 0
