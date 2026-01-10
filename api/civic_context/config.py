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

    # External API
    represent_api_base_url: str = "https://represent.opennorth.ca"
    represent_api_timeout: float = 10.0

    # Cache Configuration
    cache_ttl_seconds: int = 3600

    # Application
    debug: bool = False
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
