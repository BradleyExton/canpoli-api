"""Party model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from canpoli.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from canpoli.models.representative import Representative


class Party(Base, TimestampMixin):
    """Political party (Liberal, Conservative, NDP, etc.)."""

    __tablename__ = "parties"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    short_name: Mapped[str | None] = mapped_column(String(20))  # "LPC", "CPC"
    color: Mapped[str | None] = mapped_column(String(7))  # Hex color "#D71920"

    # Relationships
    representatives: Mapped[list[Representative]] = relationship(back_populates="party")

    __table_args__ = (
        # Explicit index for name lookups (unique constraint also creates one)
        Index("ix_parties_name", "name"),
    )

    def __repr__(self) -> str:
        return f"<Party {self.name}>"
