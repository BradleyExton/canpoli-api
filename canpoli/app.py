"""FastAPI application factory."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from canpoli.config import Settings, get_settings
from canpoli.logging_config import setup_logging
from canpoli.rate_limit import increment_usage
from canpoli.routers import (
    account_router,
    billing_router,
    bills_router,
    debates_router,
    expenditures_router,
    health_router,
    parties_router,
    party_standings_router,
    petitions_router,
    representatives_router,
    ridings_router,
    roles_router,
    votes_router,
)
from canpoli.sentry import init_sentry


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = settings or get_settings()

    # Initialize logging and error tracking before app setup
    setup_logging()
    init_sentry()

    logger = logging.getLogger(__name__)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
        """Application lifespan events."""
        logger.info("CanPoli API starting up")
        yield
        logger.info("CanPoli API shutting down")

    app = FastAPI(
        title="CanPoli API",
        description="Canadian Political Data API - Federal MPs, Ridings, and Parties",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Configure CORS based on settings
    if settings.cors_origins:
        # Production: use configured origins with credentials
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "X-API-Key"],
        )
        logger.info("CORS configured with origins: %s", settings.cors_origins)
    else:
        # Development fallback: permissive but no credentials
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=False,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Content-Type", "X-API-Key", "Authorization"],
        )
        logger.warning("CORS configured with wildcard origins (development mode)")

    # Health check (no version prefix)
    app.include_router(health_router)

    # Account and billing endpoints
    app.include_router(account_router)
    app.include_router(billing_router)

    # Unversioned API endpoints
    app.include_router(representatives_router, prefix="/representatives")
    app.include_router(ridings_router, prefix="/ridings")
    app.include_router(parties_router, prefix="/parties")
    app.include_router(roles_router, prefix="/roles")
    app.include_router(party_standings_router, prefix="/party-standings")
    app.include_router(bills_router, prefix="/bills")
    app.include_router(votes_router, prefix="/votes")
    app.include_router(petitions_router, prefix="/petitions")
    app.include_router(debates_router, prefix="/debates")
    app.include_router(expenditures_router, prefix="/expenditures")

    # Backwards-compatible versioned API endpoints
    app.include_router(
        representatives_router, prefix="/v1/representatives", include_in_schema=False
    )
    app.include_router(ridings_router, prefix="/v1/ridings", include_in_schema=False)
    app.include_router(parties_router, prefix="/v1/parties", include_in_schema=False)
    app.include_router(roles_router, prefix="/v1/roles", include_in_schema=False)
    app.include_router(
        party_standings_router, prefix="/v1/party-standings", include_in_schema=False
    )
    app.include_router(bills_router, prefix="/v1/bills", include_in_schema=False)
    app.include_router(votes_router, prefix="/v1/votes", include_in_schema=False)
    app.include_router(petitions_router, prefix="/v1/petitions", include_in_schema=False)
    app.include_router(debates_router, prefix="/v1/debates", include_in_schema=False)
    app.include_router(expenditures_router, prefix="/v1/expenditures", include_in_schema=False)

    @app.middleware("http")
    async def usage_middleware(request: Request, call_next):
        response = await call_next(request)
        if response.status_code < 400:
            await increment_usage(request)
        return response

    return app
