"""FastAPI application entry point."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from canpoli.config import get_settings
from canpoli.logging_config import setup_logging
from canpoli.rate_limit import get_limiter
from canpoli.routers import (
    health_router,
    parties_router,
    representatives_router,
    ridings_router,
)

# Initialize logging before anything else
setup_logging()

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
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
        allow_methods=["GET", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    logger.info("CORS configured with origins: %s", settings.cors_origins)
else:
    # Development fallback: permissive but no credentials
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["GET", "OPTIONS"],
        allow_headers=["Content-Type"],
    )
    logger.warning("CORS configured with wildcard origins (development mode)")

# Configure rate limiting
limiter = get_limiter()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Health check (no version prefix)
app.include_router(health_router)

# Versioned API endpoints
app.include_router(representatives_router)
app.include_router(ridings_router)
app.include_router(parties_router)
