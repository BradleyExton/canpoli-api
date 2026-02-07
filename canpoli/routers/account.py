"""Account endpoints for authenticated users."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from canpoli.api_keys import generate_api_key, mask_api_key
from canpoli.auth import get_current_user
from canpoli.config import get_settings
from canpoli.database import get_session
from canpoli.rate_limit import get_usage_count, is_subscription_active
from canpoli.redis_client import get_redis
from canpoli.repositories import ApiKeyRepository, BillingRepository
from canpoli.schemas import ApiKeyResponse, ApiKeyRotateResponse, UsageResponse

router = APIRouter(prefix="/v1/account", tags=["Account"])


@router.get("/api-key", response_model=ApiKeyResponse)
async def get_api_key(
    session: Annotated[AsyncSession, Depends(get_session)],
    user=Depends(get_current_user),
) -> ApiKeyResponse:
    """Return the active API key (masked)."""
    api_repo = ApiKeyRepository(session)
    api_key = await api_repo.get_active_for_user(user.id)
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    redis = await get_redis()
    reveal_key = f"api_key_reveal:{user.id}"
    plaintext = await redis.get(reveal_key)
    if plaintext:
        await redis.delete(reveal_key)

    return ApiKeyResponse(
        api_key=plaintext,
        key_prefix=api_key.key_prefix,
        masked_key=mask_api_key(api_key.key_prefix),
        active=api_key.active,
        created_at=api_key.created_at,
        revoked_at=api_key.revoked_at,
        last_used_at=api_key.last_used_at,
    )


@router.post("/api-key/rotate", response_model=ApiKeyRotateResponse)
async def rotate_api_key(
    session: Annotated[AsyncSession, Depends(get_session)],
    user=Depends(get_current_user),
) -> ApiKeyRotateResponse:
    """Rotate the API key for an active subscriber."""
    settings = get_settings()
    if not settings.api_key_hmac_secret:
        raise HTTPException(status_code=500, detail="API key hashing not configured")

    billing_repo = BillingRepository(session)
    billing = await billing_repo.get_by_user_id(user.id)
    if not billing or not is_subscription_active(billing.status):
        raise HTTPException(status_code=403, detail="Subscription inactive")

    api_repo = ApiKeyRepository(session)
    await api_repo.deactivate_for_user(user.id)

    plaintext, prefix, key_hash = generate_api_key()
    new_key = await api_repo.create(
        user_id=user.id,
        key_prefix=prefix,
        key_hash=key_hash,
        active=True,
    )

    return ApiKeyRotateResponse(
        api_key=plaintext,
        key_prefix=prefix,
        created_at=new_key.created_at,
    )


@router.get("/usage", response_model=UsageResponse)
async def get_usage(
    session: Annotated[AsyncSession, Depends(get_session)],
    user=Depends(get_current_user),
) -> UsageResponse:
    """Return usage counts for the current billing period."""
    billing_repo = BillingRepository(session)
    billing = await billing_repo.get_by_user_id(user.id)
    if not billing or not billing.current_period_start:
        raise HTTPException(status_code=404, detail="No active billing period")

    api_repo = ApiKeyRepository(session)
    api_key = await api_repo.get_active_for_user(user.id)
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    usage_count = await get_usage_count(api_key.id, billing.current_period_start)
    settings = get_settings()

    return UsageResponse(
        usage_count=usage_count,
        period_start=billing.current_period_start,
        period_end=billing.current_period_end,
        limit_per_minute=settings.paid_rate_limit_per_minute,
    )
