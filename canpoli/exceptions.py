"""Custom exceptions for the application."""


class CanPoliError(Exception):
    """Base exception for CanPoli API."""

    pass


class IngestionError(CanPoliError):
    """Error during data ingestion from external sources."""

    pass


class RepositoryError(CanPoliError):
    """Error in repository layer during database operations."""

    pass


class ConfigurationError(CanPoliError):
    """Error in application configuration."""

    pass
