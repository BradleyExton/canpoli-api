"""
CLI script for ingesting riding boundary GeoJSON into PostGIS.

Usage:
    python -m canpoli.cli.ingest_boundaries --geojson /path/to/boundaries.geojson
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from canpoli.database import get_session_context
from canpoli.repositories import RepresentativeRepository, RidingRepository

PROVINCE_ABBREV_TO_NAME = {
    "AB": "Alberta",
    "BC": "British Columbia",
    "MB": "Manitoba",
    "NB": "New Brunswick",
    "NL": "Newfoundland and Labrador",
    "NS": "Nova Scotia",
    "NT": "Northwest Territories",
    "NU": "Nunavut",
    "ON": "Ontario",
    "PE": "Prince Edward Island",
    "QC": "Quebec",
    "SK": "Saskatchewan",
    "YT": "Yukon",
}

PROVINCE_UID_TO_NAME = {
    "10": "Newfoundland and Labrador",
    "11": "Prince Edward Island",
    "12": "Nova Scotia",
    "13": "New Brunswick",
    "24": "Quebec",
    "35": "Ontario",
    "46": "Manitoba",
    "47": "Saskatchewan",
    "48": "Alberta",
    "59": "British Columbia",
    "60": "Yukon",
    "61": "Northwest Territories",
    "62": "Nunavut",
}

DEFAULT_NAME_FIELDS = [
    "district_name",
    "riding_name",
    "name",
    "FEDNAME",
    "FED_NAME",
    "ED_NAME",
]
DEFAULT_PROVINCE_FIELDS = [
    "province",
    "province_name",
    "PRNAME",
    "PROVNAME",
    "province_abbrev",
    "PRUID",
    "PR_ABBR",
]


def _normalize_province(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    if trimmed.isdigit():
        key = trimmed.zfill(2)
        return PROVINCE_UID_TO_NAME.get(key, trimmed)
    if len(trimmed) == 2:
        return PROVINCE_ABBREV_TO_NAME.get(trimmed.upper(), trimmed)
    return trimmed


def _normalize_riding_name(value: str) -> str:
    normalized = value.strip()
    normalized = normalized.replace("—", "-").replace("–", "-").replace("−", "-")
    normalized = normalized.replace("‑", "-").replace("‐", "-")
    normalized = re.sub(r"\\s+", " ", normalized)
    return normalized.strip()


def _name_variants(value: str) -> list[str]:
    normalized = _normalize_riding_name(value)
    variants = {normalized}
    if "/" in normalized:
        parts = [part.strip() for part in normalized.split("/") if part.strip()]
        variants.update(parts)
    return list(variants)


def _pick_field(
    features: list[dict[str, Any]],
    explicit_field: str | None,
    candidates: list[str],
) -> str | None:
    if explicit_field:
        for feature in features:
            props = feature.get("properties") or {}
            if explicit_field in props:
                return explicit_field
        return None
    for field in candidates:
        for feature in features:
            props = feature.get("properties") or {}
            if field in props:
                return field
    return None


async def ingest_boundaries(
    geojson_path: Path,
    name_field: str | None,
    province_field: str | None,
    session: AsyncSession | None = None,
) -> dict[str, int]:
    stats = {"total": 0, "updated": 0, "skipped": 0}

    with geojson_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    features = payload.get("features", [])
    if not features:
        raise ValueError("GeoJSON has no features")

    resolved_name_field = _pick_field(features, name_field, DEFAULT_NAME_FIELDS)
    resolved_province_field = _pick_field(features, province_field, DEFAULT_PROVINCE_FIELDS)

    if not resolved_name_field:
        raise ValueError("Could not detect riding name field. Pass --name-field explicitly.")
    if not resolved_province_field:
        raise ValueError("Could not detect province field. Pass --province-field explicitly.")

    async def _ingest(active_session: AsyncSession) -> None:
        repo = RidingRepository(active_session)
        rep_repo = RepresentativeRepository(active_session)
        for feature in features:
            stats["total"] += 1
            props = feature.get("properties") or {}
            geometry = feature.get("geometry")
            if not geometry:
                stats["skipped"] += 1
                continue

            name_raw = props.get(resolved_name_field)
            province_raw = props.get(resolved_province_field)
            if not name_raw or not province_raw:
                stats["skipped"] += 1
                continue

            name = str(name_raw).strip()
            province = _normalize_province(str(province_raw))
            if not province:
                stats["skipped"] += 1
                continue

            riding = None
            candidate_matches = []
            for candidate in _name_variants(name):
                match = await repo.get_by_name_and_province(
                    name=candidate,
                    province=province,
                )
                if match:
                    candidate_matches.append(match)
                    rep = await rep_repo.get_by_riding_id(match.id)
                    if rep:
                        riding = match
                        break

            if riding is None and candidate_matches:
                riding = candidate_matches[0]

            if riding is None:
                riding = await repo.get_or_create(
                    name=_normalize_riding_name(name),
                    province=province,
                    fed_number=None,
                )

            await active_session.execute(
                text(
                    """
                    UPDATE ridings
                    SET geom = ST_SetSRID(ST_Multi(ST_GeomFromGeoJSON(:geojson)), 4326)
                    WHERE id = :id
                    """
                ),
                {"geojson": json.dumps(geometry), "id": riding.id},
            )
            stats["updated"] += 1

    if session is None:
        async with get_session_context() as active_session:
            await _ingest(active_session)
    else:
        await _ingest(session)

    return stats


async def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest riding boundary GeoJSON into PostGIS.")
    parser.add_argument(
        "--geojson",
        required=True,
        help="Path to GeoJSON file containing riding boundaries",
    )
    parser.add_argument(
        "--name-field",
        default=None,
        help="GeoJSON property name for riding name (auto-detected if omitted)",
    )
    parser.add_argument(
        "--province-field",
        default=None,
        help="GeoJSON property name for province name (auto-detected if omitted)",
    )
    args = parser.parse_args()

    stats = await ingest_boundaries(
        geojson_path=Path(args.geojson),
        name_field=args.name_field,
        province_field=args.province_field,
    )

    print("Boundary ingestion complete:")
    print(f"  Total:   {stats['total']}")
    print(f"  Updated: {stats['updated']}")
    print(f"  Skipped: {stats['skipped']}")


if __name__ == "__main__":
    asyncio.run(main())
