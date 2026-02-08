"""Repository for API keys."""

from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from canpoli.models.api_key import ApiKey
from canpoli.repositories.base import BaseRepository


class ApiKeyRepository(BaseRepository[ApiKey]):
    """API key repository with lookup helpers."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, ApiKey)

    async def get_by_hash(self, key_hash: str) -> ApiKey | None:
        """Fetch API key by hash."""
        result = await self.session.execute(select(ApiKey).where(ApiKey.key_hash == key_hash))
        return result.scalar_one_or_none()

    async def get_active_for_user(self, user_id: str) -> ApiKey | None:
        """Fetch active key for a user."""
        result = await self.session.execute(
            select(ApiKey).where(ApiKey.user_id == user_id, ApiKey.active.is_(True))
        )
        return result.scalar_one_or_none()

    async def deactivate_for_user(self, user_id: str) -> None:
        """Deactivate all keys for a user."""
        now = datetime.now(timezone.utc)
        await self.session.execute(
            update(ApiKey)
            .where(ApiKey.user_id == user_id, ApiKey.active.is_(True))
            .values(active=False, revoked_at=now)
        )
