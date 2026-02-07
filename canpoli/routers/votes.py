"""Votes API endpoints."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from canpoli.database import get_session
from canpoli.rate_limit import rate_limit_dependency
from canpoli.repositories import VoteRepository
from canpoli.schemas import VoteListResponse, VoteMemberResponse, VoteResponse

router = APIRouter(
    tags=["Votes"],
    dependencies=[Depends(rate_limit_dependency)],
)


def _serialize_vote(vote, include_members: bool) -> VoteResponse:
    members = None
    if include_members and vote.members is not None:
        members = [VoteMemberResponse.model_validate(m) for m in vote.members]
    return VoteResponse(
        id=vote.id,
        vote_number=vote.vote_number,
        parliament=vote.parliament,
        session=vote.session,
        vote_date=vote.vote_date,
        subject_en=vote.subject_en,
        subject_fr=vote.subject_fr,
        decision=vote.decision,
        yeas=vote.yeas,
        nays=vote.nays,
        paired=vote.paired,
        bill_number=vote.bill_number,
        motion_text=vote.motion_text,
        sitting=vote.sitting,
        members=members,
    )


@router.get("", response_model=VoteListResponse)
async def list_votes(
    session: Annotated[AsyncSession, Depends(get_session)],
    vote_date: Annotated[
        date | None, Query(alias="date", description="Filter by vote date")
    ] = None,
    decision: Annotated[str | None, Query(description="Filter by vote decision")] = None,
    bill_number: Annotated[str | None, Query(description="Filter by bill number")] = None,
    parliament: Annotated[int | None, Query(description="Filter by parliament number")] = None,
    session_number: Annotated[int | None, Query(description="Filter by session number")] = None,
    include_members: Annotated[bool, Query(description="Include per-member votes")] = False,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> VoteListResponse:
    """Get votes with optional filters."""
    repo = VoteRepository(session)
    votes = await repo.list_with_filters(
        vote_date=vote_date,
        decision=decision,
        bill_number=bill_number,
        parliament=parliament,
        session=session_number,
        include_members=include_members,
        limit=limit,
        offset=offset,
    )
    total = await repo.count_with_filters(
        vote_date=vote_date,
        decision=decision,
        bill_number=bill_number,
        parliament=parliament,
        session=session_number,
    )
    return VoteListResponse(
        votes=[_serialize_vote(vote, include_members) for vote in votes],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{vote_id}", response_model=VoteResponse)
async def get_vote(
    session: Annotated[AsyncSession, Depends(get_session)],
    vote_id: int,
    include_members: Annotated[bool, Query(description="Include per-member votes")] = True,
) -> VoteResponse:
    """Get a single vote by ID."""
    repo = VoteRepository(session)
    vote = await repo.get_with_members(vote_id) if include_members else await repo.get(vote_id)
    if not vote:
        raise HTTPException(status_code=404, detail="Vote not found")
    return _serialize_vote(vote, include_members)
