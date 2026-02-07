"""Parties API endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from canpoli.database import get_session
from canpoli.repositories import PartyRepository
from canpoli.schemas import PartyListResponse, PartyResponse

router = APIRouter(prefix="/v1/parties", tags=["Parties"])


@router.get("", response_model=PartyListResponse)
async def list_parties(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PartyListResponse:
    """Get all political parties."""
    repo = PartyRepository(session)
    limit = 50  # Unlikely to have more than 50 parties
    parties = await repo.get_all(limit=limit)
    total = await repo.count()

    return PartyListResponse(
        parties=[PartyResponse.model_validate(p) for p in parties],
        total=total,
        limit=limit,
        offset=0,
    )
