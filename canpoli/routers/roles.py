"""Representative roles API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from canpoli.database import get_session
from canpoli.rate_limit import rate_limit_dependency
from canpoli.repositories import RepresentativeRoleRepository
from canpoli.schemas import RepresentativeRoleListResponse, RepresentativeRoleResponse

router = APIRouter(
    tags=["Roles"],
    dependencies=[Depends(rate_limit_dependency)],
)


@router.get("", response_model=RepresentativeRoleListResponse)
async def list_roles(
    session: Annotated[AsyncSession, Depends(get_session)],
    hoc_id: Annotated[int | None, Query(description="Filter by representative HoC ID")] = None,
    current: Annotated[bool | None, Query(description="Filter by current roles")] = None,
    role_type: Annotated[str | None, Query(description="Filter by role type")] = None,
    parliament: Annotated[int | None, Query(description="Filter by parliament number")] = None,
    session_number: Annotated[int | None, Query(description="Filter by session number")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> RepresentativeRoleListResponse:
    """Get roles with optional filters."""
    repo = RepresentativeRoleRepository(session)
    roles = await repo.list_with_filters(
        hoc_id=hoc_id,
        role_type=role_type,
        current=current,
        parliament=parliament,
        session=session_number,
        limit=limit,
        offset=offset,
    )
    total = await repo.count_with_filters(
        hoc_id=hoc_id,
        role_type=role_type,
        current=current,
        parliament=parliament,
        session=session_number,
    )
    return RepresentativeRoleListResponse(
        roles=[RepresentativeRoleResponse.model_validate(role) for role in roles],
        total=total,
        limit=limit,
        offset=offset,
    )

