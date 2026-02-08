"""Riding repository."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from canpoli.models import Riding
from canpoli.repositories.base import BaseRepository


class RidingRepository(BaseRepository[Riding]):
    """Repository for Riding queries."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Riding)

    async def get_or_create(
        self,
        name: str,
        province: str,
        fed_number: int | None = None,
    ) -> Riding:
        """Get existing riding or create new one."""
        result = await self.session.execute(
            select(Riding).where(Riding.name == name).where(Riding.province == province)
        )
        riding = result.scalar_one_or_none()

        if not riding:
            riding = Riding(name=name, province=province, fed_number=fed_number)
            self.session.add(riding)
            await self.session.flush()

        return riding

    async def get_by_province(
        self,
        province: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Riding]:
        """Get ridings filtered by province."""
        result = await self.session.execute(
            select(Riding)
            .where(Riding.province == province)
            .order_by(Riding.name)
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_by_name_and_province(
        self,
        name: str,
        province: str,
    ) -> Riding | None:
        """Get a riding by name and province (case-insensitive)."""
        result = await self.session.execute(
            select(Riding)
            .where(func.lower(Riding.name) == name.lower())
            .where(func.lower(Riding.province) == province.lower())
        )
        return result.scalar_one_or_none()

    async def get_by_point(self, lat: float, lng: float) -> Riding | None:
        """Get a riding containing the given point (lat/lng)."""
        point = func.ST_SetSRID(func.ST_MakePoint(lng, lat), 4326)
        result = await self.session.execute(
            select(Riding)
            .where(Riding.geom.is_not(None))
            .where(func.ST_Contains(Riding.geom, point))
        )
        return result.scalar_one_or_none()

    async def count_by_province(self, province: str) -> int:
        """Count ridings in a province."""
        result = await self.session.execute(
            select(func.count()).select_from(Riding).where(Riding.province == province)
        )
        return result.scalar_one()
