"""Petition model."""

from __future__ import annotations

from sqlalchemy import Date, DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from canpoli.models.base import Base, TimestampMixin


class Petition(Base, TimestampMixin):
    """Parliamentary petition record."""

    __tablename__ = "petitions"

    id: Mapped[int] = mapped_column(primary_key=True)
    petition_number: Mapped[str] = mapped_column(String(50), nullable=False)

    title_en: Mapped[str | None] = mapped_column(Text())
    title_fr: Mapped[str | None] = mapped_column(Text())

    status: Mapped[str | None] = mapped_column(String(200))
    presentation_date: Mapped[Date | None] = mapped_column(Date())
    closing_date: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))
    signatures: Mapped[int | None] = mapped_column()

    sponsor_hoc_id: Mapped[int | None] = mapped_column()
    sponsor_name: Mapped[str | None] = mapped_column(String(200))

    parliament: Mapped[int | None] = mapped_column()
    session: Mapped[int | None] = mapped_column()

    source_url: Mapped[str | None] = mapped_column(String(500))
    source_hash: Mapped[str | None] = mapped_column(String(64))

    __table_args__ = (
        Index("ix_petitions_petition_number", "petition_number"),
        Index("ix_petitions_presentation_date", "presentation_date"),
    )

    def __repr__(self) -> str:
        return f"<Petition {self.petition_number}>"
