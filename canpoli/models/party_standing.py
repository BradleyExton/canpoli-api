"""Party standing model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from canpoli.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from canpoli.models.party import Party


class PartyStanding(Base, TimestampMixin):
    """Party seat standings for a parliament/session."""

    __tablename__ = "party_standings"

    id: Mapped[int] = mapped_column(primary_key=True)
    party_id: Mapped[int | None] = mapped_column(ForeignKey("parties.id"))
    party_name: Mapped[str] = mapped_column(String(100), nullable=False)
    seat_count: Mapped[int] = mapped_column(nullable=False)

    as_of_date: Mapped[Date | None] = mapped_column(Date())
    parliament: Mapped[int | None] = mapped_column()
    session: Mapped[int | None] = mapped_column()

    source_url: Mapped[str | None] = mapped_column(String(500))

    party: Mapped[Party | None] = relationship()

    __table_args__ = (
        Index("ix_party_standings_party_name", "party_name"),
        Index("ix_party_standings_parl_session", "parliament", "session"),
    )

    def __repr__(self) -> str:
        return f"<PartyStanding {self.party_name}: {self.seat_count}>"
