"""Account endpoints for authenticated users."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from canpoli.auth import get_current_user
from canpoli.config import get_settings
from canpoli.database import get_session
from canpoli.rate_limit import get_usage_count
from canpoli.redis_client import get_redis
from canpoli.repositories import ApiKeyRepository, BillingRepository
from canpoli.schemas import ApiKeyResponse, ApiKeyRotateResponse, UsageResponse
from canpoli.services.api_key_service import ApiKeyService

router = APIRouter(prefix="/v1/account", tags=["Account"])


@router.get("/api-key", response_model=ApiKeyResponse)
async def get_api_key(
    session: Annotated[AsyncSession, Depends(get_session)],
    user=Depends(get_current_user),
) -> ApiKeyResponse:
    """Return the active API key (masked)."""
    redis = await get_redis()
    service = ApiKeyService(session, get_settings(), redis)
    return await service.get_api_key(user.id)


@router.post("/api-key/rotate", response_model=ApiKeyRotateResponse)
async def rotate_api_key(
    session: Annotated[AsyncSession, Depends(get_session)],
    user=Depends(get_current_user),
) -> ApiKeyRotateResponse:
    """Rotate the API key for an active subscriber."""
    service = ApiKeyService(session, get_settings(), None)
    return await service.rotate_api_key(user.id)


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
