"""OpenParliament.ca API client for MP parliamentary activity."""

import asyncio
from dataclasses import dataclass

import httpx

from api.civic_context.config import get_settings
from api.civic_context.logging_config import get_logger
from api.civic_context.routers.civic.models import (
    Bill,
    VoteRecord,
)

logger = get_logger()
settings = get_settings()


@dataclass
class OpenParliamentData:
    """Data fetched from OpenParliament API."""

    openparliament_url: str | None
    bills_sponsored: list[Bill]
    recent_votes: list[VoteRecord]


def _get_headers() -> dict[str, str]:
    """Get headers for OpenParliament API requests."""
    return {
        "User-Agent": f"CivicContextAPI/1.0.0 ({settings.openparliament_contact_email})",
        "Accept": "application/json",
    }


def _normalize_name(name: str) -> str:
    """Normalize MP name for searching by removing honorifics."""
    honorifics = [
        "Right Hon.",
        "The Right Hon.",
        "The Hon.",
        "Hon.",
        "Dr.",
        "Mr.",
        "Mrs.",
        "Ms.",
    ]
    result = name
    for honorific in honorifics:
        result = result.replace(honorific, "").strip()
    return result


async def _search_politician(client: httpx.AsyncClient, name: str) -> str | None:
    """
    Search OpenParliament for a politician by name and return their URL slug.

    Returns None if no match found.
    """
    try:
        clean_name = _normalize_name(name)

        response = await client.get("/politicians/", params={"name": clean_name})
        response.raise_for_status()

        data = response.json()
        objects = data.get("objects", [])

        # Filter for current MPs (those with current_riding)
        current_mps = [p for p in objects if p.get("current_riding")]

        if not current_mps and objects:
            # Fall back to any match if no current MPs found
            current_mps = objects

        if not current_mps:
            # Try with just last name as fallback
            last_name = clean_name.split()[-1] if clean_name else ""
            if last_name:
                response = await client.get(
                    "/politicians/", params={"name": last_name}
                )
                response.raise_for_status()
                data = response.json()
                objects = data.get("objects", [])
                current_mps = [p for p in objects if p.get("current_riding")]
                if not current_mps:
                    current_mps = objects

        if current_mps:
            # Extract slug from URL: "/politicians/john-doe/" -> "john-doe"
            url: str = current_mps[0].get("url", "")
            if url:
                slug: str = url.strip("/").split("/")[-1]
                return slug

        return None

    except Exception as e:
        logger.warning(f"OpenParliament politician search failed: {e}")
        return None


async def _fetch_sponsored_bills(
    client: httpx.AsyncClient, slug: str
) -> list[Bill]:
    """Fetch recent bills sponsored by the politician."""
    try:
        response = await client.get(
            "/bills/",
            params={
                "sponsor_politician": f"/politicians/{slug}/",
                "limit": settings.openparliament_bills_limit,
            },
        )

        if response.status_code == 429:
            logger.warning("OpenParliament rate limited on bills request")
            return []

        response.raise_for_status()
        data = response.json()

        bills = []
        for b in data.get("objects", []):
            try:
                # Handle bilingual name field
                name = b.get("name", {})
                if isinstance(name, dict):
                    name = name.get("en", name.get("fr", "Unknown"))

                bills.append(
                    Bill(
                        number=b.get("number", "Unknown"),
                        name=name,
                        introduced=b.get("introduced", "Unknown"),
                        session=b.get("session", "Unknown"),
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to parse bill: {e}")
                continue

        return bills

    except httpx.TimeoutException:
        logger.warning(f"OpenParliament bills timeout for {slug}")
        return []
    except httpx.HTTPStatusError as e:
        logger.warning(f"OpenParliament bills error: {e.response.status_code}")
        return []
    except Exception as e:
        logger.error(f"OpenParliament bills unexpected error: {e}")
        return []


async def _fetch_recent_votes(
    client: httpx.AsyncClient, slug: str
) -> list[VoteRecord]:
    """Fetch recent voting record for the politician."""
    try:
        response = await client.get(
            "/votes/ballots/",
            params={
                "politician": f"/politicians/{slug}/",
                "limit": settings.openparliament_votes_limit,
            },
        )

        if response.status_code == 429:
            logger.warning("OpenParliament rate limited on votes request")
            return []

        response.raise_for_status()
        data = response.json()

        votes = []
        for ballot in data.get("objects", []):
            try:
                # Parse vote_url: "/votes/45-1/59/" -> session="45-1", number=59
                vote_url: str = ballot.get("vote_url", "")
                parts = vote_url.strip("/").split("/")

                session = "Unknown"
                vote_number = 0
                if len(parts) >= 3:
                    session = parts[1]  # "45-1"
                    try:
                        vote_number = int(parts[2])  # 59
                    except ValueError:
                        pass

                votes.append(
                    VoteRecord(
                        session=session,
                        vote_number=vote_number,
                        mp_vote=ballot.get("ballot", "Unknown"),
                        vote_url=f"https://openparliament.ca{vote_url}",
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to parse vote: {e}")
                continue

        return votes

    except httpx.TimeoutException:
        logger.warning(f"OpenParliament votes timeout for {slug}")
        return []
    except httpx.HTTPStatusError as e:
        logger.warning(f"OpenParliament votes error: {e.response.status_code}")
        return []
    except Exception as e:
        logger.error(f"OpenParliament votes unexpected error: {e}")
        return []


async def get_parliamentary_activity(mp_name: str) -> OpenParliamentData | None:
    """
    Fetch parliamentary activity for an MP by name.

    Returns None if MP not found or API fails (graceful degradation).
    """
    async with httpx.AsyncClient(
        base_url=settings.openparliament_api_base_url,
        headers=_get_headers(),
        timeout=settings.openparliament_api_timeout,
    ) as client:
        # Step 1: Search for politician (sequential - need slug first)
        slug = await _search_politician(client, mp_name)
        if not slug:
            logger.info(f"MP not found in OpenParliament: {mp_name}")
            return None

        # Step 2: Fetch bills and votes in parallel
        bills_task = _fetch_sponsored_bills(client, slug)
        votes_task = _fetch_recent_votes(client, slug)

        results = await asyncio.gather(
            bills_task,
            votes_task,
            return_exceptions=True,
        )

        bills_result, votes_result = results

        # Handle partial failures gracefully
        bills_list: list[Bill] = (
            bills_result if isinstance(bills_result, list) else []
        )
        votes_list: list[VoteRecord] = (
            votes_result if isinstance(votes_result, list) else []
        )

        return OpenParliamentData(
            openparliament_url=slug,
            bills_sponsored=bills_list,
            recent_votes=votes_list,
        )
