"""House of Commons parliamentary data ingestion service."""

from __future__ import annotations

import asyncio
import csv
import hashlib
import io
import json
import logging
import re
import time
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import delete, func, select

from canpoli.config import get_settings
from canpoli.database import get_session_context
from canpoli.exceptions import IngestionError
from canpoli.models import Debate, PartyStanding, Representative
from canpoli.repositories import (
    BillRepository,
    DebateInterventionRepository,
    DebateRepository,
    HouseOfficerExpenditureRepository,
    MemberExpenditureRepository,
    PartyRepository,
    PartyStandingRepository,
    PetitionRepository,
    RepresentativeRoleRepository,
    VoteMemberRepository,
    VoteRepository,
)

logger = logging.getLogger(__name__)
settings = get_settings()

USER_AGENT = "CanPoliAPI/1.0"


@dataclass
class HttpResult:
    url: str
    text: str


class HoCParliamentIngestionService:
    """Service to ingest parliamentary data from House of Commons and LEGISinfo."""

    def __init__(self) -> None:
        self.client = httpx.AsyncClient(
            timeout=settings.hoc_api_timeout,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "*/*",
            },
        )
        self.semaphore = asyncio.Semaphore(settings.hoc_max_concurrency)
        self.min_interval = settings.hoc_min_request_interval_ms / 1000.0
        self._last_request: dict[str, float] = {}
        self._last_lock = asyncio.Lock()

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

    async def _throttle(self, host: str) -> None:
        if self.min_interval <= 0:
            return
        async with self._last_lock:
            now = time.monotonic()
            last = self._last_request.get(host, 0.0)
            wait = self.min_interval - (now - last)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_request[host] = time.monotonic()

    async def _fetch_text(self, url: str, method: str = "GET", **kwargs: Any) -> HttpResult:
        async with self.semaphore:
            host = httpx.URL(url).host or ""
            await self._throttle(host)
            try:
                if method.upper() == "POST":
                    response = await self.client.post(url, **kwargs)
                else:
                    response = await self.client.get(url, **kwargs)
                response.raise_for_status()
            except httpx.HTTPError as exc:
                logger.error("HTTP error fetching %s: %s", url, exc, exc_info=True)
                raise IngestionError(f"Failed to fetch {url}: {exc}") from exc
            return HttpResult(url=url, text=response.text)

    async def ingest(self) -> dict[str, Any]:
        """Run all enabled ingestion pipelines."""
        stats: dict[str, Any] = {}
        try:
            if settings.hoc_enable_party_standings:
                stats["party_standings"] = await self.ingest_party_standings()
            if settings.hoc_enable_roles:
                stats["roles"] = await self.ingest_roles()
            if settings.hoc_enable_votes:
                stats["votes"] = await self.ingest_votes()
            if settings.hoc_enable_petitions:
                stats["petitions"] = await self.ingest_petitions()
            if settings.hoc_enable_debates:
                stats["debates"] = await self.ingest_debates()
            if settings.hoc_enable_expenditures:
                stats["expenditures"] = await self.ingest_expenditures()
            if settings.hoc_enable_bills:
                stats["bills"] = await self.ingest_bills()
            return stats
        finally:
            await self.close()

    async def ingest_party_standings(self) -> dict[str, int]:
        """Ingest party standings (seat counts)."""
        url = "https://www.ourcommons.ca/Members/en/party-standings/XML"
        result = await self._fetch_text(url)
        try:
            root = ET.fromstring(result.text)
        except ET.ParseError as exc:
            raise IngestionError(f"Failed to parse party standings XML: {exc}") from exc

        party_totals: dict[str, int] = defaultdict(int)
        for item in root.findall(".//PartyStanding"):
            party_name = (item.findtext("CaucusShortName") or "").strip()
            seat_text = (item.findtext("SeatCount") or "0").strip()
            if not party_name:
                continue
            try:
                seat_count = int(seat_text)
            except ValueError:
                seat_count = 0
            party_totals[party_name] += seat_count

        as_of = date.today()
        stats = {"created": 0, "updated": 0}
        async with get_session_context() as session:
            party_repo = PartyRepository(session)
            standings_repo = PartyStandingRepository(session)

            for party_name, seat_count in party_totals.items():
                party = None
                if party_name.lower() != "vacant":
                    party = await party_repo.get_by_name(party_name)
                    if not party:
                        party = await party_repo.get_or_create(name=party_name)

                existing_result = await session.execute(
                    select(PartyStanding)
                    .where(PartyStanding.party_name == party_name)
                    .where(PartyStanding.parliament == settings.hoc_parliament)
                    .where(PartyStanding.session == settings.hoc_session)
                    .where(PartyStanding.as_of_date == as_of)
                )
                existing = existing_result.scalar_one_or_none()
                await standings_repo.upsert(
                    party_name=party_name,
                    parliament=settings.hoc_parliament,
                    session=settings.hoc_session,
                    as_of_date=as_of,
                    party_id=party.id if party else None,
                    seat_count=seat_count,
                    source_url=result.url,
                )
                if existing:
                    stats["updated"] += 1
                else:
                    stats["created"] += 1

        return stats

    async def ingest_roles(self) -> dict[str, int]:
        """Ingest MP roles for current representatives."""
        stats = {"representatives": 0, "roles": 0, "errors": 0}
        async with get_session_context() as session:
            role_repo = RepresentativeRoleRepository(session)

            reps_result = await session.execute(
                select(Representative).where(Representative.is_active == True)  # noqa: E712
            )
            representatives = list(reps_result.scalars().all())
            stats["representatives"] = len(representatives)

            for rep in representatives:
                url = f"https://www.ourcommons.ca/members/en/{rep.hoc_id}/xml"
                try:
                    result = await self._fetch_text(url)
                    roles = self._parse_roles_xml(result.text, result.url)
                except Exception as exc:
                    logger.error(
                        "Failed to ingest roles for %s: %s", rep.hoc_id, exc, exc_info=True
                    )
                    stats["errors"] += 1
                    continue

                await role_repo.delete_by_representative_id(rep.id)
                for role in roles:
                    await role_repo.create(representative_id=rep.id, **role)
                    stats["roles"] += 1

        return stats

    def _parse_roles_xml(self, xml_text: str, source_url: str) -> list[dict[str, Any]]:
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            raise IngestionError(f"Failed to parse roles XML: {exc}") from exc

        source_hash = hashlib.sha256(xml_text.encode("utf-8")).hexdigest()
        roles: list[dict[str, Any]] = []

        def parse_dt(text: str | None) -> datetime | None:
            if not text:
                return None
            try:
                dt = datetime.fromisoformat(text)
            except ValueError:
                return None
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt

        # Caucus roles
        for role in root.findall(".//CaucusMemberRole"):
            roles.append(
                {
                    "role_name": (role.findtext("CaucusShortName") or "").strip()
                    or "Caucus Member",
                    "role_type": "caucus",
                    "organization": None,
                    "parliament": _to_int(role.findtext("ParliamentNumber")),
                    "session": _to_int(role.findtext("SessionNumber")),
                    "start_date": parse_dt(role.findtext("FromDateTime")),
                    "end_date": parse_dt(role.findtext("ToDateTime")),
                    "is_current": role.findtext("ToDateTime") in (None, ""),
                    "source_url": source_url,
                    "source_hash": source_hash,
                }
            )

        # Parliamentary positions
        for role in root.findall(".//ParliamentaryPositionRole"):
            roles.append(
                {
                    "role_name": (role.findtext("Title") or "").strip() or "Parliamentary Position",
                    "role_type": "parliamentary_position",
                    "organization": None,
                    "parliament": _to_int(role.findtext("ParliamentNumber")),
                    "session": _to_int(role.findtext("SessionNumber")),
                    "start_date": parse_dt(role.findtext("FromDateTime")),
                    "end_date": parse_dt(role.findtext("ToDateTime")),
                    "is_current": role.findtext("ToDateTime") in (None, ""),
                    "source_url": source_url,
                    "source_hash": source_hash,
                }
            )

        # Committee roles
        for role in root.findall(".//CommitteeMemberRole"):
            role_name = (role.findtext("AffiliationRoleName") or "").strip()
            committee_name = (role.findtext("CommitteeName") or "").strip()
            roles.append(
                {
                    "role_name": role_name or committee_name or "Committee Member",
                    "role_type": "committee",
                    "organization": committee_name or None,
                    "parliament": _to_int(role.findtext("ParliamentNumber")),
                    "session": _to_int(role.findtext("SessionNumber")),
                    "start_date": parse_dt(role.findtext("FromDateTime")),
                    "end_date": parse_dt(role.findtext("ToDateTime")),
                    "is_current": role.findtext("ToDateTime") in (None, ""),
                    "source_url": source_url,
                    "source_hash": source_hash,
                }
            )

        # Associations and interparliamentary group roles
        for role in root.findall(".//ParliamentaryAssociationsandInterparliamentaryGroupRole"):
            role_name = (role.findtext("AssociationMemberRoleType") or "").strip()
            title = (role.findtext("Title") or "").strip()
            organization = (role.findtext("Organization") or "").strip()
            roles.append(
                {
                    "role_name": title or role_name or "Association Member",
                    "role_type": "association",
                    "organization": organization or None,
                    "parliament": _to_int(role.findtext("ParliamentNumber")),
                    "session": _to_int(role.findtext("SessionNumber")),
                    "start_date": parse_dt(role.findtext("FromDateTime")),
                    "end_date": parse_dt(role.findtext("ToDateTime")),
                    "is_current": role.findtext("ToDateTime") in (None, ""),
                    "source_url": source_url,
                    "source_hash": source_hash,
                }
            )

        return roles

    async def ingest_votes(self) -> dict[str, int]:
        """Ingest votes and per-member vote records."""
        stats = {"votes": 0, "members": 0, "errors": 0}
        list_url = (
            "https://www.ourcommons.ca/members/en/votes"
            f"?parl={settings.hoc_parliament}&session={settings.hoc_session}"
        )

        result = await self._fetch_text(list_url)
        soup = BeautifulSoup(result.text, "html.parser")
        table = soup.find("table", id="global-votes")
        if not table:
            raise IngestionError("Votes table not found")

        rows = table.find("tbody").find_all("tr")
        votes: list[dict[str, Any]] = []
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 6:
                continue
            link = cells[0].find("a")
            vote_number = _parse_int(_strip_text(link.get_text()) if link else None)
            if not vote_number:
                continue
            subject = _strip_text(cells[2].get_text())
            counts_text = _strip_text(cells[3].get_text())
            counts = [c.strip() for c in counts_text.split("/") if c.strip()]
            yeas = _parse_int(counts[0]) if len(counts) > 0 else None
            nays = _parse_int(counts[1]) if len(counts) > 1 else None
            paired = _parse_int(counts[2]) if len(counts) > 2 else None
            decision = _strip_text(cells[4].get_text())
            vote_date = _parse_date(_strip_text(cells[5].get_text()))
            detail_href = link.get("href") if link else None
            detail_url = f"https://www.ourcommons.ca{detail_href}" if detail_href else None
            bill_number = _extract_bill_number(subject)
            votes.append(
                {
                    "vote_number": vote_number,
                    "subject_en": subject,
                    "decision": decision,
                    "yeas": yeas,
                    "nays": nays,
                    "paired": paired,
                    "vote_date": vote_date,
                    "bill_number": bill_number,
                    "detail_url": detail_url,
                }
            )

        async with get_session_context() as session:
            vote_repo = VoteRepository(session)
            vote_member_repo = VoteMemberRepository(session)

            rep_rows = await session.execute(select(Representative))
            rep_map = {rep.hoc_id: rep for rep in rep_rows.scalars().all()}

            for vote in votes:
                try:
                    detail_url = vote.pop("detail_url")
                    detail_text = None
                    source_hash = None
                    if detail_url:
                        detail = await self._fetch_text(detail_url)
                        detail_text = detail.text
                        source_hash = hashlib.sha256(detail_text.encode("utf-8")).hexdigest()

                    existing = await vote_repo.get_by_vote_number(
                        vote_number=vote["vote_number"],
                        parliament=settings.hoc_parliament,
                        session=settings.hoc_session,
                    )

                    if existing and source_hash and existing.source_hash == source_hash:
                        continue

                    extra_fields = {}
                    members: list[dict[str, Any]] = []
                    if detail_text:
                        extra_fields, members = self._parse_vote_detail(detail_text)

                    stored = await vote_repo.upsert(
                        vote_number=vote["vote_number"],
                        parliament=settings.hoc_parliament,
                        session=settings.hoc_session,
                        vote_date=vote.get("vote_date"),
                        subject_en=extra_fields.get("subject_en") or vote.get("subject_en"),
                        decision=vote.get("decision"),
                        yeas=vote.get("yeas"),
                        nays=vote.get("nays"),
                        paired=vote.get("paired"),
                        bill_number=extra_fields.get("bill_number") or vote.get("bill_number"),
                        motion_text=extra_fields.get("motion_text"),
                        sitting=extra_fields.get("sitting"),
                        source_url=detail_url,
                        source_hash=source_hash,
                    )
                    stats["votes"] += 1

                    if members:
                        await vote_member_repo.delete_by_vote_id(stored.id)
                        for member in members:
                            hoc_id = member.get("hoc_id")
                            rep = rep_map.get(hoc_id) if hoc_id else None
                            await vote_member_repo.create(
                                vote_id=stored.id,
                                representative_id=rep.id if rep else None,
                                hoc_id=hoc_id,
                                member_name=member.get("member_name"),
                                position=member.get("position"),
                                party_name=member.get("party_name"),
                                riding_name=member.get("riding_name"),
                            )
                            stats["members"] += 1
                except Exception as exc:
                    logger.error("Failed to ingest vote %s: %s", vote, exc, exc_info=True)
                    stats["errors"] += 1

        return stats

    def _parse_vote_detail(self, html_text: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        soup = BeautifulSoup(html_text, "html.parser")
        extra: dict[str, Any] = {}

        subject_div = soup.select_one("#mip-vote-desc")
        if subject_div:
            extra["subject_en"] = _strip_text(subject_div.get_text())

        motion_div = soup.select_one("#mip-vote-text-collapsible-text")
        if motion_div:
            extra["motion_text"] = _strip_text(motion_div.get_text(" "))

        bill_heading = soup.select_one(".mip-vote-bill-section h2")
        if bill_heading:
            bill_text = _strip_text(bill_heading.get_text())
            extra["bill_number"] = _extract_bill_number(bill_text) or bill_text

        sitting_text = soup.select_one(".mip-vote-title-section p")
        if sitting_text:
            match = re.search(r"Sitting\s+No\.\s*(\d+)", sitting_text.get_text())
            if match:
                extra["sitting"] = _parse_int(match.group(1))

        members: list[dict[str, Any]] = []
        members_table = soup.select_one(".ce-mip-mp-vote-panel-body table")
        if members_table:
            for row in members_table.select("tbody tr"):
                cells = row.find_all("td")
                if len(cells) < 3:
                    continue
                name_cell = cells[0]
                link = name_cell.find("a")
                hoc_id = None
                member_name = (
                    _strip_text(link.get_text()) if link else _strip_text(name_cell.get_text())
                )
                if link and link.get("href"):
                    hoc_id = _parse_int(link.get("href").strip("/").split("/")[-1])
                riding_name = None
                if "(" in name_cell.get_text():
                    ride_match = re.search(r"\((.*?)\)", name_cell.get_text())
                    riding_name = ride_match.group(1).strip() if ride_match else None

                party_name = _strip_text(cells[1].get_text())
                vote_text = _strip_text(cells[2].get_text())
                paired_text = _strip_text(cells[3].get_text()) if len(cells) > 3 else ""
                position = vote_text or ("Paired" if paired_text else "Absent")

                members.append(
                    {
                        "hoc_id": hoc_id,
                        "member_name": member_name,
                        "party_name": party_name or None,
                        "riding_name": riding_name,
                        "position": position,
                    }
                )

        return extra, members

    async def ingest_petitions(self) -> dict[str, int]:
        """Ingest petitions from the petitions portal."""
        stats = {"petitions": 0, "errors": 0}
        base_url = "https://www.ourcommons.ca/petitions/en/Petition/SearchAsync"

        def build_form(page: int) -> dict[str, str]:
            return {
                "parl": "Latest",
                "type": "",
                "keyword": "",
                "sponsor": "",
                "status": "",
                "RPP": "20",
                "order": "Recent",
                "page": str(page),
                "category": "All",
                "output": "",
                "reCaptchaAction": "",
                "reCaptchaToken": "",
            }

        first = await self._fetch_text(base_url, method="POST", data=build_form(1))
        payload = json.loads(first.text)
        html = payload.get("html", "")
        total_pages = _extract_total_pages(html) or 1

        async with get_session_context() as session:
            petition_repo = PetitionRepository(session)
            rep_rows = await session.execute(select(Representative))
            rep_name_map = {rep.name.lower(): rep for rep in rep_rows.scalars().all()}

            for page in range(1, total_pages + 1):
                page_result = (
                    first
                    if page == 1
                    else await self._fetch_text(base_url, method="POST", data=build_form(page))
                )
                page_payload = json.loads(page_result.text)
                page_html = page_payload.get("html", "")
                soup = BeautifulSoup(page_html, "html.parser")
                for row in soup.select("tr.Pub"):
                    try:
                        cells = row.find_all("td")
                        if len(cells) < 6:
                            continue
                        link = row.select_one("a.publicationTitleSearch")
                        if not link:
                            continue
                        spans = link.find_all("span")
                        petition_number = _strip_text(spans[0].get_text()) if spans else None
                        if not petition_number:
                            continue
                        title_text = (
                            _strip_text(spans[1].get_text())
                            if len(spans) > 1
                            else _strip_text(link.get_text())
                        )

                        status_text = _strip_text(cells[3].get_text(" "))
                        sponsor_name = _strip_text(cells[4].get_text())
                        signatures = _parse_int(_strip_text(cells[5].get_text()))
                        detail_href = link.get("href")
                        detail_url = (
                            f"https://www.ourcommons.ca/petitions/en/Petition/{detail_href}"
                            if detail_href
                            else None
                        )

                        details = {}
                        if detail_url:
                            details = await self._parse_petition_detail(detail_url)

                        sponsor_hoc_id = details.get("sponsor_hoc_id")
                        if sponsor_hoc_id is None and sponsor_name:
                            rep = rep_name_map.get(sponsor_name.lower())
                            sponsor_hoc_id = rep.hoc_id if rep else None

                        await petition_repo.upsert(
                            petition_number=petition_number,
                            title_en=title_text,
                            status=status_text,
                            presentation_date=details.get("presentation_date"),
                            closing_date=details.get("closing_date"),
                            signatures=signatures,
                            sponsor_hoc_id=sponsor_hoc_id,
                            sponsor_name=details.get("sponsor_name") or sponsor_name,
                            parliament=settings.hoc_parliament,
                            session=settings.hoc_session,
                            source_url=detail_url,
                            source_hash=details.get("source_hash"),
                        )
                        stats["petitions"] += 1
                    except Exception as exc:
                        logger.error("Failed to ingest petition row: %s", exc, exc_info=True)
                        stats["errors"] += 1

        return stats

    async def _parse_petition_detail(self, url: str) -> dict[str, Any]:
        result = await self._fetch_text(url)
        soup = BeautifulSoup(result.text, "html.parser")
        details: dict[str, Any] = {
            "source_hash": hashlib.sha256(result.text.encode("utf-8")).hexdigest(),
        }

        member_link = soup.select_one("#DetailsMember a")
        if member_link and member_link.get("href"):
            match = re.search(r"\((\d+)\)", member_link.get("href"))
            if match:
                details["sponsor_hoc_id"] = _parse_int(match.group(1))
            details["sponsor_name"] = _strip_text(member_link.get_text())

        # History dates
        for dt_tag in soup.select(".history-section dt"):
            label = _strip_text(dt_tag.get_text()).lower()
            dd_tag = dt_tag.find_next_sibling("dd")
            if not dd_tag:
                continue
            dt_value = _parse_datetime(_strip_text(dd_tag.get_text()))
            if not dt_value:
                continue
            if "presented" in label:
                details["presentation_date"] = dt_value.date()
            if "closed" in label:
                details["closing_date"] = dt_value

        return details

    async def ingest_debates(self) -> dict[str, int]:
        """Ingest Hansard debates with full text."""
        stats = {"debates": 0, "interventions": 0, "errors": 0}
        parl = settings.hoc_parliament
        sess = settings.hoc_session

        async with get_session_context() as session:
            debate_repo = DebateRepository(session)
            intervention_repo = DebateInterventionRepository(session)

            max_sitting_result = await session.execute(
                select(func.max(Debate.sitting)).where(
                    Debate.parliament == parl, Debate.session == sess
                )
            )
            max_sitting = max_sitting_result.scalar_one()
            if max_sitting:
                start = max_sitting + 1
                end = max_sitting + settings.hoc_debates_lookahead
            else:
                start = 1
                end = settings.hoc_debates_max_sitting

            missing = 0
            for sitting in range(start, end + 1):
                found_any = False
                for lang in settings.hoc_debate_languages:
                    lang_code = "E" if lang.lower().startswith("en") else "F"
                    parl_session_code = f"{parl}{sess}"
                    url = (
                        "https://www.ourcommons.ca/Content/House/"
                        f"{parl_session_code}/Debates/{sitting}/HAN{sitting}-{lang_code}.XML"
                    )
                    try:
                        result = await self._fetch_text(url)
                    except IngestionError:
                        continue

                    found_any = True
                    debate_data, interventions = self._parse_hansard_xml(
                        result.text, url, lang.lower(), sitting
                    )

                    existing = await debate_repo.get_by_parl_session_sitting_lang(
                        parl, sess, sitting, debate_data.get("language")
                    )
                    source_hash = debate_data.get("source_hash")
                    if existing and existing.source_hash == source_hash:
                        continue

                    stored = await debate_repo.upsert(
                        parliament=parl,
                        session=sess,
                        sitting=sitting,
                        language=debate_data.get("language"),
                        debate_date=debate_data.get("debate_date"),
                        volume=debate_data.get("volume"),
                        number=debate_data.get("number"),
                        speaker_name=debate_data.get("speaker_name"),
                        document_url=url,
                        source_hash=source_hash,
                    )
                    stats["debates"] += 1

                    await intervention_repo.delete_by_debate_id(stored.id)
                    for idx, item in enumerate(interventions, start=1):
                        await intervention_repo.create(
                            debate_id=stored.id,
                            sequence=idx,
                            speaker_name=item.get("speaker_name"),
                            speaker_affiliation=item.get("speaker_affiliation"),
                            floor_language=item.get("floor_language"),
                            timestamp=item.get("timestamp"),
                            order_of_business=item.get("order_of_business"),
                            subject_title=item.get("subject_title"),
                            intervention_type=item.get("intervention_type"),
                            text=item.get("text"),
                        )
                        stats["interventions"] += 1

                if not found_any:
                    missing += 1
                    if missing >= settings.hoc_debates_max_missing:
                        break
                else:
                    missing = 0

        return stats

    def _parse_hansard_xml(
        self,
        xml_text: str,
        source_url: str,
        language: str,
        sitting: int,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            raise IngestionError(f"Failed to parse Hansard XML: {exc}") from exc

        extracted = {
            item.attrib.get("Name"): "".join(item.itertext()).strip()
            for item in root.findall(".//ExtractedItem")
        }

        debate_date = _parse_date(extracted.get("Date"))
        if not debate_date:
            date_text = f"{extracted.get('MetaDateNumYear')}-{extracted.get('MetaDateNumMonth')}-{extracted.get('MetaDateNumDay')}"
            debate_date = _parse_date(date_text)

        data = {
            "parliament": _to_int(extracted.get("ParliamentNumber")),
            "session": _to_int(extracted.get("SessionNumber")),
            "debate_date": debate_date,
            "volume": extracted.get("Volume"),
            "number": extracted.get("Number"),
            "speaker_name": extracted.get("SpeakerName"),
            "language": language,
            "source_hash": hashlib.sha256(xml_text.encode("utf-8")).hexdigest(),
            "source_url": source_url,
            "sitting": sitting,
        }

        interventions: list[dict[str, Any]] = []
        current_order = None
        current_subject = None
        current_language = None
        current_timestamp = None

        for element in root.iter():
            tag = _strip_tag(element.tag)
            if tag == "OrderOfBusinessTitle":
                current_order = _strip_text("".join(element.itertext()))
            elif tag == "SubjectOfBusinessTitle":
                current_subject = _strip_text("".join(element.itertext()))
            elif tag == "FloorLanguage":
                current_language = element.attrib.get("language")
            elif tag == "Timestamp":
                hr = element.attrib.get("Hr")
                mn = element.attrib.get("Mn")
                if hr and mn:
                    current_timestamp = f"{int(hr):02d}:{int(mn):02d}"
            elif tag == "Intervention":
                interventions.append(
                    self._parse_intervention(
                        element,
                        current_order,
                        current_subject,
                        current_language,
                        current_timestamp,
                    )
                )

        return data, interventions

    def _parse_intervention(
        self,
        element: ET.Element,
        current_order: str | None,
        current_subject: str | None,
        current_language: str | None,
        current_timestamp: str | None,
    ) -> dict[str, Any]:
        speaker_affiliation = None
        speaker_name = None
        affiliation = element.find(".//PersonSpeaking/Affiliation")
        if affiliation is not None:
            speaker_affiliation = _strip_text("".join(affiliation.itertext()))
            if speaker_affiliation:
                speaker_name = speaker_affiliation.split("(")[0].strip()

        para_texts = []
        for para in element.findall(".//ParaText"):
            text = _strip_text("".join(para.itertext()))
            if text:
                para_texts.append(text)

        return {
            "speaker_name": speaker_name,
            "speaker_affiliation": speaker_affiliation,
            "floor_language": (current_language or "").lower() if current_language else None,
            "timestamp": current_timestamp,
            "order_of_business": current_order,
            "subject_title": current_subject,
            "intervention_type": element.attrib.get("Type"),
            "text": "\n\n".join(para_texts) if para_texts else None,
        }

    async def ingest_expenditures(self) -> dict[str, int]:
        """Ingest member and house officer expenditures."""
        stats = {"members": 0, "house_officers": 0, "errors": 0}
        try:
            stats["members"] = await self.ingest_member_expenditures()
        except Exception as exc:
            logger.error("Failed to ingest member expenditures: %s", exc, exc_info=True)
            stats["errors"] += 1
        try:
            stats["house_officers"] = await self.ingest_house_officer_expenditures()
        except Exception as exc:
            logger.error("Failed to ingest house officer expenditures: %s", exc, exc_info=True)
            stats["errors"] += 1
        return stats

    async def ingest_member_expenditures(self) -> int:
        """Ingest latest member expenditures CSV."""
        page_url = "https://www.ourcommons.ca/ProactiveDisclosure/en/members"
        page = await self._fetch_text(page_url)
        soup = BeautifulSoup(page.text, "html.parser")
        csv_link = soup.select_one("a.csv-btn")
        if not csv_link or not csv_link.get("href"):
            raise IngestionError("Member expenditure CSV link not found")

        period_tag = soup.select_one("#quarters-dropdown-text")
        period_text = _strip_text(period_tag.get_text()) if period_tag else ""

        period_start, period_end = _parse_date_range(period_text)
        fiscal_year = _fiscal_year(period_start) if period_start else None

        csv_url = f"https://www.ourcommons.ca{csv_link.get('href')}"
        csv_result = await self._fetch_text(csv_url)
        reader = csv.DictReader(io.StringIO(csv_result.text))
        if reader.fieldnames:
            reader.fieldnames = [name.lstrip("\ufeff") for name in reader.fieldnames]

        async with get_session_context() as session:
            repo = MemberExpenditureRepository(session)
            rep_rows = await session.execute(select(Representative))
            rep_map: dict[tuple[str, str], Representative] = {}
            for rep in rep_rows.scalars().all():
                last = (rep.last_name or "").lower().strip()
                first = (rep.first_name or "").lower().strip()
                if last:
                    rep_map[(last, first)] = rep
                    rep_map[(last, "")] = rep

            if period_start and period_end:
                await session.execute(
                    delete(repo.model).where(
                        repo.model.period_start == period_start,
                        repo.model.period_end == period_end,
                    )
                )

            count = 0
            for row in reader:
                name = (row.get("Name") or "").strip().strip("\ufeff")
                if not name:
                    continue
                hoc_id, representative_id = _map_member_name(name, rep_map)

                categories = {
                    "Salaries": row.get("Salaries"),
                    "Travel": row.get("Travel"),
                    "Hospitality": row.get("Hospitality"),
                    "Contracts": row.get("Contracts"),
                }
                for category, amount in categories.items():
                    value = _parse_amount(amount)
                    await repo.create(
                        representative_id=representative_id,
                        hoc_id=hoc_id,
                        member_name=name,
                        category=category,
                        amount=value,
                        period_start=period_start,
                        period_end=period_end,
                        fiscal_year=fiscal_year,
                        source_url=csv_url,
                    )
                    count += 1

        return count

    async def ingest_house_officer_expenditures(self) -> int:
        """Ingest house officer expenditures from CSV links."""
        page_url = "https://www.ourcommons.ca/Boie/en/reports-and-disclosure"
        page = await self._fetch_text(page_url)
        soup = BeautifulSoup(page.text, "html.parser")
        csv_links = [
            link.get("href")
            for link in soup.find_all("a")
            if link.get("href", "").endswith(".csv") and "HouseOfficers" in link.get("href", "")
        ]
        if not csv_links:
            raise IngestionError("House officer CSV links not found")

        count = 0
        async with get_session_context() as session:
            repo = HouseOfficerExpenditureRepository(session)

            for href in csv_links:
                csv_url = f"https://www.ourcommons.ca{href}"
                csv_result = await self._fetch_text(csv_url)
                text_stream = io.StringIO(csv_result.text)
                reader = csv.reader(text_stream)

                rows = list(reader)
                if len(rows) < 3:
                    continue

                period_line = rows[1][0] if rows[1] else ""
                period_start, period_end = _parse_date_range(period_line)
                fiscal_year = _fiscal_year(period_start) if period_start else None

                if period_start and period_end:
                    await session.execute(
                        delete(repo.model).where(
                            repo.model.period_start == period_start,
                            repo.model.period_end == period_end,
                        )
                    )

                headers = [h.strip() for h in rows[2]]
                for row in rows[3:]:
                    if not row or not row[0].strip():
                        continue
                    row_data = {
                        headers[i]: row[i] if i < len(row) else "" for i in range(len(headers))
                    }
                    role_title = row_data.get("Role")
                    officer_name = row_data.get("Name")

                    categories = {
                        "Employees' Salaries": row_data.get("Employees' Salaries($)"),
                        "Service Contracts": row_data.get("Service Contracts($)"),
                        "Travel": row_data.get("Travel($)"),
                        "Hospitality": row_data.get("Hospitality($)"),
                        "Office": row_data.get("Office($)"),
                    }
                    for category, amount in categories.items():
                        value = _parse_amount(amount)
                        await repo.create(
                            officer_name=officer_name or "",
                            role_title=role_title,
                            category=category,
                            amount=value,
                            period_start=period_start,
                            period_end=period_end,
                            fiscal_year=fiscal_year,
                            source_url=csv_url,
                        )
                        count += 1

        return count

    async def ingest_bills(self) -> dict[str, int]:
        """Ingest bills from LEGISinfo list endpoint."""
        stats = {"bills": 0, "errors": 0}
        parlsession = f"{settings.hoc_parliament}-{settings.hoc_session}"
        url = f"https://www.parl.ca/legisinfo/en/bills/json?parlsession={parlsession}"
        result = await self._fetch_text(url)
        try:
            items = json.loads(result.text)
        except json.JSONDecodeError as exc:
            raise IngestionError(f"Failed to parse bills JSON: {exc}") from exc

        async with get_session_context() as session:
            repo = BillRepository(session)
            for item in items:
                try:
                    bill_number = item.get("BillNumberFormatted")
                    if not bill_number:
                        continue

                    introduced_date = _pick_first_date(
                        item.get("PassedHouseFirstReadingDateTime"),
                        item.get("PassedSenateFirstReadingDateTime"),
                    )

                    latest_activity_date = _parse_datetime(item.get("LatestActivityDateTime"))
                    title_en = item.get("LongTitleEn") or item.get("ShortTitleEn")
                    title_fr = item.get("LongTitleFr") or item.get("ShortTitleFr")

                    source_hash = hashlib.sha256(
                        json.dumps(item, sort_keys=True).encode("utf-8")
                    ).hexdigest()

                    await repo.upsert(
                        bill_number=bill_number,
                        parliament=item.get("ParliamentNumber"),
                        session=item.get("SessionNumber"),
                        legisinfo_id=item.get("BillId"),
                        title_en=title_en,
                        title_fr=title_fr,
                        status=item.get("CurrentStatusEn"),
                        introduced_date=introduced_date,
                        latest_activity_date=latest_activity_date,
                        sponsor_name=item.get("SponsorEn"),
                        sponsor_party=None,
                        summary_en=None,
                        summary_fr=None,
                        source_url=url,
                        source_hash=source_hash,
                    )
                    stats["bills"] += 1
                except Exception as exc:
                    logger.error("Failed to ingest bill: %s", exc, exc_info=True)
                    stats["errors"] += 1

        return stats


def _strip_tag(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


def _strip_text(text: str | None) -> str:
    return (text or "").strip()


def _parse_int(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(re.sub(r"[^0-9]", "", value))
    except ValueError:
        return None


def _to_int(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    value = value.strip()
    for fmt in ("%A, %B %d, %Y", "%B %d, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    cleaned = (
        value.replace("a.m.", "AM")
        .replace("p.m.", "PM")
        .replace(" at ", " ")
        .replace("(EDT)", "")
        .replace("(EST)", "")
        .replace("(PDT)", "")
        .replace("(PST)", "")
        .strip()
    )
    for fmt in (
        "%B %d, %Y, %I:%M %p",
        "%B %d, %Y %I:%M %p",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
    ):
        try:
            dt = datetime.strptime(cleaned, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


def _parse_date_range(text: str | None) -> tuple[date | None, date | None]:
    if not text:
        return None, None
    match = re.search(
        r"From\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})\s+to\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})", text
    )
    if not match:
        return None, None
    start = _parse_date(match.group(1))
    end = _parse_date(match.group(2))
    return start, end


def _parse_amount(value: str | None) -> float:
    if not value:
        return 0.0
    cleaned = value.replace(",", "").replace("$", "").strip()
    if cleaned in {"-", "-   ", ""}:
        return 0.0
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _extract_bill_number(text: str | None) -> str | None:
    if not text:
        return None
    match = re.search(r"Bill\s+([A-Z]-\d+)", text)
    return match.group(1) if match else None


def _extract_total_pages(html: str) -> int | None:
    match = re.search(r"Page:\s*\d+\s*of\s*(\d+)", html)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def _fiscal_year(start_date: date | None) -> str | None:
    if not start_date:
        return None
    if start_date.month >= 4:
        return f"{start_date.year}-{start_date.year + 1}"
    return f"{start_date.year - 1}-{start_date.year}"


def _map_member_name(
    name: str, rep_map: dict[tuple[str, str], Representative]
) -> tuple[int | None, int | None]:
    if "," in name:
        parts = [p.strip() for p in name.split(",", 1)]
        last = parts[0].lower()
        first = parts[1].lower() if len(parts) > 1 else ""
        rep = rep_map.get((last, first)) or rep_map.get((last, ""))
        if rep:
            return rep.hoc_id, rep.id
    return None, None


def _pick_first_date(*values: str | None) -> date | None:
    dates = [_parse_datetime(value) for value in values if value]
    dates = [d for d in dates if d]
    if not dates:
        return None
    dates.sort()
    return dates[0].date()
