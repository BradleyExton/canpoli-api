"""Ridings API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from canpoli.database import get_session
from canpoli.rate_limit import rate_limit_dependency
from canpoli.repositories import RepresentativeRepository, RidingRepository
from canpoli.schemas import RidingDetailResponse, RidingListResponse, RidingResponse
from canpoli.schemas.representative import RepresentativeResponse

router = APIRouter(
    tags=["Ridings"],
    dependencies=[Depends(rate_limit_dependency)],
)


@router.get("", response_model=RidingListResponse)
async def list_ridings(
    session: Annotated[AsyncSession, Depends(get_session)],
    province: Annotated[
        str | None,
        Query(
            description="Filter by province (e.g., 'Ontario', 'Quebec')",
            min_length=2,
            max_length=50,
        ),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> RidingListResponse:
    """Get paginated list of ridings with optional province filter."""
    repo = RidingRepository(session)

    if province:
        ridings = await repo.get_by_province(province, limit=limit, offset=offset)
        total = await repo.count_by_province(province)
    else:
        ridings = await repo.get_all(limit=limit, offset=offset)
        total = await repo.count()

    return RidingListResponse(
        ridings=[RidingResponse.model_validate(r) for r in ridings],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{riding_id}", response_model=RidingDetailResponse)
async def get_riding(
    session: Annotated[AsyncSession, Depends(get_session)],
    riding_id: int,
) -> RidingDetailResponse:
    """Get a single riding with its current representative."""
    riding_repo = RidingRepository(session)
    riding = await riding_repo.get(riding_id)

    if not riding:
        raise HTTPException(status_code=404, detail="Riding not found")

    # Get current representative for this riding
    rep_repo = RepresentativeRepository(session)
    rep = await rep_repo.get_by_riding_id(riding_id)

    return RidingDetailResponse(
        id=riding.id,
        name=riding.name,
        province=riding.province,
        fed_number=riding.fed_number,
        representative=RepresentativeResponse.model_validate(rep) if rep else None,
    )
