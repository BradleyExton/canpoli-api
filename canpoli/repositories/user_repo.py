"""Repository for user accounts."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from canpoli.models.user import User
from canpoli.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """User repository with auth lookups."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, User)

    async def get_by_auth_user_id(self, auth_user_id: str) -> User | None:
        """Fetch user by auth provider user id."""
        result = await self.session.execute(select(User).where(User.auth_user_id == auth_user_id))
        return result.scalar_one_or_none()
