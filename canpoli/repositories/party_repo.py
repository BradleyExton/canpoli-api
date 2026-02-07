"""Party repository."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from canpoli.models import Party
from canpoli.repositories.base import BaseRepository


class PartyRepository(BaseRepository[Party]):
    """Repository for Party queries."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Party)

    async def get_or_create(
        self,
        name: str,
        short_name: str | None = None,
        color: str | None = None,
    ) -> Party:
        """Get existing party or create new one."""
        result = await self.session.execute(select(Party).where(Party.name == name))
        party = result.scalar_one_or_none()

        if not party:
            party = Party(name=name, short_name=short_name, color=color)
            self.session.add(party)
            await self.session.flush()

        return party

    async def get_by_name(self, name: str) -> Party | None:
        """Get party by name."""
        result = await self.session.execute(select(Party).where(Party.name == name))
        return result.scalar_one_or_none()
