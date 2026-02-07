"""Service for API key workflows."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from canpoli.api_keys import generate_api_key, mask_api_key
from canpoli.config import Settings
from canpoli.rate_limit import is_subscription_active
from canpoli.repositories import ApiKeyRepository, BillingRepository
from canpoli.schemas import ApiKeyResponse, ApiKeyRotateResponse


class ApiKeyService:
    """Service for API key retrieval and rotation."""

    def __init__(self, session: AsyncSession, settings: Settings, redis_client: Any | None):
        self.session = session
        self.settings = settings
        self.redis = redis_client
        self.api_repo = ApiKeyRepository(session)
        self.billing_repo = BillingRepository(session)

    async def get_api_key(self, user_id: str) -> ApiKeyResponse:
        """Return the active API key (masked), optionally including one-time reveal."""
        api_key = await self.api_repo.get_active_for_user(user_id)
        if not api_key:
            raise HTTPException(status_code=404, detail="API key not found")

        plaintext = None
        if self.redis is not None:
            reveal_key = f"api_key_reveal:{user_id}"
            plaintext = await self.redis.get(reveal_key)
            if plaintext:
                await self.redis.delete(reveal_key)

        return ApiKeyResponse(
            api_key=plaintext,
            key_prefix=api_key.key_prefix,
            masked_key=mask_api_key(api_key.key_prefix),
            active=api_key.active,
            created_at=api_key.created_at,
            revoked_at=api_key.revoked_at,
            last_used_at=api_key.last_used_at,
        )

    async def rotate_api_key(self, user_id: str) -> ApiKeyRotateResponse:
        """Rotate the API key for an active subscriber."""
        if not self.settings.api_key_hmac_secret:
            raise HTTPException(status_code=500, detail="API key hashing not configured")

        billing = await self.billing_repo.get_by_user_id(user_id)
        if not billing or not is_subscription_active(billing.status):
            raise HTTPException(status_code=403, detail="Subscription inactive")

        await self.api_repo.deactivate_for_user(user_id)

        plaintext, prefix, key_hash = generate_api_key()
        new_key = await self.api_repo.create(
            user_id=user_id,
            key_prefix=prefix,
            key_hash=key_hash,
            active=True,
        )

        return ApiKeyRotateResponse(
            api_key=plaintext,
            key_prefix=prefix,
            created_at=new_key.created_at,
        )

    async def activate_or_create_for_user(self, user_id: str, status: str | None) -> None:
        """Create an API key if missing, or update active status."""
        api_key = await self.api_repo.get_active_for_user(user_id)
        active = is_subscription_active(status)

        if not api_key:
            plaintext, prefix, key_hash = generate_api_key()
            api_key = await self.api_repo.create(
                user_id=user_id,
                key_prefix=prefix,
                key_hash=key_hash,
                active=active,
            )
            if self.redis is not None:
                await self.redis.set(f"api_key_reveal:{user_id}", plaintext, ex=3600)
            return

        api_key.active = active
        await self.session.flush()

    async def set_active_for_user_if_exists(self, user_id: str, status: str | None) -> None:
        """Update active status for an existing key without creating new keys."""
        api_key = await self.api_repo.get_active_for_user(user_id)
        if not api_key:
            return
        api_key.active = is_subscription_active(status)
        await self.session.flush()
