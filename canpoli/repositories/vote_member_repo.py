"""Vote member repository."""

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from canpoli.models import VoteMember
from canpoli.repositories.base import BaseRepository


class VoteMemberRepository(BaseRepository[VoteMember]):
    """Repository for VoteMember queries."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, VoteMember)

    async def delete_by_vote_id(self, vote_id: int) -> None:
        await self.session.execute(
            delete(VoteMember).where(VoteMember.vote_id == vote_id)
        )

    async def list_by_vote_id(self, vote_id: int) -> list[VoteMember]:
        result = await self.session.execute(
            select(VoteMember).where(VoteMember.vote_id == vote_id)
        )
        return list(result.scalars().all())
