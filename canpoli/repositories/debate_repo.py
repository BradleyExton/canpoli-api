"""Debate repository."""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import Select

from canpoli.models import Debate
from canpoli.repositories.base import BaseRepository


class DebateRepository(BaseRepository[Debate]):
    """Repository for Debate queries."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Debate)

    def _apply_filters(
        self,
        query: Select,
        debate_date: date | None = None,
        language: str | None = None,
        sitting: int | None = None,
        parliament: int | None = None,
        session: int | None = None,
    ) -> Select:
        if debate_date is not None:
            query = query.where(Debate.debate_date == debate_date)
        if language:
            query = query.where(Debate.language == language)
        if sitting is not None:
            query = query.where(Debate.sitting == sitting)
        if parliament is not None:
            query = query.where(Debate.parliament == parliament)
        if session is not None:
            query = query.where(Debate.session == session)
        return query

    async def list_with_filters(
        self,
        debate_date: date | None = None,
        language: str | None = None,
        sitting: int | None = None,
        parliament: int | None = None,
        session: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Debate]:
        query = select(Debate)
        query = self._apply_filters(query, debate_date, language, sitting, parliament, session)
        query = query.order_by(Debate.debate_date.desc().nullslast(), Debate.sitting.desc().nullslast())
        query = query.limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_with_filters(
        self,
        debate_date: date | None = None,
        language: str | None = None,
        sitting: int | None = None,
        parliament: int | None = None,
        session: int | None = None,
    ) -> int:
        query = select(func.count()).select_from(Debate)
        query = self._apply_filters(query, debate_date, language, sitting, parliament, session)
        result = await self.session.execute(query)
        return result.scalar_one()

    async def get_by_parl_session_sitting_lang(
        self,
        parliament: int | None,
        session: int | None,
        sitting: int | None,
        language: str | None,
    ) -> Debate | None:
        result = await self.session.execute(
            select(Debate)
            .where(Debate.parliament == parliament)
            .where(Debate.session == session)
            .where(Debate.sitting == sitting)
            .where(Debate.language == language)
        )
        return result.scalar_one_or_none()

    async def get_with_interventions(self, debate_id: int) -> Debate | None:
        result = await self.session.execute(
            select(Debate)
            .options(selectinload(Debate.interventions))
            .where(Debate.id == debate_id)
        )
        return result.scalar_one_or_none()

    async def upsert(
        self,
        parliament: int | None,
        session: int | None,
        sitting: int | None,
        language: str | None,
        **kwargs,
    ) -> Debate:
        result = await self.session.execute(
            select(Debate)
            .where(Debate.parliament == parliament)
            .where(Debate.session == session)
            .where(Debate.sitting == sitting)
            .where(Debate.language == language)
        )
        existing = result.scalar_one_or_none()
        if existing:
            for key, value in kwargs.items():
                setattr(existing, key, value)
            return existing
        created = Debate(
            parliament=parliament,
            session=session,
            sitting=sitting,
            language=language,
            **kwargs,
        )
        self.session.add(created)
        await self.session.flush()
        return created
