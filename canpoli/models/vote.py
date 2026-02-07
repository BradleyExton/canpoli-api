"""Vote model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Date, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from canpoli.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from canpoli.models.vote_member import VoteMember


class Vote(Base, TimestampMixin):
    """Recorded House vote."""

    __tablename__ = "votes"

    id: Mapped[int] = mapped_column(primary_key=True)
    vote_number: Mapped[int] = mapped_column(nullable=False)

    parliament: Mapped[int | None] = mapped_column()
    session: Mapped[int | None] = mapped_column()

    vote_date: Mapped[Date | None] = mapped_column(Date())
    subject_en: Mapped[str | None] = mapped_column(Text())
    subject_fr: Mapped[str | None] = mapped_column(Text())

    decision: Mapped[str | None] = mapped_column(String(100))
    yeas: Mapped[int | None] = mapped_column()
    nays: Mapped[int | None] = mapped_column()
    paired: Mapped[int | None] = mapped_column()

    bill_number: Mapped[str | None] = mapped_column(String(20))
    motion_text: Mapped[str | None] = mapped_column(Text())
    sitting: Mapped[int | None] = mapped_column()

    source_url: Mapped[str | None] = mapped_column(String(500))
    source_hash: Mapped[str | None] = mapped_column(String(64))

    members: Mapped[list[VoteMember]] = relationship(back_populates="vote")

    __table_args__ = (
        Index("ix_votes_vote_number_parl_session", "vote_number", "parliament", "session"),
        Index("ix_votes_vote_date", "vote_date"),
        Index("ix_votes_bill_number", "bill_number"),
    )

    def __repr__(self) -> str:
        return f"<Vote {self.vote_number}>"
