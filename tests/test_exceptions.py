"""Tests for custom exceptions."""

from canpoli.exceptions import CanPoliError, ConfigurationError, IngestionError, RepositoryError


def test_exception_hierarchy():
    assert issubclass(IngestionError, CanPoliError)
    assert issubclass(RepositoryError, CanPoliError)
    assert issubclass(ConfigurationError, CanPoliError)
