"""Party standings repository."""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from canpoli.models import PartyStanding
from canpoli.repositories.base import BaseRepository


class PartyStandingRepository(BaseRepository[PartyStanding]):
    """Repository for PartyStanding queries."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, PartyStanding)

    def _apply_filters(
        self,
        query: Select,
        parliament: int | None = None,
        session: int | None = None,
        as_of_date: date | None = None,
        party_name: str | None = None,
    ) -> Select:
        if parliament is not None:
            query = query.where(PartyStanding.parliament == parliament)
        if session is not None:
            query = query.where(PartyStanding.session == session)
        if as_of_date is not None:
            query = query.where(PartyStanding.as_of_date == as_of_date)
        if party_name:
            query = query.where(PartyStanding.party_name == party_name)
        return query

    async def list_with_filters(
        self,
        parliament: int | None = None,
        session: int | None = None,
        as_of_date: date | None = None,
        party_name: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PartyStanding]:
        query = select(PartyStanding)
        query = self._apply_filters(query, parliament, session, as_of_date, party_name)
        query = query.order_by(PartyStanding.seat_count.desc())
        query = query.limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_with_filters(
        self,
        parliament: int | None = None,
        session: int | None = None,
        as_of_date: date | None = None,
        party_name: str | None = None,
    ) -> int:
        query = select(func.count()).select_from(PartyStanding)
        query = self._apply_filters(query, parliament, session, as_of_date, party_name)
        result = await self.session.execute(query)
        return result.scalar_one()

    async def get_latest_as_of_date(
        self,
        parliament: int | None = None,
        session: int | None = None,
    ) -> date | None:
        query = select(func.max(PartyStanding.as_of_date))
        if parliament is not None:
            query = query.where(PartyStanding.parliament == parliament)
        if session is not None:
            query = query.where(PartyStanding.session == session)
        result = await self.session.execute(query)
        return result.scalar_one()

    async def upsert(
        self,
        party_name: str,
        parliament: int | None,
        session: int | None,
        as_of_date: date | None,
        **kwargs,
    ) -> PartyStanding:
        result = await self.session.execute(
            select(PartyStanding)
            .where(PartyStanding.party_name == party_name)
            .where(PartyStanding.parliament == parliament)
            .where(PartyStanding.session == session)
            .where(PartyStanding.as_of_date == as_of_date)
        )
        existing = result.scalar_one_or_none()
        if existing:
            for key, value in kwargs.items():
                setattr(existing, key, value)
            return existing
        created = PartyStanding(
            party_name=party_name,
            parliament=parliament,
            session=session,
            as_of_date=as_of_date,
            **kwargs,
        )
        self.session.add(created)
        await self.session.flush()
        return created
