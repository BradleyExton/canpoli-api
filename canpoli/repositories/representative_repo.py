"""Representative repository."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import Select

from canpoli.models import Party, Representative, Riding
from canpoli.repositories.base import BaseRepository


class RepresentativeRepository(BaseRepository[Representative]):
    """Repository for Representative queries."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Representative)

    def _apply_filters(
        self,
        query: Select,
        province: str | None = None,
        party: str | None = None,
    ) -> Select:
        """Apply common filters to a query.

        Args:
            query: Base SQLAlchemy select query
            province: Filter by province name
            party: Filter by party name

        Returns:
            Query with filters applied
        """
        query = query.where(Representative.is_active == True)  # noqa: E712

        if province:
            query = query.join(Representative.riding).where(Riding.province == province)

        if party:
            query = query.join(Representative.party).where(Party.name == party)

        return query

    async def get_by_hoc_id(self, hoc_id: int) -> Representative | None:
        """Get representative by House of Commons ID with relations."""
        result = await self.session.execute(
            select(Representative)
            .options(
                selectinload(Representative.party),
                selectinload(Representative.riding),
            )
            .where(Representative.hoc_id == hoc_id)
        )
        return result.scalar_one_or_none()

    async def get_all_with_filters(
        self,
        province: str | None = None,
        party: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Representative]:
        """Get representatives with optional filters and relations."""
        query = select(Representative).options(
            selectinload(Representative.party),
            selectinload(Representative.riding),
        )
        query = self._apply_filters(query, province, party)
        query = query.order_by(Representative.name).limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_with_filters(
        self,
        province: str | None = None,
        party: str | None = None,
    ) -> int:
        """Count representatives with filters."""
        query = select(func.count()).select_from(Representative)
        query = self._apply_filters(query, province, party)

        result = await self.session.execute(query)
        return result.scalar_one()

    async def upsert_by_hoc_id(self, hoc_id: int, **kwargs) -> Representative:
        """Insert or update a representative by House of Commons ID."""
        result = await self.session.execute(
            select(Representative).where(Representative.hoc_id == hoc_id)
        )
        rep = result.scalar_one_or_none()

        if rep:
            for key, value in kwargs.items():
                setattr(rep, key, value)
        else:
            rep = Representative(hoc_id=hoc_id, **kwargs)
            self.session.add(rep)

        await self.session.flush()
        return rep

    async def get_by_riding_id(self, riding_id: int) -> Representative | None:
        """Get active representative for a riding with all relations."""
        result = await self.session.execute(
            select(Representative)
            .options(
                selectinload(Representative.party),
                selectinload(Representative.riding),  # Added for consistency
            )
            .where(Representative.riding_id == riding_id)
            .where(Representative.is_active == True)  # noqa: E712
        )
        return result.scalar_one_or_none()
