"""Representative role repository."""

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import Select

from canpoli.models import Representative, RepresentativeRole
from canpoli.repositories.base import BaseRepository


class RepresentativeRoleRepository(BaseRepository[RepresentativeRole]):
    """Repository for RepresentativeRole queries."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, RepresentativeRole)

    def _apply_filters(
        self,
        query: Select,
        hoc_id: int | None = None,
        role_type: str | None = None,
        current: bool | None = None,
        parliament: int | None = None,
        session: int | None = None,
    ) -> Select:
        if hoc_id is not None:
            query = query.join(Representative).where(Representative.hoc_id == hoc_id)
        if role_type:
            query = query.where(RepresentativeRole.role_type == role_type)
        if current is not None:
            query = query.where(RepresentativeRole.is_current == current)
        if parliament is not None:
            query = query.where(RepresentativeRole.parliament == parliament)
        if session is not None:
            query = query.where(RepresentativeRole.session == session)
        return query

    async def list_with_filters(
        self,
        hoc_id: int | None = None,
        role_type: str | None = None,
        current: bool | None = None,
        parliament: int | None = None,
        session: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[RepresentativeRole]:
        query = select(RepresentativeRole).options(selectinload(RepresentativeRole.representative))
        query = self._apply_filters(query, hoc_id, role_type, current, parliament, session)
        query = query.order_by(RepresentativeRole.start_date.desc().nullslast())
        query = query.limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_with_filters(
        self,
        hoc_id: int | None = None,
        role_type: str | None = None,
        current: bool | None = None,
        parliament: int | None = None,
        session: int | None = None,
    ) -> int:
        query = select(func.count()).select_from(RepresentativeRole)
        query = self._apply_filters(query, hoc_id, role_type, current, parliament, session)
        result = await self.session.execute(query)
        return result.scalar_one()

    async def delete_by_representative_id(self, representative_id: int) -> None:
        await self.session.execute(
            delete(RepresentativeRole).where(
                RepresentativeRole.representative_id == representative_id
            )
        )

    async def list_current_for_representative(
        self, representative_id: int
    ) -> list[RepresentativeRole]:
        result = await self.session.execute(
            select(RepresentativeRole)
            .where(RepresentativeRole.representative_id == representative_id)
            .where(RepresentativeRole.is_current == True)  # noqa: E712
            .order_by(RepresentativeRole.start_date.desc().nullslast())
        )
        return list(result.scalars().all())
