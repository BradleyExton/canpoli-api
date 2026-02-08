"""Member expenditure model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from canpoli.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from canpoli.models.representative import Representative


class MemberExpenditure(Base, TimestampMixin):
    """Member expenditures by category."""

    __tablename__ = "member_expenditures"

    id: Mapped[int] = mapped_column(primary_key=True)
    representative_id: Mapped[int | None] = mapped_column(ForeignKey("representatives.id"))
    hoc_id: Mapped[int | None] = mapped_column()
    member_name: Mapped[str] = mapped_column(String(200), nullable=False)

    category: Mapped[str] = mapped_column(String(50), nullable=False)
    amount: Mapped[Numeric] = mapped_column(Numeric(14, 2), nullable=False)

    period_start: Mapped[Date | None] = mapped_column(Date())
    period_end: Mapped[Date | None] = mapped_column(Date())
    fiscal_year: Mapped[str | None] = mapped_column(String(9))

    source_url: Mapped[str | None] = mapped_column(String(500))

    representative: Mapped[Representative | None] = relationship()

    __table_args__ = (
        Index("ix_member_expenditures_representative_id", "representative_id"),
        Index("ix_member_expenditures_fiscal_year", "fiscal_year"),
        Index("ix_member_expenditures_period", "period_start", "period_end"),
    )

    def __repr__(self) -> str:
        return f"<MemberExpenditure {self.member_name}: {self.category}>"
