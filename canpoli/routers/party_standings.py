"""Party standings API endpoints."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from canpoli.database import get_session
from canpoli.rate_limit import rate_limit_dependency
from canpoli.repositories import PartyStandingRepository
from canpoli.schemas import PartyStandingListResponse, PartyStandingResponse

router = APIRouter(
    tags=["Party Standings"],
    dependencies=[Depends(rate_limit_dependency)],
)


@router.get("", response_model=PartyStandingListResponse)
async def list_party_standings(
    session: Annotated[AsyncSession, Depends(get_session)],
    parliament: Annotated[int | None, Query(description="Filter by parliament number")] = None,
    session_number: Annotated[int | None, Query(description="Filter by session number")] = None,
    as_of_date: Annotated[date | None, Query(description="Filter by as-of date")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PartyStandingListResponse:
    """Get party standings (latest by default)."""
    repo = PartyStandingRepository(session)
    if as_of_date is None:
        as_of_date = await repo.get_latest_as_of_date(parliament, session_number)
    standings = await repo.list_with_filters(
        parliament=parliament,
        session=session_number,
        as_of_date=as_of_date,
        limit=limit,
        offset=offset,
    )
    total = await repo.count_with_filters(
        parliament=parliament,
        session=session_number,
        as_of_date=as_of_date,
    )
    return PartyStandingListResponse(
        standings=[PartyStandingResponse.model_validate(s) for s in standings],
        total=total,
        limit=limit,
        offset=offset,
    )
