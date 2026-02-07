"""Representative Pydantic schemas."""

from __future__ import annotations



from canpoli.schemas.base import BaseSchema, PaginatedResponse
from canpoli.schemas.party import PartyResponse
from canpoli.schemas.representative_role import RepresentativeRoleSummary


class RepresentativeResponse(BaseSchema):
    """Representative response schema (for list views and nested use)."""

    hoc_id: int  # Public identifier
    first_name: str | None = None
    last_name: str | None = None
    name: str
    honorific: str | None = None
    email: str | None = None
    phone: str | None = None
    photo_url: str | None = None
    profile_url: str | None = None
    is_active: bool


class NestedRidingResponse(BaseSchema):
    """Riding response for nesting in representative detail."""

    id: int
    name: str
    province: str
    fed_number: int | None = None


class RepresentativeDetailResponse(RepresentativeResponse):
    """Representative with nested party and riding."""

    party: PartyResponse | None = None
    riding: NestedRidingResponse | None = None
    current_roles: list[RepresentativeRoleSummary] | None = None


class RepresentativeListResponse(PaginatedResponse):
    """Paginated list of representatives."""

    representatives: list[RepresentativeDetailResponse]
