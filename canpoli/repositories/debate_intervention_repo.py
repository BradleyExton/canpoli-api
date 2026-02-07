"""Debate intervention repository."""

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from canpoli.models import DebateIntervention
from canpoli.repositories.base import BaseRepository


class DebateInterventionRepository(BaseRepository[DebateIntervention]):
    """Repository for DebateIntervention queries."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, DebateIntervention)

    async def delete_by_debate_id(self, debate_id: int) -> None:
        await self.session.execute(
            delete(DebateIntervention).where(DebateIntervention.debate_id == debate_id)
        )

    async def list_by_debate_id(self, debate_id: int) -> list[DebateIntervention]:
        result = await self.session.execute(
            select(DebateIntervention)
            .where(DebateIntervention.debate_id == debate_id)
            .order_by(DebateIntervention.sequence)
        )
        return list(result.scalars().all())
