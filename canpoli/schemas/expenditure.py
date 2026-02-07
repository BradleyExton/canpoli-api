"""Expenditure schemas."""

from datetime import date
from decimal import Decimal

from canpoli.schemas.base import BaseSchema, PaginatedResponse


class MemberExpenditureResponse(BaseSchema):
    """Member expenditure response schema."""

    id: int
    representative_id: int | None = None
    hoc_id: int | None = None
    member_name: str
    category: str
    amount: Decimal
    period_start: date | None = None
    period_end: date | None = None
    fiscal_year: str | None = None


class HouseOfficerExpenditureResponse(BaseSchema):
    """House officer expenditure response schema."""

    id: int
    officer_name: str
    role_title: str | None = None
    category: str
    amount: Decimal
    period_start: date | None = None
    period_end: date | None = None
    fiscal_year: str | None = None


class MemberExpenditureListResponse(PaginatedResponse):
    """Paginated member expenditures response."""

    expenditures: list[MemberExpenditureResponse]


class HouseOfficerExpenditureListResponse(PaginatedResponse):
    """Paginated house officer expenditures response."""

    expenditures: list[HouseOfficerExpenditureResponse]
