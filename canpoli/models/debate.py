"""Debate (Hansard) model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Date, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from canpoli.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from canpoli.models.debate_intervention import DebateIntervention


class Debate(Base, TimestampMixin):
    """Hansard debate metadata."""

    __tablename__ = "debates"

    id: Mapped[int] = mapped_column(primary_key=True)

    parliament: Mapped[int | None] = mapped_column()
    session: Mapped[int | None] = mapped_column()
    sitting: Mapped[int | None] = mapped_column()

    debate_date: Mapped[Date | None] = mapped_column(Date())
    language: Mapped[str | None] = mapped_column(String(2))

    volume: Mapped[str | None] = mapped_column(String(50))
    number: Mapped[str | None] = mapped_column(String(50))
    speaker_name: Mapped[str | None] = mapped_column(String(200))

    document_url: Mapped[str | None] = mapped_column(String(500))
    source_hash: Mapped[str | None] = mapped_column(String(64))

    interventions: Mapped[list[DebateIntervention]] = relationship(back_populates="debate")

    __table_args__ = (
        Index("ix_debates_parl_session", "parliament", "session"),
        Index("ix_debates_debate_date", "debate_date"),
        Index("ix_debates_sitting", "sitting"),
    )

    def __repr__(self) -> str:
        return f"<Debate {self.parliament}-{self.session} #{self.sitting}>"
