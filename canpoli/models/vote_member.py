"""Vote member model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from canpoli.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from canpoli.models.representative import Representative
    from canpoli.models.vote import Vote


class VoteMember(Base, TimestampMixin):
    """How a member voted on a specific vote."""

    __tablename__ = "vote_members"

    id: Mapped[int] = mapped_column(primary_key=True)
    vote_id: Mapped[int] = mapped_column(ForeignKey("votes.id"), nullable=False)
    representative_id: Mapped[int | None] = mapped_column(ForeignKey("representatives.id"))

    hoc_id: Mapped[int | None] = mapped_column()
    member_name: Mapped[str] = mapped_column(String(200), nullable=False)
    position: Mapped[str] = mapped_column(String(20), nullable=False)
    party_name: Mapped[str | None] = mapped_column(String(100))
    riding_name: Mapped[str | None] = mapped_column(String(200))

    vote: Mapped[Vote] = relationship(back_populates="members")
    representative: Mapped[Representative | None] = relationship()

    __table_args__ = (
        Index("ix_vote_members_vote_id", "vote_id"),
        Index("ix_vote_members_representative_id", "representative_id"),
    )

    def __repr__(self) -> str:
        return f"<VoteMember {self.member_name}: {self.position}>"
