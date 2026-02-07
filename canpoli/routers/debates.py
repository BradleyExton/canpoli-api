"""Debates (Hansard) API endpoints."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from canpoli.database import get_session
from canpoli.rate_limit import rate_limit_dependency
from canpoli.repositories import DebateRepository
from canpoli.schemas import DebateInterventionResponse, DebateListResponse, DebateResponse

router = APIRouter(
    tags=["Debates"],
    dependencies=[Depends(rate_limit_dependency)],
)


def _serialize_debate(debate, include_interventions: bool) -> DebateResponse:
    interventions = None
    if include_interventions and debate.interventions is not None:
        interventions = [
            DebateInterventionResponse.model_validate(i) for i in debate.interventions
        ]
    return DebateResponse(
        id=debate.id,
        parliament=debate.parliament,
        session=debate.session,
        sitting=debate.sitting,
        debate_date=debate.debate_date,
        language=debate.language,
        volume=debate.volume,
        number=debate.number,
        speaker_name=debate.speaker_name,
        document_url=debate.document_url,
        interventions=interventions,
    )


@router.get("", response_model=DebateListResponse)
async def list_debates(
    session: Annotated[AsyncSession, Depends(get_session)],
    debate_date: Annotated[
        date | None, Query(alias="date", description="Filter by debate date")
    ] = None,
    language: Annotated[str | None, Query(description="Filter by language (en/fr)")] = None,
    sitting: Annotated[int | None, Query(description="Filter by sitting number")] = None,
    parliament: Annotated[int | None, Query(description="Filter by parliament number")] = None,
    session_number: Annotated[int | None, Query(description="Filter by session number")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> DebateListResponse:
    """Get debates with optional filters."""
    repo = DebateRepository(session)
    debates = await repo.list_with_filters(
        debate_date=debate_date,
        language=language,
        sitting=sitting,
        parliament=parliament,
        session=session_number,
        limit=limit,
        offset=offset,
    )
    total = await repo.count_with_filters(
        debate_date=debate_date,
        language=language,
        sitting=sitting,
        parliament=parliament,
        session=session_number,
    )
    return DebateListResponse(
        debates=[_serialize_debate(d, include_interventions=False) for d in debates],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{debate_id}", response_model=DebateResponse)
async def get_debate(
    session: Annotated[AsyncSession, Depends(get_session)],
    debate_id: int,
    include_interventions: Annotated[
        bool, Query(description="Include full interventions text")
    ] = True,
) -> DebateResponse:
    """Get a single debate by ID."""
    repo = DebateRepository(session)
    debate = (
        await repo.get_with_interventions(debate_id)
        if include_interventions
        else await repo.get(debate_id)
    )
    if not debate:
        raise HTTPException(status_code=404, detail="Debate not found")
    return _serialize_debate(debate, include_interventions)
