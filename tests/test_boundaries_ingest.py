"""Boundary ingestion tests."""

from pathlib import Path
import json

import pytest

from sqlalchemy import text

from canpoli.cli.ingest_boundaries import ingest_boundaries
from canpoli.repositories import RidingRepository


@pytest.mark.asyncio
async def test_ingest_boundaries_updates_geom(postgis_session):
    """Ingest boundaries sets geometry for a riding."""
    repo = RidingRepository(postgis_session)
    await repo.get_or_create(name="Test Riding", province="Ontario", fed_number=None)
    await postgis_session.commit()

    geojson_path = Path(__file__).parent / "fixtures" / "riding_boundaries.geojson"
    stats = await ingest_boundaries(
        geojson_path=geojson_path,
        name_field=None,
        province_field=None,
        session=postgis_session,
    )

    assert stats["total"] == 1
    assert stats["updated"] == 1
    assert stats["skipped"] == 0

    riding = await repo.get_by_name_and_province("Test Riding", "Ontario")
    assert riding is not None
    result = await postgis_session.execute(
        text("SELECT ST_IsValid(geom) FROM ridings WHERE id = :id"),
        {"id": riding.id},
    )
    assert result.scalar_one() is True


@pytest.mark.asyncio
async def test_ingest_boundaries_missing_fields(postgis_session, tmp_path):
    """Ingest boundaries skips invalid features."""
    payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"district_name": "No Geometry", "province": "Ontario"},
                "geometry": None,
            },
            {
                "type": "Feature",
                "properties": {"province": "Ontario"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [-75.0, 45.0],
                            [-74.0, 45.0],
                            [-74.0, 46.0],
                            [-75.0, 46.0],
                            [-75.0, 45.0],
                        ]
                    ],
                },
            },
        ],
    }
    geojson_path = tmp_path / "missing.geojson"
    geojson_path.write_text(json.dumps(payload), encoding="utf-8")

    stats = await ingest_boundaries(
        geojson_path=geojson_path,
        name_field=None,
        province_field=None,
        session=postgis_session,
    )

    assert stats["total"] == 2
    assert stats["updated"] == 0
    assert stats["skipped"] == 2


@pytest.mark.asyncio
async def test_ingest_boundaries_normalizes_province(postgis_session, tmp_path):
    """Ingest boundaries normalizes province abbreviations."""
    payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"district_name": "Abbrev Riding", "province": "ON"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [-75.0, 45.0],
                            [-74.0, 45.0],
                            [-74.0, 46.0],
                            [-75.0, 46.0],
                            [-75.0, 45.0],
                        ]
                    ],
                },
            }
        ],
    }
    geojson_path = tmp_path / "abbr.geojson"
    geojson_path.write_text(json.dumps(payload), encoding="utf-8")

    stats = await ingest_boundaries(
        geojson_path=geojson_path,
        name_field=None,
        province_field=None,
        session=postgis_session,
    )

    assert stats["total"] == 1
    assert stats["updated"] == 1
    assert stats["skipped"] == 0

    repo = RidingRepository(postgis_session)
    riding = await repo.get_by_name_and_province("Abbrev Riding", "Ontario")
    assert riding is not None


@pytest.mark.asyncio
async def test_ingest_boundaries_normalizes_pruid(postgis_session, tmp_path):
    """Ingest boundaries normalizes province PRUID codes."""
    payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"district_name": "PRUID Riding", "PRUID": "35"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [-75.0, 45.0],
                            [-74.0, 45.0],
                            [-74.0, 46.0],
                            [-75.0, 46.0],
                            [-75.0, 45.0],
                        ]
                    ],
                },
            }
        ],
    }
    geojson_path = tmp_path / "pruid.geojson"
    geojson_path.write_text(json.dumps(payload), encoding="utf-8")

    stats = await ingest_boundaries(
        geojson_path=geojson_path,
        name_field=None,
        province_field=None,
        session=postgis_session,
    )

    assert stats["total"] == 1
    assert stats["updated"] == 1
    assert stats["skipped"] == 0

    repo = RidingRepository(postgis_session)
    riding = await repo.get_by_name_and_province("PRUID Riding", "Ontario")
    assert riding is not None


@pytest.mark.asyncio
async def test_ingest_boundaries_detects_fields_after_first_feature(
    postgis_session,
    tmp_path,
):
    """Ingest boundaries detects fields even if first feature is missing them."""
    payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"province": "Ontario"},
                "geometry": None,
            },
            {
                "type": "Feature",
                "properties": {"district_name": "Later Riding", "province": "Ontario"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [-75.0, 45.0],
                            [-74.0, 45.0],
                            [-74.0, 46.0],
                            [-75.0, 46.0],
                            [-75.0, 45.0],
                        ]
                    ],
                },
            },
        ],
    }
    geojson_path = tmp_path / "later.geojson"
    geojson_path.write_text(json.dumps(payload), encoding="utf-8")

    stats = await ingest_boundaries(
        geojson_path=geojson_path,
        name_field=None,
        province_field=None,
        session=postgis_session,
    )

    assert stats["total"] == 2
    assert stats["updated"] == 1
    assert stats["skipped"] == 1
