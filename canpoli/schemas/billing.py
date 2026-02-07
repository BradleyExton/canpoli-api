"""Schemas for billing endpoints."""

from pydantic import BaseModel


class CheckoutSessionResponse(BaseModel):
    """Checkout session response."""

    url: str


class PortalSessionResponse(BaseModel):
    """Billing portal response."""

    url: str
