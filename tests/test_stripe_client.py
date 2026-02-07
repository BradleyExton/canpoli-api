"""Tests for Stripe client helper."""

import pytest

from canpoli.config import get_settings
from canpoli.stripe_client import get_stripe
import stripe as stripe_module


def test_get_stripe_missing_secret(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "")
    get_settings.cache_clear()

    with pytest.raises(RuntimeError, match="STRIPE_SECRET_KEY"):
        get_stripe()


def test_get_stripe_sets_api_key(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_123")
    get_settings.cache_clear()

    stripe = get_stripe()
    assert stripe is stripe_module
    assert stripe.api_key == "sk_test_123"
