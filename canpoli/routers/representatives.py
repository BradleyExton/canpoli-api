"""Representatives API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from canpoli.database import get_session
from canpoli.rate_limit import rate_limit_dependency
from canpoli.repositories import RepresentativeRepository, RidingRepository
from canpoli.schemas import RepresentativeDetailResponse, RepresentativeListResponse

router = APIRouter(
    tags=["Representatives"],
    dependencies=[Depends(rate_limit_dependency)],
)


@router.get("", response_model=RepresentativeListResponse)
async def list_representatives(
    session: Annotated[AsyncSession, Depends(get_session)],
    province: Annotated[
        str | None,
        Query(description="Filter by province (e.g., 'Ontario', 'Quebec')", min_length=2, max_length=50),
    ] = None,
    party: Annotated[
        str | None,
        Query(description="Filter by party name (e.g., 'Liberal', 'Conservative')", min_length=2, max_length=100),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> RepresentativeListResponse:
    """Get paginated list of representatives with optional filters."""
    repo = RepresentativeRepository(session)

    representatives = await repo.get_all_with_filters(
        province=province,
        party=party,
        limit=limit,
        offset=offset,
    )
    total = await repo.count_with_filters(province=province, party=party)

    return RepresentativeListResponse(
        representatives=[
            RepresentativeDetailResponse.model_validate(r) for r in representatives
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/lookup", response_model=RepresentativeDetailResponse)
async def lookup_representative(
    session: Annotated[AsyncSession, Depends(get_session)],
    postal_code: Annotated[
        str | None, Query(description="Canadian postal code")
    ] = None,
    lat: Annotated[float | None, Query(ge=-90, le=90)] = None,
    lng: Annotated[float | None, Query(ge=-180, le=180)] = None,
) -> RepresentativeDetailResponse:
    """
    Lookup representative by postal code or coordinates.

    Uses PostGIS to resolve coordinates to a riding.
    """
    has_postal = postal_code is not None
    has_lat = lat is not None
    has_lng = lng is not None

    if has_postal and (has_lat or has_lng):
        raise HTTPException(
            status_code=422,
            detail="Provide only one of postal_code or lat+lng",
        )

    if not has_postal and not (has_lat or has_lng):
        raise HTTPException(
            status_code=422,
            detail="Provide either postal_code or lat+lng",
        )

    if has_lat != has_lng:
        raise HTTPException(
            status_code=422,
            detail="Both lat and lng are required for coordinate lookup",
        )

    if has_postal:
        raise HTTPException(
            status_code=501,
            detail="Lookup by postal code not yet implemented",
        )

    riding_repo = RidingRepository(session)
    assert lat is not None and lng is not None
    riding = await riding_repo.get_by_point(lat=lat, lng=lng)
    if not riding:
        raise HTTPException(
            status_code=404,
            detail="Riding not found for coordinates",
        )

    rep_repo = RepresentativeRepository(session)
    rep = await rep_repo.get_by_riding_id(riding.id)
    if not rep:
        raise HTTPException(status_code=404, detail="Representative not found")

    return RepresentativeDetailResponse.model_validate(rep)


@router.get("/{hoc_id}", response_model=RepresentativeDetailResponse)
async def get_representative(
    session: Annotated[AsyncSession, Depends(get_session)],
    hoc_id: int,
) -> RepresentativeDetailResponse:
    """Get a single representative by House of Commons ID."""
    repo = RepresentativeRepository(session)
    rep = await repo.get_by_hoc_id(hoc_id)

    if not rep:
        raise HTTPException(status_code=404, detail="Representative not found")

    return RepresentativeDetailResponse.model_validate(rep)
