"""Billing endpoints for Stripe Checkout and Portal."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from canpoli.auth import get_current_user
from canpoli.config import get_settings
from canpoli.database import get_session
from canpoli.schemas import CheckoutSessionResponse, PortalSessionResponse
from canpoli.services.billing_service import BillingService
from canpoli.stripe_client import get_stripe

router = APIRouter(prefix="/v1/billing", tags=["Billing"])


@router.post("/checkout", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    session: Annotated[AsyncSession, Depends(get_session)],
    user=Depends(get_current_user),
) -> CheckoutSessionResponse:
    """Create a Stripe Checkout session for subscriptions."""
    service = BillingService(session, get_stripe(), get_settings())
    return await service.create_checkout_session(user)


@router.post("/portal", response_model=PortalSessionResponse)
async def create_portal_session(
    session: Annotated[AsyncSession, Depends(get_session)],
    user=Depends(get_current_user),
) -> PortalSessionResponse:
    """Create a Stripe billing portal session."""
    service = BillingService(session, get_stripe(), get_settings())
    return await service.create_portal_session(user)


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

    service = BillingService(session, stripe, settings)
    await service.handle_webhook_event(event)

    return {"received": True}
