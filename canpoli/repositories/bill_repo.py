"""Bill repository."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from canpoli.models import Bill
from canpoli.repositories.base import BaseRepository


class BillRepository(BaseRepository[Bill]):
    """Repository for Bill queries."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Bill)

    def _apply_filters(
        self,
        query: Select,
        bill_number: str | None = None,
        status: str | None = None,
        sponsor_hoc_id: int | None = None,
        updated_since: datetime | None = None,
        parliament: int | None = None,
        session: int | None = None,
    ) -> Select:
        if bill_number:
            query = query.where(Bill.bill_number == bill_number)
        if status:
            query = query.where(Bill.status == status)
        if sponsor_hoc_id is not None:
            query = query.where(Bill.sponsor_hoc_id == sponsor_hoc_id)
        if updated_since is not None:
            query = query.where(Bill.latest_activity_date >= updated_since)
        if parliament is not None:
            query = query.where(Bill.parliament == parliament)
        if session is not None:
            query = query.where(Bill.session == session)
        return query

    async def list_with_filters(
        self,
        bill_number: str | None = None,
        status: str | None = None,
        sponsor_hoc_id: int | None = None,
        updated_since: datetime | None = None,
        parliament: int | None = None,
        session: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Bill]:
        query = select(Bill)
        query = self._apply_filters(
            query,
            bill_number,
            status,
            sponsor_hoc_id,
            updated_since,
            parliament,
            session,
        )
        query = query.order_by(Bill.latest_activity_date.desc().nullslast())
        query = query.limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_with_filters(
        self,
        bill_number: str | None = None,
        status: str | None = None,
        sponsor_hoc_id: int | None = None,
        updated_since: datetime | None = None,
        parliament: int | None = None,
        session: int | None = None,
    ) -> int:
        query = select(func.count()).select_from(Bill)
        query = self._apply_filters(
            query,
            bill_number,
            status,
            sponsor_hoc_id,
            updated_since,
            parliament,
            session,
        )
        result = await self.session.execute(query)
        return result.scalar_one()

    async def upsert(
        self,
        bill_number: str,
        parliament: int | None,
        session: int | None,
        **kwargs,
    ) -> Bill:
        result = await self.session.execute(
            select(Bill)
            .where(Bill.bill_number == bill_number)
            .where(Bill.parliament == parliament)
            .where(Bill.session == session)
        )
        existing = result.scalar_one_or_none()
        if existing:
            for key, value in kwargs.items():
                setattr(existing, key, value)
            return existing
        created = Bill(
            bill_number=bill_number,
            parliament=parliament,
            session=session,
            **kwargs,
        )
        self.session.add(created)
        await self.session.flush()
        return created
