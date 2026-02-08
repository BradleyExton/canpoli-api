"""Tests for ingest boundaries helpers."""

import json
from pathlib import Path

import pytest

from canpoli.cli import ingest_boundaries


def test_normalize_province():
    assert ingest_boundaries._normalize_province(None) is None
    assert ingest_boundaries._normalize_province("ON") == "Ontario"
    assert ingest_boundaries._normalize_province("35") == "Ontario"
    assert ingest_boundaries._normalize_province("  qc ") == "Quebec"
    assert ingest_boundaries._normalize_province("Unknown") == "Unknown"


def test_normalize_riding_name():
    name = " Ottawa—Centre  "
    assert ingest_boundaries._normalize_riding_name(name) == "Ottawa-Centre"


def test_name_variants():
    variants = set(ingest_boundaries._name_variants("Alpha / Beta"))
    assert variants == {"Alpha / Beta", "Alpha", "Beta"}


def test_pick_field_explicit():
    features = [{"properties": {"name": "One"}}]
    assert ingest_boundaries._pick_field(features, "name", ["other"]) == "name"
    assert ingest_boundaries._pick_field(features, "missing", ["name"]) is None


def test_pick_field_auto():
    features = [
        {"properties": {"foo": "bar"}},
        {"properties": {"district_name": "Riding"}},
    ]
    assert (
        ingest_boundaries._pick_field(features, None, ["district_name", "name"]) == "district_name"
    )


@pytest.mark.asyncio
async def test_ingest_boundaries_empty_features(tmp_path):
    payload = {"type": "FeatureCollection", "features": []}
    geojson_path = Path(tmp_path) / "empty.geojson"
    geojson_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="no features"):
        await ingest_boundaries.ingest_boundaries(
            geojson_path=geojson_path,
            name_field=None,
            province_field=None,
            session=None,
        )
