"""House officer expenditure repository."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from canpoli.models import HouseOfficerExpenditure
from canpoli.repositories.base import BaseRepository


class HouseOfficerExpenditureRepository(BaseRepository[HouseOfficerExpenditure]):
    """Repository for HouseOfficerExpenditure queries."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, HouseOfficerExpenditure)

    def _apply_filters(
        self,
        query: Select,
        fiscal_year: str | None = None,
        category: str | None = None,
    ) -> Select:
        if fiscal_year:
            query = query.where(HouseOfficerExpenditure.fiscal_year == fiscal_year)
        if category:
            query = query.where(HouseOfficerExpenditure.category == category)
        return query

    async def list_with_filters(
        self,
        fiscal_year: str | None = None,
        category: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[HouseOfficerExpenditure]:
        query = select(HouseOfficerExpenditure)
        query = self._apply_filters(query, fiscal_year, category)
        query = query.order_by(HouseOfficerExpenditure.period_start.desc().nullslast())
        query = query.limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_with_filters(
        self,
        fiscal_year: str | None = None,
        category: str | None = None,
    ) -> int:
        query = select(func.count()).select_from(HouseOfficerExpenditure)
        query = self._apply_filters(query, fiscal_year, category)
        result = await self.session.execute(query)
        return result.scalar_one()
