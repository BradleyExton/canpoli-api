"""Billing endpoints for Stripe Checkout and Portal."""

from datetime import datetime, timezone
from typing import Annotated

import anyio
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from canpoli.api_keys import generate_api_key
from canpoli.auth import get_current_user
from canpoli.config import get_settings
from canpoli.database import get_session
from canpoli.rate_limit import is_subscription_active
from canpoli.repositories import ApiKeyRepository, BillingRepository
from canpoli.redis_client import get_redis
from canpoli.schemas import CheckoutSessionResponse, PortalSessionResponse
from canpoli.stripe_client import get_stripe

router = APIRouter(prefix="/v1/billing", tags=["Billing"])


async def _stripe_call(func, *args, **kwargs):
    return await anyio.to_thread.run_sync(lambda: func(*args, **kwargs))


@router.post("/checkout", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    session: Annotated[AsyncSession, Depends(get_session)],
    user=Depends(get_current_user),
) -> CheckoutSessionResponse:
    """Create a Stripe Checkout session for subscriptions."""
    settings = get_settings()
    if not settings.stripe_price_id:
        raise HTTPException(status_code=500, detail="Stripe price is not configured")
    if not settings.stripe_checkout_success_url or not settings.stripe_checkout_cancel_url:
        raise HTTPException(status_code=500, detail="Checkout URLs are not configured")

    stripe = get_stripe()
    billing_repo = BillingRepository(session)
    billing = await billing_repo.get_by_user_id(user.id)
    if not billing or not billing.stripe_customer_id:
        customer = await _stripe_call(
            stripe.Customer.create,
            email=user.email,
            metadata={"user_id": user.id},
        )
        if not billing:
            billing = await billing_repo.create(
                user_id=user.id,
                stripe_customer_id=customer.id,
            )
        else:
            billing.stripe_customer_id = customer.id
            await session.flush()

    checkout = await _stripe_call(
        stripe.checkout.Session.create,
        mode="subscription",
        line_items=[{"price": settings.stripe_price_id, "quantity": 1}],
        success_url=settings.stripe_checkout_success_url,
        cancel_url=settings.stripe_checkout_cancel_url,
        customer=billing.stripe_customer_id,
        client_reference_id=user.id,
        metadata={"user_id": user.id},
    )

    return CheckoutSessionResponse(url=checkout.url)


@router.post("/portal", response_model=PortalSessionResponse)
async def create_portal_session(
    session: Annotated[AsyncSession, Depends(get_session)],
    user=Depends(get_current_user),
) -> PortalSessionResponse:
    """Create a Stripe billing portal session."""
    settings = get_settings()
    if not settings.stripe_portal_return_url:
        raise HTTPException(status_code=500, detail="Portal return URL is not configured")

    billing_repo = BillingRepository(session)
    billing = await billing_repo.get_by_user_id(user.id)
    if not billing or not billing.stripe_customer_id:
        raise HTTPException(status_code=404, detail="Stripe customer not found")

    stripe = get_stripe()
    portal = await _stripe_call(
        stripe.billing_portal.Session.create,
        customer=billing.stripe_customer_id,
        return_url=settings.stripe_portal_return_url,
    )

    return PortalSessionResponse(url=portal.url)


@router.post("/webhook")
async def stripe_webhook(request: Request, session: Annotated[AsyncSession, Depends(get_session)]):
    """Handle Stripe webhook events."""
    settings = get_settings()
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=500, detail="Stripe webhook secret not configured")
    if not settings.api_key_hmac_secret:
        raise HTTPException(status_code=500, detail="API key hashing not configured")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing Stripe signature")

    stripe = get_stripe()
    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=settings.stripe_webhook_secret,
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Stripe signature") from None

    event_type = event["type"]
    data_object = event["data"]["object"]

    billing_repo = BillingRepository(session)
    api_repo = ApiKeyRepository(session)

    if event_type == "checkout.session.completed":
        user_id = data_object.get("client_reference_id") or data_object.get("metadata", {}).get("user_id")
        if not user_id:
            return {"received": True}

        subscription_id = data_object.get("subscription")
        customer_id = data_object.get("customer")

        subscription = None
        if subscription_id:
            subscription = await _stripe_call(stripe.Subscription.retrieve, subscription_id)

        billing = await billing_repo.get_by_user_id(user_id)
        if not billing:
            billing = await billing_repo.create(user_id=user_id)

        billing.stripe_customer_id = customer_id
        billing.stripe_subscription_id = subscription_id
        if subscription:
            billing.status = subscription.get("status")
            billing.price_id = (
                subscription.get("items", {})
                .get("data", [{}])[0]
                .get("price", {})
                .get("id")
            )
            if subscription.get("current_period_start") is not None:
                billing.current_period_start = datetime.fromtimestamp(
                    subscription.get("current_period_start"), tz=timezone.utc
                )
            if subscription.get("current_period_end") is not None:
                billing.current_period_end = datetime.fromtimestamp(
                    subscription.get("current_period_end"), tz=timezone.utc
                )
        await session.flush()

        api_key = await api_repo.get_active_for_user(user_id)
        if not api_key:
            plaintext, prefix, key_hash = generate_api_key()
            api_key = await api_repo.create(
                user_id=user_id,
                key_prefix=prefix,
                key_hash=key_hash,
                active=is_subscription_active(billing.status),
            )
            redis = await get_redis()
            await redis.set(f"api_key_reveal:{user_id}", plaintext, ex=3600)
        else:
            api_key.active = is_subscription_active(billing.status)
            await session.flush()

    elif event_type in {"customer.subscription.updated", "customer.subscription.deleted"}:
        customer_id = data_object.get("customer")
        if not customer_id:
            return {"received": True}

        billing = await billing_repo.get_by_customer_id(customer_id)
        if not billing:
            return {"received": True}

        billing.stripe_subscription_id = data_object.get("id")
        billing.status = data_object.get("status")
        billing.price_id = (
            data_object.get("items", {})
            .get("data", [{}])[0]
            .get("price", {})
            .get("id")
        )
        if data_object.get("current_period_start") is not None:
            billing.current_period_start = datetime.fromtimestamp(
                data_object.get("current_period_start"), tz=timezone.utc
            )
        if data_object.get("current_period_end") is not None:
            billing.current_period_end = datetime.fromtimestamp(
                data_object.get("current_period_end"), tz=timezone.utc
            )
        await session.flush()

        api_key = await api_repo.get_active_for_user(billing.user_id)
        if api_key:
            api_key.active = is_subscription_active(billing.status)
            await session.flush()

    return {"received": True}
