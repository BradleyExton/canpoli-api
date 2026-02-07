"""Petition repository."""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from canpoli.models import Petition
from canpoli.repositories.base import BaseRepository


class PetitionRepository(BaseRepository[Petition]):
    """Repository for Petition queries."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Petition)

    def _apply_filters(
        self,
        query: Select,
        status: str | None = None,
        sponsor_hoc_id: int | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        parliament: int | None = None,
        session: int | None = None,
    ) -> Select:
        if status:
            query = query.where(Petition.status == status)
        if sponsor_hoc_id is not None:
            query = query.where(Petition.sponsor_hoc_id == sponsor_hoc_id)
        if from_date is not None:
            query = query.where(Petition.presentation_date >= from_date)
        if to_date is not None:
            query = query.where(Petition.presentation_date <= to_date)
        if parliament is not None:
            query = query.where(Petition.parliament == parliament)
        if session is not None:
            query = query.where(Petition.session == session)
        return query

    async def list_with_filters(
        self,
        status: str | None = None,
        sponsor_hoc_id: int | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        parliament: int | None = None,
        session: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Petition]:
        query = select(Petition)
        query = self._apply_filters(
            query,
            status,
            sponsor_hoc_id,
            from_date,
            to_date,
            parliament,
            session,
        )
        query = query.order_by(Petition.presentation_date.desc().nullslast())
        query = query.limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_with_filters(
        self,
        status: str | None = None,
        sponsor_hoc_id: int | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        parliament: int | None = None,
        session: int | None = None,
    ) -> int:
        query = select(func.count()).select_from(Petition)
        query = self._apply_filters(
            query,
            status,
            sponsor_hoc_id,
            from_date,
            to_date,
            parliament,
            session,
        )
        result = await self.session.execute(query)
        return result.scalar_one()

    async def upsert(
        self,
        petition_number: str,
        **kwargs,
    ) -> Petition:
        result = await self.session.execute(
            select(Petition).where(Petition.petition_number == petition_number)
        )
        existing = result.scalar_one_or_none()
        if existing:
            for key, value in kwargs.items():
                setattr(existing, key, value)
            return existing
        created = Petition(petition_number=petition_number, **kwargs)
        self.session.add(created)
        await self.session.flush()
        return created
