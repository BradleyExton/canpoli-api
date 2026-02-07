"""Bill model."""

from __future__ import annotations

from sqlalchemy import Date, DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from canpoli.models.base import Base, TimestampMixin


class Bill(Base, TimestampMixin):
    """Parliamentary bill."""

    __tablename__ = "bills"

    id: Mapped[int] = mapped_column(primary_key=True)
    legisinfo_id: Mapped[int | None] = mapped_column()
    bill_number: Mapped[str] = mapped_column(String(20), nullable=False)

    title_en: Mapped[str | None] = mapped_column(String(500))
    title_fr: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str | None] = mapped_column(String(200))

    parliament: Mapped[int | None] = mapped_column()
    session: Mapped[int | None] = mapped_column()

    introduced_date: Mapped[Date | None] = mapped_column(Date())
    latest_activity_date: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))

    sponsor_hoc_id: Mapped[int | None] = mapped_column()
    sponsor_name: Mapped[str | None] = mapped_column(String(200))
    sponsor_party: Mapped[str | None] = mapped_column(String(100))

    summary_en: Mapped[str | None] = mapped_column(Text())
    summary_fr: Mapped[str | None] = mapped_column(Text())

    source_url: Mapped[str | None] = mapped_column(String(500))
    source_hash: Mapped[str | None] = mapped_column(String(64))

    __table_args__ = (
        Index("ix_bills_bill_number", "bill_number"),
        Index("ix_bills_parl_session", "parliament", "session"),
        Index("ix_bills_latest_activity_date", "latest_activity_date"),
    )

    def __repr__(self) -> str:
        return f"<Bill {self.bill_number}>"
