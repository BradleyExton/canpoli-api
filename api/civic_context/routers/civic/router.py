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
from api.civic_context.services.openparliament import get_parliamentary_activity
from api.civic_context.services.represent import get_representatives

logger = get_logger()

router = APIRouter(prefix="/civic", tags=["Civic Context"])


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

    # Enrich federal MP with OpenParliament data if available
    if representatives.federal:
        activity = await get_parliamentary_activity(representatives.federal.name)
        if activity:
            representatives = Representatives(
                federal=Representative(
                    name=representatives.federal.name,
                    party=representatives.federal.party,
                    riding=representatives.federal.riding,
                    email=representatives.federal.email,
                    parliamentary_activity=activity,
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
