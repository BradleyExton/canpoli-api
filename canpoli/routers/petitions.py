"""Petitions API endpoints."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from canpoli.database import get_session
from canpoli.rate_limit import rate_limit_dependency
from canpoli.repositories import PetitionRepository
from canpoli.schemas import PetitionListResponse, PetitionResponse

router = APIRouter(
    tags=["Petitions"],
    dependencies=[Depends(rate_limit_dependency)],
)


@router.get("", response_model=PetitionListResponse)
async def list_petitions(
    session: Annotated[AsyncSession, Depends(get_session)],
    status: Annotated[str | None, Query(description="Filter by status")] = None,
    sponsor_hoc_id: Annotated[int | None, Query(description="Filter by sponsor HoC ID")] = None,
    from_date: Annotated[date | None, Query(description="Filter by presentation date (from)")] = None,
    to_date: Annotated[date | None, Query(description="Filter by presentation date (to)")] = None,
    parliament: Annotated[int | None, Query(description="Filter by parliament number")] = None,
    session_number: Annotated[int | None, Query(description="Filter by session number")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PetitionListResponse:
    """Get petitions with optional filters."""
    repo = PetitionRepository(session)
    petitions = await repo.list_with_filters(
        status=status,
        sponsor_hoc_id=sponsor_hoc_id,
        from_date=from_date,
        to_date=to_date,
        parliament=parliament,
        session=session_number,
        limit=limit,
        offset=offset,
    )
    total = await repo.count_with_filters(
        status=status,
        sponsor_hoc_id=sponsor_hoc_id,
        from_date=from_date,
        to_date=to_date,
        parliament=parliament,
        session=session_number,
    )
    return PetitionListResponse(
        petitions=[PetitionResponse.model_validate(p) for p in petitions],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{petition_id}", response_model=PetitionResponse)
async def get_petition(
    session: Annotated[AsyncSession, Depends(get_session)],
    petition_id: int,
) -> PetitionResponse:
    """Get a single petition by ID."""
    repo = PetitionRepository(session)
    petition = await repo.get(petition_id)
    if not petition:
        raise HTTPException(status_code=404, detail="Petition not found")
    return PetitionResponse.model_validate(petition)
