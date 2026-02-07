"""Debate intervention (speech) model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from canpoli.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from canpoli.models.debate import Debate


class DebateIntervention(Base, TimestampMixin):
    """Single intervention/speech within a debate."""

    __tablename__ = "debate_interventions"

    id: Mapped[int] = mapped_column(primary_key=True)
    debate_id: Mapped[int] = mapped_column(ForeignKey("debates.id"), nullable=False)
    sequence: Mapped[int] = mapped_column(nullable=False)

    speaker_name: Mapped[str | None] = mapped_column(String(200))
    speaker_affiliation: Mapped[str | None] = mapped_column(String(300))
    floor_language: Mapped[str | None] = mapped_column(String(2))
    timestamp: Mapped[str | None] = mapped_column(String(5))

    order_of_business: Mapped[str | None] = mapped_column(String(200))
    subject_title: Mapped[str | None] = mapped_column(String(500))
    intervention_type: Mapped[str | None] = mapped_column(String(50))

    text: Mapped[str | None] = mapped_column(Text())

    debate: Mapped[Debate] = relationship(back_populates="interventions")

    __table_args__ = (
        Index("ix_debate_interventions_debate_id", "debate_id"),
        Index("ix_debate_interventions_sequence", "sequence"),
    )

    def __repr__(self) -> str:
        return f"<DebateIntervention {self.sequence}>"
