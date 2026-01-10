"""House of Commons Open Data API client for official MP data."""

import asyncio
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import httpx

from api.civic_context.config import get_settings
from api.civic_context.logging_config import get_logger
from api.civic_context.routers.civic.models import (
    Committee,
    MinisterialRole,
    ParliamentaryAssociation,
    ParliamentarySecretaryRole,
)

logger = get_logger()
settings = get_settings()


@dataclass
class HouseOfCommonsData:
    """Data fetched from House of Commons API."""

    hoc_person_id: int
    honorific: str | None
    province: str
    photo_url: str
    profile_url: str
    ministerial_role: MinisterialRole | None
    parliamentary_secretary_role: ParliamentarySecretaryRole | None
    committees: list[Committee]
    parliamentary_associations: list[ParliamentaryAssociation]


# In-memory cache for MP list and ministerial data
_mp_cache: dict[str, Any] | None = None
_mp_cache_expires_at: datetime | None = None

_ministers_cache: dict[int, MinisterialRole] | None = None
_ministers_cache_expires_at: datetime | None = None

_secretaries_cache: dict[int, ParliamentarySecretaryRole] | None = None
_secretaries_cache_expires_at: datetime | None = None


def _get_headers() -> dict[str, str]:
    """Get headers for House of Commons API requests."""
    return {
        "User-Agent": f"CivicContextAPI/1.0.0 ({settings.hoc_contact_email})",
        "Accept": "application/xml",
    }


def _normalize_constituency(name: str) -> str:
    """Normalize constituency name for matching."""
    # Handle dash variations (em-dash, en-dash, hyphen) and case
    return name.lower().replace("—", "-").replace("–", "-").strip()


async def _fetch_all_mps(client: httpx.AsyncClient) -> dict[str, dict[str, Any]]:
    """
    Fetch all current MPs and return dict keyed by normalized constituency.
    """
    global _mp_cache, _mp_cache_expires_at

    # Check cache
    if _mp_cache is not None and _mp_cache_expires_at and _mp_cache_expires_at > datetime.now():
        return _mp_cache

    try:
        response = await client.get("/Members/en/search/XML")
        response.raise_for_status()

        root = ET.fromstring(response.text)
        mps_by_constituency: dict[str, dict[str, Any]] = {}

        for mp in root.findall(".//MemberOfParliament"):
            constituency = mp.findtext("ConstituencyName", "")
            if not constituency:
                continue

            mp_data = {
                "person_id": int(mp.findtext("PersonId", "0")),
                "honorific": mp.findtext("PersonShortHonorific"),
                "first_name": mp.findtext("PersonOfficialFirstName", ""),
                "last_name": mp.findtext("PersonOfficialLastName", ""),
                "constituency": constituency,
                "province": mp.findtext("ConstituencyProvinceTerritoryName", ""),
                "caucus": mp.findtext("CaucusShortName", ""),
            }

            normalized_key = _normalize_constituency(constituency)
            mps_by_constituency[normalized_key] = mp_data

        # Cache for 24 hours
        _mp_cache = mps_by_constituency
        _mp_cache_expires_at = datetime.now() + timedelta(hours=24)

        logger.info(f"Cached {len(mps_by_constituency)} MPs from House of Commons")
        return mps_by_constituency

    except httpx.TimeoutException:
        logger.warning("House of Commons MP list request timed out")
        return _mp_cache or {}
    except httpx.HTTPStatusError as e:
        logger.warning(f"House of Commons MP list error: {e.response.status_code}")
        return _mp_cache or {}
    except ET.ParseError as e:
        logger.warning(f"House of Commons MP list XML parse error: {e}")
        return _mp_cache or {}
    except Exception as e:
        logger.warning(f"Failed to fetch MP list: {e}")
        return _mp_cache or {}


async def _fetch_ministers(client: httpx.AsyncClient) -> dict[int, MinisterialRole]:
    """Fetch all ministers, keyed by PersonId."""
    global _ministers_cache, _ministers_cache_expires_at

    if (
        _ministers_cache is not None
        and _ministers_cache_expires_at
        and _ministers_cache_expires_at > datetime.now()
    ):
        return _ministers_cache

    try:
        response = await client.get("/Members/en/ministries/XML")
        response.raise_for_status()

        root = ET.fromstring(response.text)
        ministers: dict[int, MinisterialRole] = {}

        for minister in root.findall(".//CabinetMember"):
            person_id_text = minister.findtext("PersonId", "0")
            person_id = int(person_id_text) if person_id_text else 0
            if person_id:
                order_text = minister.findtext("OrderOfPrecedence")
                order = int(order_text) if order_text else None

                ministers[person_id] = MinisterialRole(
                    title=minister.findtext("Title", "Unknown"),
                    order_of_precedence=order,
                    from_date=minister.findtext("FromDateTime"),
                )

        # Cache for 1 hour
        _ministers_cache = ministers
        _ministers_cache_expires_at = datetime.now() + timedelta(hours=1)

        logger.info(f"Cached {len(ministers)} ministers from House of Commons")
        return ministers

    except httpx.TimeoutException:
        logger.warning("House of Commons ministers request timed out")
        return _ministers_cache or {}
    except httpx.HTTPStatusError as e:
        logger.warning(f"House of Commons ministers error: {e.response.status_code}")
        return _ministers_cache or {}
    except ET.ParseError as e:
        logger.warning(f"House of Commons ministers XML parse error: {e}")
        return _ministers_cache or {}
    except Exception as e:
        logger.warning(f"Failed to fetch ministers: {e}")
        return _ministers_cache or {}


