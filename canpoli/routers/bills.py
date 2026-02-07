"""Bills API endpoints."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from canpoli.database import get_session
from canpoli.rate_limit import rate_limit_dependency
from canpoli.repositories import BillRepository
from canpoli.schemas import BillListResponse, BillResponse

router = APIRouter(
    tags=["Bills"],
    dependencies=[Depends(rate_limit_dependency)],
)


@router.get("", response_model=BillListResponse)
async def list_bills(
    session: Annotated[AsyncSession, Depends(get_session)],
    bill_number: Annotated[str | None, Query(description="Filter by bill number")] = None,
    status: Annotated[str | None, Query(description="Filter by bill status")] = None,
    sponsor_hoc_id: Annotated[int | None, Query(description="Filter by sponsor HoC ID")] = None,
    updated_since: Annotated[datetime | None, Query(description="Filter by latest activity datetime")] = None,
    parliament: Annotated[int | None, Query(description="Filter by parliament number")] = None,
    session_number: Annotated[int | None, Query(description="Filter by session number")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> BillListResponse:
    """Get bills with optional filters."""
    repo = BillRepository(session)
    bills = await repo.list_with_filters(
        bill_number=bill_number,
        status=status,
        sponsor_hoc_id=sponsor_hoc_id,
        updated_since=updated_since,
        parliament=parliament,
        session=session_number,
        limit=limit,
        offset=offset,
    )
    total = await repo.count_with_filters(
        bill_number=bill_number,
        status=status,
        sponsor_hoc_id=sponsor_hoc_id,
        updated_since=updated_since,
        parliament=parliament,
        session=session_number,
    )
    return BillListResponse(
        bills=[BillResponse.model_validate(b) for b in bills],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{bill_id}", response_model=BillResponse)
async def get_bill(
    session: Annotated[AsyncSession, Depends(get_session)],
    bill_id: int,
) -> BillResponse:
    """Get a single bill by ID."""
    repo = BillRepository(session)
    bill = await repo.get(bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    return BillResponse.model_validate(bill)
