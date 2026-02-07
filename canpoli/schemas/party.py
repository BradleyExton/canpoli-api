"""Party Pydantic schemas."""

from canpoli.schemas.base import BaseSchema, PaginatedResponse


class PartyResponse(BaseSchema):
    """Party response schema."""

    name: str
    short_name: str | None = None
    color: str | None = None
    seat_count: int | None = None


class PartyListResponse(PaginatedResponse):
    """List of parties response."""

    parties: list[PartyResponse]
