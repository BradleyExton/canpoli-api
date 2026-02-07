"""Party standing schemas."""

from datetime import date

from canpoli.schemas.base import BaseSchema, PaginatedResponse


class PartyStandingResponse(BaseSchema):
    """Party standing response schema."""

    id: int
    party_id: int | None = None
    party_name: str
    seat_count: int
    as_of_date: date | None = None
    parliament: int | None = None
    session: int | None = None


class PartyStandingListResponse(PaginatedResponse):
    """Paginated party standings response."""

    standings: list[PartyStandingResponse]
