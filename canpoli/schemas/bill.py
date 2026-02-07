"""Bill schemas."""

from datetime import date, datetime

from canpoli.schemas.base import BaseSchema, PaginatedResponse


class BillResponse(BaseSchema):
    """Bill response schema."""

    id: int
    legisinfo_id: int | None = None
    bill_number: str
    title_en: str | None = None
    title_fr: str | None = None
    status: str | None = None
    parliament: int | None = None
    session: int | None = None
    introduced_date: date | None = None
    latest_activity_date: datetime | None = None
    sponsor_hoc_id: int | None = None
    sponsor_name: str | None = None
    sponsor_party: str | None = None
    summary_en: str | None = None
    summary_fr: str | None = None


class BillListResponse(PaginatedResponse):
    """Paginated bills response."""

    bills: list[BillResponse]
