"""Tests for billing service."""

from __future__ import annotations

from datetime import timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from canpoli.api_keys import hash_api_key
from canpoli.config import get_settings
from canpoli.models import ApiKey, Billing, User
from canpoli.redis_client import get_redis
from canpoli.services.billing_service import BillingService


def _make_stripe(subscription_response=None):
    class DummyStripe:
        class Customer:
            @staticmethod
            def create(**_kwargs):
                return SimpleNamespace(id="cus_new")

        class checkout:
            class Session:
                @staticmethod
                def create(**_kwargs):
                    return SimpleNamespace(url="https://checkout.test")

        class billing_portal:
            class Session:
                @staticmethod
                def create(**_kwargs):
                    return SimpleNamespace(url="https://portal.test")

        class Subscription:
            @staticmethod
            def retrieve(_sub_id):
                return subscription_response or {}

    return DummyStripe()


@pytest.mark.asyncio
async def test_create_checkout_session_creates_billing(test_session, monkeypatch):
    monkeypatch.setenv("STRIPE_PRICE_ID", "price_test")
    monkeypatch.setenv("STRIPE_CHECKOUT_SUCCESS_URL", "https://example.com/success")
    monkeypatch.setenv("STRIPE_CHECKOUT_CANCEL_URL", "https://example.com/cancel")
    get_settings.cache_clear()

    user = User(auth_provider="clerk", auth_user_id="auth-10", email="a@b.com")
    test_session.add(user)
    await test_session.flush()

    service = BillingService(test_session, _make_stripe(), get_settings())
    response = await service.create_checkout_session(user)
    assert response.url == "https://checkout.test"

    billing = await test_session.get(Billing, user.id)
    assert billing is not None
    assert billing.stripe_customer_id == "cus_new"


@pytest.mark.asyncio
async def test_handle_webhook_checkout_creates_key(test_session, monkeypatch):
    monkeypatch.setenv("API_KEY_HMAC_SECRET", "test-secret")
    get_settings.cache_clear()

    user = User(auth_provider="clerk", auth_user_id="auth-11", email="b@c.com")
    test_session.add(user)
    await test_session.flush()

    subscription_response = {
        "status": "active",
        "items": {"data": [{"price": {"id": "price_active"}}]},
        "current_period_start": 1000,
        "current_period_end": 2000,
    }

    stripe = _make_stripe(subscription_response=subscription_response)
    service = BillingService(test_session, stripe, get_settings())
    event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "client_reference_id": user.id,
                "subscription": "sub_123",
                "customer": "cus_123",
            }
        },
    }

    await service.handle_webhook_event(event)

    billing = await test_session.get(Billing, user.id)
    assert billing.stripe_customer_id == "cus_123"
    assert billing.status == "active"
    assert billing.price_id == "price_active"
    assert int(billing.current_period_start.replace(tzinfo=timezone.utc).timestamp()) == 1000
    assert int(billing.current_period_end.replace(tzinfo=timezone.utc).timestamp()) == 2000

    result = await test_session.execute(select(ApiKey).where(ApiKey.user_id == user.id))
    api_key = result.scalar_one()
    assert api_key.active is True

    redis = await get_redis()
    reveal = await redis.get(f"api_key_reveal:{user.id}")
    assert reveal is not None


@pytest.mark.asyncio
async def test_handle_webhook_subscription_update_deactivates_key(test_session, monkeypatch):
    monkeypatch.setenv("API_KEY_HMAC_SECRET", "test-secret")
    get_settings.cache_clear()

    user = User(auth_provider="clerk", auth_user_id="auth-12", email="c@d.com")
    test_session.add(user)
    await test_session.flush()

    billing = Billing(
        user_id=user.id,
        stripe_customer_id="cus_456",
        status="active",
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

    stripe = _make_stripe()
    service = BillingService(test_session, stripe, get_settings())
    event = {
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_456",
                "customer": "cus_456",
                "status": "canceled",
                "items": {"data": [{"price": {"id": "price_new"}}]},
                "current_period_start": 3000,
                "current_period_end": 4000,
            }
        },
    }

    await service.handle_webhook_event(event)

    updated_billing = await test_session.get(Billing, user.id)
    assert updated_billing.status == "canceled"
    assert updated_billing.price_id == "price_new"

    updated_key = await test_session.get(ApiKey, api_key.id)
    assert updated_key.active is False
