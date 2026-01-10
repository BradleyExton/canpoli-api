import asyncio
from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import ValidationError

from api.civic_context.db.cache import get_cached_response, set_cached_response
from api.civic_context.logging_config import get_logger
from api.civic_context.routers.civic.models import (
    CivicContextResponse,
    Location,
    Representative,
    Representatives,
)
from api.civic_context.services.houseofcommons import (
    HouseOfCommonsData,
    get_house_of_commons_data,
)
from api.civic_context.services.openparliament import (
    OpenParliamentData,
    get_parliamentary_activity,
)
from api.civic_context.services.represent import get_representatives

logger = get_logger()

router = APIRouter(prefix="/civic", tags=["Civic Context"])


def _enrich_federal_representative(
    base: Representative,
    op_data: OpenParliamentData | None,
    hoc_data: HouseOfCommonsData | None,
) -> Representative:
    """Combine base representative data with enrichment data into flattened structure."""
    return Representative(
        # Core identity (from Represent API)
        name=base.name,
        riding=base.riding,
        party=base.party,
        email=base.email,
        # Official profile (from House of Commons)
        hoc_person_id=hoc_data.hoc_person_id if hoc_data else None,
        honorific=hoc_data.honorific if hoc_data else None,
        province=hoc_data.province if hoc_data else None,
        photo_url=hoc_data.photo_url if hoc_data else None,
        profile_url=hoc_data.profile_url if hoc_data else None,
        # Executive roles (from House of Commons)
        ministerial_role=hoc_data.ministerial_role if hoc_data else None,
        parliamentary_secretary_role=hoc_data.parliamentary_secretary_role if hoc_data else None,
        # Parliamentary engagement (from House of Commons)
        committees=hoc_data.committees if hoc_data else [],
        parliamentary_associations=hoc_data.parliamentary_associations if hoc_data else [],
        # Legislative activity (from OpenParliament)
        openparliament_url=op_data.openparliament_url if op_data else None,
        bills_sponsored=op_data.bills_sponsored if op_data else [],
        recent_votes=op_data.recent_votes if op_data else [],
    )


@router.get("/", response_model=CivicContextResponse)
async def get_civic_context(
    lat: Annotated[float, Query(ge=-90, le=90, description="Latitude")],
    lng: Annotated[float, Query(ge=-180, le=180, description="Longitude")],
) -> CivicContextResponse:
    """Get civic context for a location."""

    # Check cache first
    cached = get_cached_response(lat, lng)
    if cached:
        try:
            logger.info(f"Cache HIT for {lat}, {lng}")
            return CivicContextResponse(**cached)
        except ValidationError:
            # Stale cache with incompatible schema - treat as cache miss
            logger.warning(f"Cache schema mismatch for {lat}, {lng} - refetching")

    logger.info(f"Cache MISS for {lat}, {lng}")

    # Fetch from Represent API
    representatives = await get_representatives(lat, lng)

    # Enrich federal MP with OpenParliament and House of Commons data if available
    if representatives.federal:
        # Fetch both data sources in parallel
        activity_task = get_parliamentary_activity(representatives.federal.name)
        hoc_task = get_house_of_commons_data(representatives.federal.riding)

        results = await asyncio.gather(
            activity_task,
            hoc_task,
            return_exceptions=True,
        )

        # Handle partial failures gracefully
        op_data: OpenParliamentData | None = (
            results[0] if isinstance(results[0], OpenParliamentData) else None
        )
        hoc_data: HouseOfCommonsData | None = (
            results[1] if isinstance(results[1], HouseOfCommonsData) else None
        )

        if op_data or hoc_data:
            representatives = Representatives(
                federal=_enrich_federal_representative(
                    representatives.federal, op_data, hoc_data
                ),
                provincial=representatives.provincial,
                municipal=representatives.municipal,
            )

    response = CivicContextResponse(
        representatives=representatives,
        location=Location(lat=lat, lng=lng),
    )

    # Save to cache
    set_cached_response(lat, lng, response.model_dump())

    return response
