"""Member expenditure repository."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from canpoli.models import MemberExpenditure
from canpoli.repositories.base import BaseRepository


class MemberExpenditureRepository(BaseRepository[MemberExpenditure]):
    """Repository for MemberExpenditure queries."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, MemberExpenditure)

    def _apply_filters(
        self,
        query: Select,
        hoc_id: int | None = None,
        representative_id: int | None = None,
        fiscal_year: str | None = None,
        category: str | None = None,
    ) -> Select:
        if hoc_id is not None:
            query = query.where(MemberExpenditure.hoc_id == hoc_id)
        if representative_id is not None:
            query = query.where(MemberExpenditure.representative_id == representative_id)
        if fiscal_year:
            query = query.where(MemberExpenditure.fiscal_year == fiscal_year)
        if category:
            query = query.where(MemberExpenditure.category == category)
        return query

    async def list_with_filters(
        self,
        hoc_id: int | None = None,
        representative_id: int | None = None,
        fiscal_year: str | None = None,
        category: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[MemberExpenditure]:
        query = select(MemberExpenditure)
        query = self._apply_filters(query, hoc_id, representative_id, fiscal_year, category)
        query = query.order_by(MemberExpenditure.period_start.desc().nullslast())
        query = query.limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_with_filters(
        self,
        hoc_id: int | None = None,
        representative_id: int | None = None,
        fiscal_year: str | None = None,
        category: str | None = None,
    ) -> int:
        query = select(func.count()).select_from(MemberExpenditure)
        query = self._apply_filters(query, hoc_id, representative_id, fiscal_year, category)
        result = await self.session.execute(query)
        return result.scalar_one()
