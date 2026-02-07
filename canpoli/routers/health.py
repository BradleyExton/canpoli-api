"""Health check endpoint."""

import logging

from fastapi import APIRouter
from sqlalchemy import text

from canpoli.database import async_session_factory

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check() -> dict:
    """Check if the API and database are running."""
    db_status = "unknown"

    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
            db_status = "ok"
    except Exception as e:
        # Log the actual error for debugging (not exposed to client)
        logger.error("Health check database error: %s", e, exc_info=True)
        # Return generic status to client - no internal details
        db_status = "error"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "database": db_status,
    }
