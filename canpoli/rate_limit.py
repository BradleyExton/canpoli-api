"""Rate limiting and usage tracking."""

from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from canpoli.api_keys import hash_api_key
from canpoli.config import get_settings
from canpoli.database import get_session
from canpoli.redis_client import get_redis
from canpoli.repositories import ApiKeyRepository, BillingRepository


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def is_subscription_active(status: str | None) -> bool:
    """Return True for subscription statuses that allow access."""
    return status in {"active", "trialing"}


async def _apply_rate_limit(identity: str, limit: int) -> None:
    redis = await get_redis()
    now = datetime.now(timezone.utc)
    window = int(now.timestamp() // 60)
    key = f"ratelimit:{identity}:{window}"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, 60)
    if count > limit:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")


async def rate_limit_dependency(
    request: Request,
    session: AsyncSession = Depends(get_session),
    api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    """Rate limit /v1 data endpoints by IP or API key."""
    settings = get_settings()

    if api_key:
        api_key = api_key.strip()
        if not api_key:
            api_key = None

    if api_key:
        if not settings.api_key_hmac_secret:
            raise HTTPException(status_code=500, detail="API key hashing not configured")

        repo = ApiKeyRepository(session)
        key_hash = hash_api_key(api_key, settings.api_key_hmac_secret)
        api_key_record = await repo.get_by_hash(key_hash)
        if not api_key_record:
            raise HTTPException(status_code=401, detail="Invalid API key")
        if not api_key_record.active:
            raise HTTPException(status_code=403, detail="API key inactive")

        billing_repo = BillingRepository(session)
        billing = await billing_repo.get_by_user_id(api_key_record.user_id)
        if not billing or not is_subscription_active(billing.status):
            raise HTTPException(status_code=403, detail="Subscription inactive")

        await _apply_rate_limit(
            identity=f"key:{api_key_record.id}",
            limit=settings.paid_rate_limit_per_minute,
        )

        request.state.api_key_id = api_key_record.id
        if billing.current_period_start:
            request.state.usage_period_start = billing.current_period_start
        if billing.current_period_end:
            request.state.usage_period_end = billing.current_period_end
        return

    identity = f"ip:{_client_ip(request)}"
    await _apply_rate_limit(identity=identity, limit=settings.free_rate_limit_per_minute)


async def increment_usage(request: Request) -> None:
    """Increment usage counters for paid API keys."""
    api_key_id = getattr(request.state, "api_key_id", None)
    if not api_key_id:
        return

    period_start = getattr(request.state, "usage_period_start", None)
    if not period_start:
        return

    period_end = getattr(request.state, "usage_period_end", None)
    period_start_ts = int(period_start.timestamp())
    now_ts = int(datetime.now(timezone.utc).timestamp())
    ttl = 60 * 60 * 24 * 35
    if period_end:
        ttl = max(60, int(period_end.timestamp()) - now_ts + 86400)

    redis = await get_redis()
    key = f"usage:{api_key_id}:{period_start_ts}"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, ttl)


async def get_usage_count(api_key_id: str, period_start: datetime) -> int:
    """Fetch usage counter for a period."""
    redis = await get_redis()
    period_start_ts = int(period_start.timestamp())
    key = f"usage:{api_key_id}:{period_start_ts}"
    value = await redis.get(key)
    if value is None:
        return 0
    return int(value)
