"""Schemas for account endpoints."""

from datetime import datetime

from pydantic import BaseModel


class ApiKeyResponse(BaseModel):
    """Masked API key details."""

    api_key: str | None = None
    key_prefix: str
    masked_key: str
    active: bool
    created_at: datetime
    revoked_at: datetime | None = None
    last_used_at: datetime | None = None


class ApiKeyRotateResponse(BaseModel):
    """Returned when rotating a key."""

    api_key: str
    key_prefix: str
    created_at: datetime


class UsageResponse(BaseModel):
    """Usage counts for current billing period."""

    usage_count: int
    period_start: datetime | None
    period_end: datetime | None
    limit_per_minute: int
