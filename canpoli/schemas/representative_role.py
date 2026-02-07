"""Representative role schemas."""

from datetime import datetime

from canpoli.schemas.base import BaseSchema, PaginatedResponse


class RoleRepresentativeSummary(BaseSchema):
    """Minimal representative info for role responses."""

    hoc_id: int
    name: str


class RepresentativeRoleSummary(BaseSchema):
    """Representative role summary."""

    id: int
    role_name: str
    role_type: str
    organization: str | None = None
    parliament: int | None = None
    session: int | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    is_current: bool


class RepresentativeRoleResponse(RepresentativeRoleSummary):
    """Representative role response with representative."""

    representative: RoleRepresentativeSummary | None = None


class RepresentativeRoleListResponse(PaginatedResponse):
    """Paginated representative roles response."""

    roles: list[RepresentativeRoleResponse]
