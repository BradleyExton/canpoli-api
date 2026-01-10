from typing import Annotated

from fastapi import APIRouter, Query

from api.civic_context.db.cache import get_cached_response, set_cached_response
from api.civic_context.logging_config import get_logger
from api.civic_context.routers.civic.models import CivicContextResponse, Location
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
        logger.info(f"Cache HIT for {lat}, {lng}")
        return CivicContextResponse(**cached)

    logger.info(f"Cache MISS for {lat}, {lng}")

    # Fetch from API
    representatives = await get_representatives(lat, lng)

    response = CivicContextResponse(
        representatives=representatives,
        location=Location(lat=lat, lng=lng),
    )

    # Save to cache
    set_cached_response(lat, lng, response.model_dump())

    return response
