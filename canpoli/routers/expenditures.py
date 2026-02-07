"""Expenditures API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from canpoli.database import get_session
from canpoli.rate_limit import rate_limit_dependency
from canpoli.repositories import (
    HouseOfficerExpenditureRepository,
    MemberExpenditureRepository,
)
from canpoli.schemas import (
    HouseOfficerExpenditureListResponse,
    HouseOfficerExpenditureResponse,
    MemberExpenditureListResponse,
    MemberExpenditureResponse,
)

router = APIRouter(
    tags=["Expenditures"],
    dependencies=[Depends(rate_limit_dependency)],
)


@router.get("/members", response_model=MemberExpenditureListResponse)
async def list_member_expenditures(
    session: Annotated[AsyncSession, Depends(get_session)],
    fiscal_year: Annotated[str | None, Query(description="Filter by fiscal year")] = None,
    category: Annotated[str | None, Query(description="Filter by category")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> MemberExpenditureListResponse:
    """Get member expenditures with optional filters."""
    repo = MemberExpenditureRepository(session)
    expenditures = await repo.list_with_filters(
        fiscal_year=fiscal_year,
        category=category,
        limit=limit,
        offset=offset,
    )
    total = await repo.count_with_filters(
        fiscal_year=fiscal_year,
        category=category,
    )
    return MemberExpenditureListResponse(
        expenditures=[MemberExpenditureResponse.model_validate(e) for e in expenditures],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/members/{hoc_id}", response_model=MemberExpenditureListResponse)
async def list_member_expenditures_for_member(
    session: Annotated[AsyncSession, Depends(get_session)],
    hoc_id: int,
    fiscal_year: Annotated[str | None, Query(description="Filter by fiscal year")] = None,
    category: Annotated[str | None, Query(description="Filter by category")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> MemberExpenditureListResponse:
    """Get expenditures for a specific member."""
    repo = MemberExpenditureRepository(session)
    expenditures = await repo.list_with_filters(
        hoc_id=hoc_id,
        fiscal_year=fiscal_year,
        category=category,
        limit=limit,
        offset=offset,
    )
    total = await repo.count_with_filters(
        hoc_id=hoc_id,
        fiscal_year=fiscal_year,
        category=category,
    )
    return MemberExpenditureListResponse(
        expenditures=[MemberExpenditureResponse.model_validate(e) for e in expenditures],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/house-officers", response_model=HouseOfficerExpenditureListResponse)
async def list_house_officer_expenditures(
    session: Annotated[AsyncSession, Depends(get_session)],
    fiscal_year: Annotated[str | None, Query(description="Filter by fiscal year")] = None,
    category: Annotated[str | None, Query(description="Filter by category")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> HouseOfficerExpenditureListResponse:
    """Get house officer expenditures with optional filters."""
    repo = HouseOfficerExpenditureRepository(session)
    expenditures = await repo.list_with_filters(
        fiscal_year=fiscal_year,
        category=category,
        limit=limit,
        offset=offset,
    )
    total = await repo.count_with_filters(
        fiscal_year=fiscal_year,
        category=category,
    )
    return HouseOfficerExpenditureListResponse(
        expenditures=[HouseOfficerExpenditureResponse.model_validate(e) for e in expenditures],
        total=total,
        limit=limit,
        offset=offset,
    )
