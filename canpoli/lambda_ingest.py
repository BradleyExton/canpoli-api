"""AWS Lambda handler for scheduled data ingestion."""

from __future__ import annotations

import asyncio
import logging
import urllib.request
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from canpoli.cli.ingest_boundaries import ingest_boundaries
from canpoli.config import get_settings
from canpoli.sentry import init_sentry
from canpoli.services.hoc_ingestion import HoCIngestionService
from canpoli.services.hoc_parliament_ingestion import HoCParliamentIngestionService

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
    settings = get_settings()
    logger.info("Starting scheduled HoC ingestion")
    stats = asyncio.run(HoCIngestionService().ingest())
    logger.info("HoC ingestion complete: %s", stats)

    parliament_ingest = settings.enable_parliament_ingest
    if parliament_ingest:
        logger.info("Starting parliamentary ingestion")
        parliament_stats = asyncio.run(HoCParliamentIngestionService().ingest())
        logger.info("Parliamentary ingestion complete: %s", parliament_stats)
    else:
        parliament_stats = None

    boundary_url = settings.boundary_geojson_url
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
            "parliament_stats": parliament_stats,
            "boundary_stats": boundary_stats,
        }

    return {"status": "ok", "stats": stats, "parliament_stats": parliament_stats}
