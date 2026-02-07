"""Petition schemas."""

from datetime import date, datetime

from canpoli.schemas.base import BaseSchema, PaginatedResponse


class PetitionResponse(BaseSchema):
    """Petition response schema."""

    id: int
    petition_number: str
    title_en: str | None = None
    title_fr: str | None = None
    status: str | None = None
    presentation_date: date | None = None
    closing_date: datetime | None = None
    signatures: int | None = None
    sponsor_hoc_id: int | None = None
    sponsor_name: str | None = None
    parliament: int | None = None
    session: int | None = None


class PetitionListResponse(PaginatedResponse):
    """Paginated petitions response."""

    petitions: list[PetitionResponse]
