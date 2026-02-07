"""Vote repository."""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import Select

from canpoli.models import Vote
from canpoli.repositories.base import BaseRepository


class VoteRepository(BaseRepository[Vote]):
    """Repository for Vote queries."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Vote)

    def _apply_filters(
        self,
        query: Select,
        vote_date: date | None = None,
        decision: str | None = None,
        bill_number: str | None = None,
        parliament: int | None = None,
        session: int | None = None,
    ) -> Select:
        if vote_date is not None:
            query = query.where(Vote.vote_date == vote_date)
        if decision:
            query = query.where(Vote.decision == decision)
        if bill_number:
            query = query.where(Vote.bill_number == bill_number)
        if parliament is not None:
            query = query.where(Vote.parliament == parliament)
        if session is not None:
            query = query.where(Vote.session == session)
        return query

    async def list_with_filters(
        self,
        vote_date: date | None = None,
        decision: str | None = None,
        bill_number: str | None = None,
        parliament: int | None = None,
        session: int | None = None,
        include_members: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Vote]:
        query = select(Vote)
        if include_members:
            query = query.options(selectinload(Vote.members))
        query = self._apply_filters(query, vote_date, decision, bill_number, parliament, session)
        query = query.order_by(Vote.vote_date.desc().nullslast(), Vote.vote_number.desc())
        query = query.limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_with_filters(
        self,
        vote_date: date | None = None,
        decision: str | None = None,
        bill_number: str | None = None,
        parliament: int | None = None,
        session: int | None = None,
    ) -> int:
        query = select(func.count()).select_from(Vote)
        query = self._apply_filters(query, vote_date, decision, bill_number, parliament, session)
        result = await self.session.execute(query)
        return result.scalar_one()

    async def get_by_vote_number(
        self, vote_number: int, parliament: int | None, session: int | None
    ) -> Vote | None:
        result = await self.session.execute(
            select(Vote)
            .where(Vote.vote_number == vote_number)
            .where(Vote.parliament == parliament)
            .where(Vote.session == session)
        )
        return result.scalar_one_or_none()

    async def get_with_members(self, vote_id: int) -> Vote | None:
        result = await self.session.execute(
            select(Vote).options(selectinload(Vote.members)).where(Vote.id == vote_id)
        )
        return result.scalar_one_or_none()

    async def upsert(
        self,
        vote_number: int,
        parliament: int | None,
        session: int | None,
        **kwargs,
    ) -> Vote:
        result = await self.session.execute(
            select(Vote)
            .where(Vote.vote_number == vote_number)
            .where(Vote.parliament == parliament)
            .where(Vote.session == session)
        )
        existing = result.scalar_one_or_none()
        if existing:
            for key, value in kwargs.items():
                setattr(existing, key, value)
            return existing
        created = Vote(
            vote_number=vote_number,
            parliament=parliament,
            session=session,
            **kwargs,
        )
        self.session.add(created)
        await self.session.flush()
        return created
