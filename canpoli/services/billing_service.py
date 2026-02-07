"""Service for billing workflows."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import anyio
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from canpoli.config import Settings
from canpoli.redis_client import get_redis
from canpoli.repositories import BillingRepository
from canpoli.schemas import CheckoutSessionResponse, PortalSessionResponse
from canpoli.services.api_key_service import ApiKeyService


class BillingService:
    """Service for Stripe billing workflows."""

    def __init__(self, session: AsyncSession, stripe_client: Any, settings: Settings):
        self.session = session
        self.stripe = stripe_client
        self.settings = settings
        self.billing_repo = BillingRepository(session)

    async def _stripe_call(self, func, *args, **kwargs):
        return await anyio.to_thread.run_sync(lambda: func(*args, **kwargs))

    async def _ensure_customer(self, user) -> Any:
        billing = await self.billing_repo.get_by_user_id(user.id)
        if not billing or not billing.stripe_customer_id:
            customer = await self._stripe_call(
                self.stripe.Customer.create,
                email=user.email,
                metadata={"user_id": user.id},
            )
            if not billing:
                billing = await self.billing_repo.create(
                    user_id=user.id,
                    stripe_customer_id=customer.id,
                )
            else:
                billing.stripe_customer_id = customer.id
                await self.session.flush()
        return billing

    async def create_checkout_session(self, user) -> CheckoutSessionResponse:
        """Create a Stripe Checkout session for subscriptions."""
        if not self.settings.stripe_price_id:
            raise HTTPException(status_code=500, detail="Stripe price is not configured")
        if not self.settings.stripe_checkout_success_url or not self.settings.stripe_checkout_cancel_url:
            raise HTTPException(status_code=500, detail="Checkout URLs are not configured")

        billing = await self._ensure_customer(user)
        checkout = await self._stripe_call(
            self.stripe.checkout.Session.create,
            mode="subscription",
            line_items=[{"price": self.settings.stripe_price_id, "quantity": 1}],
            success_url=self.settings.stripe_checkout_success_url,
            cancel_url=self.settings.stripe_checkout_cancel_url,
            customer=billing.stripe_customer_id,
            client_reference_id=user.id,
            metadata={"user_id": user.id},
        )

        return CheckoutSessionResponse(url=checkout.url)

    async def create_portal_session(self, user) -> PortalSessionResponse:
        """Create a Stripe billing portal session."""
        if not self.settings.stripe_portal_return_url:
            raise HTTPException(status_code=500, detail="Portal return URL is not configured")

        billing = await self.billing_repo.get_by_user_id(user.id)
        if not billing or not billing.stripe_customer_id:
            raise HTTPException(status_code=404, detail="Stripe customer not found")

        portal = await self._stripe_call(
            self.stripe.billing_portal.Session.create,
            customer=billing.stripe_customer_id,
            return_url=self.settings.stripe_portal_return_url,
        )

        return PortalSessionResponse(url=portal.url)

    async def handle_webhook_event(self, event: dict[str, Any]) -> None:
        """Handle Stripe webhook events."""
        event_type = event["type"]
        data_object = event["data"]["object"]

        if event_type == "checkout.session.completed":
            user_id = data_object.get("client_reference_id") or data_object.get("metadata", {}).get("user_id")
            if not user_id:
                return

            subscription_id = data_object.get("subscription")
            customer_id = data_object.get("customer")

            subscription = None
            if subscription_id:
                subscription = await self._stripe_call(self.stripe.Subscription.retrieve, subscription_id)

            billing = await self.billing_repo.get_by_user_id(user_id)
            if not billing:
                billing = await self.billing_repo.create(user_id=user_id)

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
            await self.session.flush()

            redis = await get_redis()
            api_key_service = ApiKeyService(self.session, self.settings, redis)
            await api_key_service.activate_or_create_for_user(user_id, billing.status)
            return

        if event_type in {"customer.subscription.updated", "customer.subscription.deleted"}:
            customer_id = data_object.get("customer")
            if not customer_id:
                return

            billing = await self.billing_repo.get_by_customer_id(customer_id)
            if not billing:
                return

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
            await self.session.flush()

            api_key_service = ApiKeyService(self.session, self.settings, None)
            await api_key_service.set_active_for_user_if_exists(billing.user_id, billing.status)
