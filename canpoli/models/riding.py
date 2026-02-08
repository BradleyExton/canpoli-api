"""Riding (electoral district) model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from canpoli.models.base import Base, TimestampMixin
from canpoli.models.geometry import Geometry

if TYPE_CHECKING:
    from canpoli.models.representative import Representative


class Riding(Base, TimestampMixin):
    """Federal electoral district (riding)."""

    __tablename__ = "ridings"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    province: Mapped[str] = mapped_column(String(50), nullable=False)
    fed_number: Mapped[int | None] = mapped_column()  # Elections Canada ID
    geom: Mapped[object | None] = mapped_column(
        Geometry("MULTIPOLYGON", 4326),
        nullable=True,
    )

    # Relationships
    representatives: Mapped[list[Representative]] = relationship(back_populates="riding")

    __table_args__ = (
        Index("ix_ridings_province", "province"),
        Index("ix_ridings_fed_number", "fed_number"),
        Index("ix_ridings_name", "name"),  # For get_or_create lookups
        Index("ix_ridings_name_province", "name", "province"),
    )

    def __repr__(self) -> str:
        return f"<Riding {self.name}, {self.province}>"
