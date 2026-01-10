import httpx
from fastapi import HTTPException

from api.civic_context.config import get_settings
from api.civic_context.logging_config import get_logger
from api.civic_context.routers.civic.models import Representative, Representatives

logger = get_logger()
settings = get_settings()


async def get_representatives(lat: float, lng: float) -> Representatives:
    """Fetch representatives for a location from Represent API."""

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{settings.represent_api_base_url}/representatives/",
                params={"point": f"{lat},{lng}"},
                timeout=settings.represent_api_timeout,
            )
            response.raise_for_status()
            data = response.json()

            return _parse_representatives(data.get("objects", []))

        except httpx.TimeoutException as e:
            logger.error(f"Represent API timeout: {e}")
            raise HTTPException(
                status_code=504, detail="Upstream API timeout - please try again"
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"Represent API HTTP error: {e.response.status_code}")
            if e.response.status_code >= 500:
                raise HTTPException(status_code=503, detail="Upstream API unavailable")
            raise HTTPException(
                status_code=502, detail=f"Upstream API error: {e.response.status_code}"
            )
        except httpx.RequestError as e:
            logger.error(f"Represent API request error: {e}")
            raise HTTPException(
                status_code=502, detail="Failed to connect to upstream API"
            )


def _parse_representatives(objects: list[dict]) -> Representatives:
    """Parse Represent API response into our schema."""
    federal = None
    provincial = None
    municipal = None

    for rep in objects:
        elected_office = rep.get("elected_office", "").lower()

        representative = Representative(
            name=rep.get("name", "Unknown"),
            party=rep.get("party_name"),
            riding=rep.get("district_name", "Unknown"),
            email=rep.get("email"),
        )

        # Determine government level
        # Check provincial first since "mpp" contains "mp"
        if provincial is None and (
            "mla" in elected_office
            or "mna" in elected_office
            or "mpp" in elected_office
        ):
            provincial = representative
        elif federal is None and (
            "mp" in elected_office or "member of parliament" in elected_office
        ):
            federal = representative
        elif municipal is None and (
            "councillor" in elected_office or "mayor" in elected_office
        ):
            municipal = representative

    return Representatives(
        federal=federal,
        provincial=provincial,
        municipal=municipal,
    )
