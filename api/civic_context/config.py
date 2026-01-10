from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # AWS Configuration
    aws_region: str = "us-east-1"
    dynamodb_table_name: str = "civic-context-cache"

    # External APIs
    represent_api_base_url: str = "https://represent.opennorth.ca"
    represent_api_timeout: float = 10.0

    # OpenParliament API
    openparliament_api_base_url: str = "https://api.openparliament.ca"
    openparliament_api_timeout: float = 8.0
    openparliament_contact_email: str = "contact@example.com"
    openparliament_bills_limit: int = 5
    openparliament_votes_limit: int = 10

    # House of Commons API
    hoc_api_base_url: str = "https://www.ourcommons.ca"
    hoc_api_timeout: float = 10.0
    hoc_contact_email: str = "contact@example.com"

    # Cache Configuration
    cache_ttl_seconds: int = 3600

    # Application
    debug: bool = False
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
