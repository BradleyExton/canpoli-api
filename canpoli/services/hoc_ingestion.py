"""House of Commons data ingestion service."""

import logging
import xml.etree.ElementTree as ET
from typing import Any

import httpx

from canpoli.config import get_settings
from canpoli.database import get_session_context
from canpoli.exceptions import IngestionError
from canpoli.repositories import (
    PartyRepository,
    RepresentativeRepository,
    RidingRepository,
)

logger = logging.getLogger(__name__)
settings = get_settings()

# Party color mapping for major Canadian parties
PARTY_COLORS = {
    "Liberal": "#D71920",
    "Conservative": "#1A4782",
    "NDP": "#F37021",
    "Bloc Québécois": "#33B2CC",
    "Green Party": "#3D9B35",
    "Independent": "#808080",
}

# Party short name mapping
PARTY_SHORT_NAMES = {
    "Liberal": "LPC",
    "Conservative": "CPC",
    "NDP": "NDP",
    "Bloc Québécois": "BQ",
    "Green Party": "GPC",
    "Independent": "Ind.",
}


class HoCIngestionService:
    """Service to ingest MP data from House of Commons XML API."""

    def __init__(self):
        self.client = httpx.AsyncClient(
            base_url=settings.hoc_api_base_url,
            timeout=settings.hoc_api_timeout,
            headers={
                "User-Agent": "CanPoliAPI/1.0",
                "Accept": "application/xml",
            },
        )

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def fetch_all_mps(self) -> list[dict[str, Any]]:
        """Fetch all current MPs from House of Commons XML endpoint."""
        try:
            response = await self.client.get("/Members/en/search/XML")
            response.raise_for_status()
        except httpx.HTTPError as e:
            logger.error("HTTP error fetching MP data: %s", e, exc_info=True)
            raise IngestionError(f"Failed to fetch MP data: {e}") from e

        try:
            root = ET.fromstring(response.text)
        except ET.ParseError as e:
            logger.error("XML parse error: %s", e, exc_info=True)
            raise IngestionError(f"Failed to parse XML response: {e}") from e

        mps = []

        for mp in root.findall(".//MemberOfParliament"):
            person_id_text = mp.findtext("PersonId", "0")
            person_id = int(person_id_text) if person_id_text else 0
            if not person_id:
                continue

            first_name = mp.findtext("PersonOfficialFirstName", "")
            last_name = mp.findtext("PersonOfficialLastName", "")

            # Try to extract contact info (may not be in XML, will be None)
            email = mp.findtext("PersonEmail") or mp.findtext("Email")
            phone = mp.findtext("PersonTelephone") or mp.findtext("Telephone")

            mps.append(
                {
                    "hoc_id": person_id,
                    "first_name": first_name,
                    "last_name": last_name,
                    "name": f"{first_name} {last_name}".strip(),
                    "honorific": mp.findtext("PersonShortHonorific"),
                    "email": email,
                    "phone": phone,
                    "riding": mp.findtext("ConstituencyName", ""),
                    "province": mp.findtext("ConstituencyProvinceTerritoryName", ""),
                    "party": mp.findtext("CaucusShortName", ""),
                    "photo_url": f"https://www.ourcommons.ca/Members/en/{person_id}/photo",
                    "profile_url": f"https://www.ourcommons.ca/Members/en/{person_id}",
                }
            )

        return mps

    async def ingest(self) -> dict[str, int]:
        """Pull all current MPs and save to database."""
        stats = {"created": 0, "updated": 0, "errors": 0}

        try:
            mps_data = await self.fetch_all_mps()
            logger.info("Found %d MPs from House of Commons", len(mps_data))

            async with get_session_context() as session:
                party_repo = PartyRepository(session)
                riding_repo = RidingRepository(session)
                rep_repo = RepresentativeRepository(session)

                for mp in mps_data:
                    try:
                        # Get or create party
                        party = None
                        if mp.get("party"):
                            party_name = mp["party"]
                            party = await party_repo.get_or_create(
                                name=party_name,
                                short_name=PARTY_SHORT_NAMES.get(party_name),
                                color=PARTY_COLORS.get(party_name),
                            )

                        # Get or create riding
                        riding = None
                        if mp.get("riding"):
                            riding = await riding_repo.get_or_create(
                                name=mp["riding"],
                                province=mp.get("province", "Unknown"),
                            )

                        # Check if exists for stats
                        existing = await rep_repo.get_by_hoc_id(mp["hoc_id"])

                        # Upsert representative
                        await rep_repo.upsert_by_hoc_id(
                            hoc_id=mp["hoc_id"],
                            name=mp["name"],
                            first_name=mp.get("first_name"),
                            last_name=mp.get("last_name"),
                            honorific=mp.get("honorific"),
                            email=mp.get("email"),
                            phone=mp.get("phone"),
                            photo_url=mp.get("photo_url"),
                            profile_url=mp.get("profile_url"),
                            party_id=party.id if party else None,
                            riding_id=riding.id if riding else None,
                            is_active=True,
                        )

                        if existing:
                            stats["updated"] += 1
                        else:
                            stats["created"] += 1

                    except httpx.HTTPError as e:
                        logger.error(
                            "HTTP error processing MP %s: %s",
                            mp.get("name"),
                            e,
                            exc_info=True,
                        )
                        stats["errors"] += 1
                    except ValueError as e:
                        logger.error(
                            "Data validation error for MP %s: %s",
                            mp.get("name"),
                            e,
                            exc_info=True,
                        )
                        stats["errors"] += 1
                    except Exception as e:
                        logger.error(
                            "Unexpected error processing MP %s: %s",
                            mp.get("name"),
                            e,
                            exc_info=True,
                        )
                        stats["errors"] += 1

            return stats

        finally:
            await self.close()
