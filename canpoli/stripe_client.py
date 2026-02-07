"""Stripe client helper."""

import stripe

from canpoli.config import get_settings


def get_stripe() -> stripe:
    """Configure and return the Stripe module."""
    settings = get_settings()
    if not settings.stripe_secret_key:
        raise RuntimeError("STRIPE_SECRET_KEY is not configured")
    stripe.api_key = settings.stripe_secret_key
    return stripe
