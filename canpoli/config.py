"""Application configuration loaded from environment variables."""

import os
import sys
from functools import lru_cache

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

_env_file = None
_env_file_override = os.environ.get("CANPOLI_ENV_FILE")
if _env_file_override is not None:
    _env_file = _env_file_override or None
elif "PYTEST_CURRENT_TEST" in os.environ or "pytest" in sys.modules:
    _env_file = None
else:
    _env_file = ".env"


class Settings(BaseSettings):
    """Application configuration."""

    model_config = SettingsConfigDict(
        env_file=_env_file,
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_ignore_empty=True,
    )

    # PostgreSQL Configuration - REQUIRED, no default with credentials
    database_url: str = Field(
        ...,  # Required
        description="PostgreSQL connection URL (e.g., postgresql+asyncpg://user:pass@host:port/db)",
    )
    database_pool_size: int = Field(default=5, ge=1, le=50)
    database_max_overflow: int = Field(default=10, ge=0, le=50)
    database_pool_timeout: int = Field(default=30, ge=5, le=120)
    database_pool_recycle: int = Field(default=1800, ge=300)
    database_echo: bool = False

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_lambda(self) -> bool:
        """Detect if running in AWS Lambda environment."""
        return "AWS_LAMBDA_FUNCTION_NAME" in os.environ

    # House of Commons API
    hoc_api_base_url: str = "https://www.ourcommons.ca"
    hoc_api_timeout: float = 10.0
    hoc_parliament: int = Field(default=45, ge=1)
    hoc_session: int = Field(default=1, ge=1)
    hoc_max_concurrency: int = Field(default=4, ge=1, le=20)
    hoc_min_request_interval_ms: int = Field(default=250, ge=0, le=5000)
    hoc_debates_max_sitting: int = Field(default=200, ge=1, le=1000)
    hoc_debates_lookahead: int = Field(default=10, ge=1, le=100)
    hoc_debates_max_missing: int = Field(default=20, ge=1, le=200)
    hoc_debate_languages: list[str] = Field(default_factory=lambda: ["en", "fr"])
    hoc_enable_roles: bool = True
    hoc_enable_party_standings: bool = True
    hoc_enable_votes: bool = True
    hoc_enable_petitions: bool = True
    hoc_enable_debates: bool = True
    hoc_enable_expenditures: bool = True
    hoc_enable_bills: bool = True

    # CORS Configuration
    cors_origins: list[str] = Field(
        default_factory=list,
        description="Allowed CORS origins. Empty list uses permissive defaults for development.",
    )

    # Rate Limiting
    rate_limit_per_minute: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Deprecated: use free_rate_limit_per_minute/paid_rate_limit_per_minute.",
    )
    free_rate_limit_per_minute: int = Field(default=50, ge=1, le=1000)
    paid_rate_limit_per_minute: int = Field(default=500, ge=1, le=10000)
    redis_url: str | None = Field(
        default=None,
        description="Redis URL for rate limiting and usage tracking.",
    )

    # API Keys
    api_key_hmac_secret: str | None = Field(
        default=None,
        description="Secret used to hash API keys (HMAC-SHA256).",
    )

    # Stripe Billing
    stripe_secret_key: str | None = Field(default=None)
    stripe_webhook_secret: str | None = Field(default=None)
    stripe_price_id: str | None = Field(default=None)
    stripe_checkout_success_url: str | None = Field(default=None)
    stripe_checkout_cancel_url: str | None = Field(default=None)
    stripe_portal_return_url: str | None = Field(default=None)

    # Clerk Auth
    clerk_jwks_url: str | None = Field(default=None)
    clerk_issuer: str | None = Field(default=None)
    clerk_audience: str | None = Field(default=None)

    # Sentry
    sentry_dsn: str | None = Field(default=None)
    sentry_environment: str | None = Field(
        default=None,
        description="Sentry environment (e.g., development, staging, production).",
    )
    sentry_release: str | None = Field(default=None)
    sentry_send_default_pii: bool = Field(default=False)
    sentry_traces_sample_rate: float | None = Field(default=None, ge=0.0, le=1.0)

    # Application
    environment: str = Field(
        default="development",
        description="Deployment environment (development, test, staging, production).",
    )
    debug: bool = False
    log_level: str = "INFO"

    # Lambda ingestion toggles
    enable_parliament_ingest: bool = Field(
        default=False,
        description="Enable parliamentary data ingestion in scheduled Lambda runs.",
    )
    boundary_geojson_url: str | None = Field(
        default=None,
        description="Optional GeoJSON URL for boundary refresh during ingestion.",
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
