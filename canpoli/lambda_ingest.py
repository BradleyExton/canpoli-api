"""AWS Lambda handler for scheduled data ingestion."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

import urllib.request

from canpoli.cli.ingest_boundaries import ingest_boundaries
from canpoli.services.hoc_ingestion import HoCIngestionService
from canpoli.sentry import init_sentry

logger = logging.getLogger(__name__)
init_sentry()


def _download_to_temp(url: str) -> Path:
    with urllib.request.urlopen(url) as response:
        data = response.read()
    tmp = NamedTemporaryFile(delete=False, suffix=".geojson")
    tmp.write(data)
    tmp.flush()
    return Path(tmp.name)


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Run House of Commons ingestion (and optional boundary refresh)."""
    logger.info("Starting scheduled HoC ingestion")
    stats = asyncio.run(HoCIngestionService().ingest())
    logger.info("HoC ingestion complete: %s", stats)

    boundary_url = os.environ.get("BOUNDARY_GEOJSON_URL")
    if boundary_url:
        logger.info("Refreshing boundaries from %s", boundary_url)
        tmp_path = _download_to_temp(boundary_url)
        boundary_stats = asyncio.run(
            ingest_boundaries(
                geojson_path=tmp_path,
                name_field="FEDNAME",
                province_field="PRUID",
            )
        )
        logger.info("Boundary ingestion complete: %s", boundary_stats)
        return {
            "status": "ok",
            "stats": stats,
            "boundary_stats": boundary_stats,
        }

    return {"status": "ok", "stats": stats}