async def _fetch_parliamentary_secretaries(
    client: httpx.AsyncClient,
) -> dict[int, ParliamentarySecretaryRole]:
    """Fetch all parliamentary secretaries, keyed by PersonId."""
    global _secretaries_cache, _secretaries_cache_expires_at

    if (
        _secretaries_cache is not None
        and _secretaries_cache_expires_at
        and _secretaries_cache_expires_at > datetime.now()
    ):
        return _secretaries_cache

    try:
        response = await client.get("/Members/en/parliamentary-secretaries/XML")
        response.raise_for_status()

        root = ET.fromstring(response.text)
        secretaries: dict[int, ParliamentarySecretaryRole] = {}

        for secretary in root.findall(".//ParliamentarySecretary"):
            person_id_text = secretary.findtext("PersonId", "0")
            person_id = int(person_id_text) if person_id_text else 0
            if person_id:
                secretaries[person_id] = ParliamentarySecretaryRole(
                    title=secretary.findtext("Title", "Unknown"),
                    from_date=secretary.findtext("FromDateTime"),
                )

        # Cache for 1 hour
        _secretaries_cache = secretaries
        _secretaries_cache_expires_at = datetime.now() + timedelta(hours=1)

        logger.info(f"Cached {len(secretaries)} parliamentary secretaries from House of Commons")
        return secretaries

    except httpx.TimeoutException:
        logger.warning("House of Commons secretaries request timed out")
        return _secretaries_cache or {}
    except httpx.HTTPStatusError as e:
        logger.warning(f"House of Commons secretaries error: {e.response.status_code}")
        return _secretaries_cache or {}
    except ET.ParseError as e:
        logger.warning(f"House of Commons secretaries XML parse error: {e}")
        return _secretaries_cache or {}
    except Exception as e:
        logger.warning(f"Failed to fetch parliamentary secretaries: {e}")
        return _secretaries_cache or {}


async def _fetch_mp_details(
    client: httpx.AsyncClient, person_id: int
) -> tuple[list[Committee], list[ParliamentaryAssociation]]:
    """Fetch detailed MP data including committees and associations."""
    try:
        response = await client.get(f"/Members/en/{person_id}/XML")
        response.raise_for_status()

        root = ET.fromstring(response.text)

        committees: list[Committee] = []
        for committee in root.findall(".//CommitteeMemberRole"):
            name = committee.findtext("CommitteeName", "")
            if name:
                committees.append(
                    Committee(
                        name=name,
                        role=committee.findtext("Title"),
                    )
                )

        associations: list[ParliamentaryAssociation] = []
        for assoc in root.findall(".//ParliamentaryAssociationandInterparliamentaryGroupRole"):
            name = assoc.findtext("OrganizationName", "")
            if name:
                associations.append(
                    ParliamentaryAssociation(
                        name=name,
                        role=assoc.findtext("Title"),
                    )
                )

        return committees, associations

    except httpx.TimeoutException:
        logger.warning(f"House of Commons MP details timeout for {person_id}")
        return [], []
    except httpx.HTTPStatusError as e:
        logger.warning(f"House of Commons MP details error for {person_id}: {e.response.status_code}")
        return [], []
    except ET.ParseError as e:
        logger.warning(f"House of Commons MP details XML parse error for {person_id}: {e}")
        return [], []
    except Exception as e:
        logger.warning(f"Failed to fetch MP details for {person_id}: {e}")
        return [], []


async def get_house_of_commons_data(riding: str) -> HouseOfCommonsData | None:
    """
    Fetch House of Commons data for an MP by riding (constituency).

    Args:
        riding: The electoral district name from Represent API

    Returns None if MP not found or API fails (graceful degradation).
    """
    async with httpx.AsyncClient(
        base_url=settings.hoc_api_base_url,
        headers=_get_headers(),
        timeout=settings.hoc_api_timeout,
    ) as client:
        # Fetch MP list, ministers, and secretaries in parallel
        mps_task = _fetch_all_mps(client)
        ministers_task = _fetch_ministers(client)
        secretaries_task = _fetch_parliamentary_secretaries(client)

        results = await asyncio.gather(
            mps_task,
            ministers_task,
            secretaries_task,
            return_exceptions=True,
        )

        # Handle failures
        mps = results[0] if isinstance(results[0], dict) else {}
        ministers = results[1] if isinstance(results[1], dict) else {}
        secretaries = results[2] if isinstance(results[2], dict) else {}

        if not mps:
            logger.warning("No MP data available from House of Commons")
            return None

        # Find MP by constituency
        normalized_riding = _normalize_constituency(riding)
        mp_data = mps.get(normalized_riding)

        if not mp_data:
            logger.info(f"MP not found for riding: {riding} (normalized: {normalized_riding})")
            return None

        person_id: int = mp_data["person_id"]

        # Fetch detailed MP info (committees, associations)
        committees, associations = await _fetch_mp_details(client, person_id)

        # Build response
        photo_url = f"https://www.ourcommons.ca/Members/en/{person_id}/photo"
        profile_url = f"https://www.ourcommons.ca/Members/en/{person_id}"

        return HouseOfCommonsData(
            hoc_person_id=person_id,
            honorific=mp_data.get("honorific"),
            province=mp_data["province"],
            photo_url=photo_url,
            profile_url=profile_url,
            ministerial_role=ministers.get(person_id),
            parliamentary_secretary_role=secretaries.get(person_id),
            committees=committees,
            parliamentary_associations=associations,
        )
