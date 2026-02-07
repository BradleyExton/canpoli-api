"""House officer expenditure model."""

from __future__ import annotations

from sqlalchemy import Date, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from canpoli.models.base import Base, TimestampMixin


class HouseOfficerExpenditure(Base, TimestampMixin):
    """House officer expenditures by category."""

    __tablename__ = "house_officer_expenditures"

    id: Mapped[int] = mapped_column(primary_key=True)

    officer_name: Mapped[str] = mapped_column(String(200), nullable=False)
    role_title: Mapped[str | None] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    amount: Mapped[Numeric] = mapped_column(Numeric(14, 2), nullable=False)

    period_start: Mapped[Date | None] = mapped_column(Date())
    period_end: Mapped[Date | None] = mapped_column(Date())
    fiscal_year: Mapped[str | None] = mapped_column(String(9))

    source_url: Mapped[str | None] = mapped_column(String(500))

    __table_args__ = (
        Index("ix_house_officer_expenditures_fiscal_year", "fiscal_year"),
        Index("ix_house_officer_expenditures_period", "period_start", "period_end"),
    )

    def __repr__(self) -> str:
        return f"<HouseOfficerExpenditure {self.officer_name}: {self.category}>"
