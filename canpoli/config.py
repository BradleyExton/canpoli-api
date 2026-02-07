"""Application configuration loaded from environment variables."""

import os
from functools import lru_cache

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
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
    debug: bool = False
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
