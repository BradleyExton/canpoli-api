"""Riding Pydantic schemas."""

from canpoli.schemas.base import BaseSchema, PaginatedResponse
from canpoli.schemas.representative import RepresentativeResponse


class RidingResponse(BaseSchema):
    """Riding response schema (for list views and nested use)."""

    id: int
    name: str
    province: str
    fed_number: int | None = None


class RidingDetailResponse(RidingResponse):
    """Riding with current representative."""

    representative: RepresentativeResponse | None = None


class RidingListResponse(PaginatedResponse):
    """Paginated list of ridings."""

    ridings: list[RidingResponse]
