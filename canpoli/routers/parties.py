"""Parties API endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from canpoli.database import get_session
from canpoli.rate_limit import rate_limit_dependency
from canpoli.repositories import PartyRepository, PartyStandingRepository
from canpoli.schemas import PartyListResponse, PartyResponse

router = APIRouter(
    tags=["Parties"],
    dependencies=[Depends(rate_limit_dependency)],
)


@router.get("", response_model=PartyListResponse)
async def list_parties(
    session: Annotated[AsyncSession, Depends(get_session)],
    include_standings: Annotated[
        bool, Query(description="Include latest party standings (seat counts)")
    ] = False,
    parliament: Annotated[int | None, Query(description="Filter standings by parliament")] = None,
    session_number: Annotated[int | None, Query(description="Filter standings by session")] = None,
) -> PartyListResponse:
    """Get all political parties."""
    repo = PartyRepository(session)
    limit = 50  # Unlikely to have more than 50 parties
    parties = await repo.get_all(limit=limit)
    total = await repo.count()

    standings_map: dict[str, int] = {}
    if include_standings:
        standings_repo = PartyStandingRepository(session)
        as_of_date = await standings_repo.get_latest_as_of_date(parliament, session_number)
        if as_of_date:
            standings = await standings_repo.list_with_filters(
                parliament=parliament,
                session=session_number,
                as_of_date=as_of_date,
                limit=200,
                offset=0,
            )
            standings_map = {s.party_name: s.seat_count for s in standings}

    return PartyListResponse(
        parties=[
            PartyResponse(
                name=p.name,
                short_name=p.short_name,
                color=p.color,
                seat_count=standings_map.get(p.name),
            )
            for p in parties
        ],
        total=total,
        limit=limit,
        offset=0,
    )
