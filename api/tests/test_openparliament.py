from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from api.civic_context.services.openparliament import (
    _fetch_committees,
    _fetch_recent_votes,
    _fetch_sponsored_bills,
    _normalize_name,
    _search_politician,
    get_parliamentary_activity,
)


class TestNormalizeName:
    """Tests for name normalization."""

    def test_normalize_plain_name(self):
        """Test name without honorifics."""
        assert _normalize_name("John Doe") == "John Doe"

    def test_normalize_hon(self):
        """Test removing Hon. prefix."""
        assert _normalize_name("Hon. John Doe") == "John Doe"

    def test_normalize_right_hon(self):
        """Test removing Right Hon. prefix."""
        assert _normalize_name("Right Hon. John Doe") == "John Doe"

    def test_normalize_the_hon(self):
        """Test removing The Hon. prefix."""
        assert _normalize_name("The Hon. John Doe") == "John Doe"

    def test_normalize_dr(self):
        """Test removing Dr. prefix."""
        assert _normalize_name("Dr. Jane Smith") == "Jane Smith"


@pytest.mark.asyncio
class TestSearchPolitician:
    """Tests for politician search."""

    async def test_search_found(self):
        """Test successful politician search."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "objects": [
                {
                    "name": "John Doe",
                    "url": "/politicians/john-doe/",
                    "current_riding": {"name": {"en": "Test Riding"}},
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        result = await _search_politician(mock_client, "John Doe")

        assert result == "john-doe"

    async def test_search_not_found(self):
        """Test politician not found returns None."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"objects": []}
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        result = await _search_politician(mock_client, "Nonexistent Person")

        assert result is None

    async def test_search_prefers_current_mp(self):
        """Test that current MPs are preferred over former MPs."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "objects": [
                {
                    "name": "John Doe Sr",
                    "url": "/politicians/john-doe-sr/",
                    "current_riding": None,  # Former MP
                },
                {
                    "name": "John Doe Jr",
                    "url": "/politicians/john-doe-jr/",
                    "current_riding": {"name": {"en": "Test Riding"}},  # Current MP
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        result = await _search_politician(mock_client, "John Doe")

        assert result == "john-doe-jr"

    async def test_search_with_honorific(self):
        """Test searching with name that has honorific."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "objects": [
                {
                    "name": "John Doe",
                    "url": "/politicians/john-doe/",
                    "current_riding": {"name": {"en": "Test Riding"}},
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        result = await _search_politician(mock_client, "Hon. John Doe")

        assert result == "john-doe"
        # Verify the API was called with normalized name
        mock_client.get.assert_called_with("/politicians/", params={"name": "John Doe"})

    async def test_search_error_returns_none(self):
        """Test that search errors return None gracefully."""
        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

        result = await _search_politician(mock_client, "John Doe")

        assert result is None


@pytest.mark.asyncio
class TestFetchSponsoredBills:
    """Tests for bill fetching."""

    async def test_fetch_bills_success(self):
        """Test successful bill fetching."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "objects": [
                {
                    "number": "C-123",
                    "name": {"en": "Test Bill", "fr": "Projet de loi test"},
                    "introduced": "2024-01-15",
                    "session": "44-1",
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        result = await _fetch_sponsored_bills(mock_client, "john-doe")

        assert len(result) == 1
        assert result[0].number == "C-123"
        assert result[0].name == "Test Bill"
        assert result[0].introduced == "2024-01-15"
        assert result[0].session == "44-1"

    async def test_fetch_bills_empty(self):
        """Test MP with no sponsored bills."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"objects": []}
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        result = await _fetch_sponsored_bills(mock_client, "john-doe")

        assert result == []

    async def test_fetch_bills_rate_limited(self):
        """Test rate limiting returns empty list."""
        mock_response = MagicMock()
        mock_response.status_code = 429

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        result = await _fetch_sponsored_bills(mock_client, "john-doe")

        assert result == []

    async def test_fetch_bills_timeout(self):
        """Test timeout returns empty list."""
        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

        result = await _fetch_sponsored_bills(mock_client, "john-doe")

        assert result == []


@pytest.mark.asyncio
class TestFetchRecentVotes:
    """Tests for vote fetching."""

    async def test_fetch_votes_success(self):
        """Test successful vote fetching."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "objects": [
                {
                    "ballot": "Yes",
                    "vote_url": "/votes/44-1/123/",
                    "politician_url": "/politicians/john-doe/",
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        result = await _fetch_recent_votes(mock_client, "john-doe")

        assert len(result) == 1
        assert result[0].session == "44-1"
        assert result[0].vote_number == 123
        assert result[0].mp_vote == "Yes"
        assert result[0].vote_url == "https://openparliament.ca/votes/44-1/123/"

    async def test_fetch_votes_timeout(self):
        """Test timeout returns empty list."""
        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

        result = await _fetch_recent_votes(mock_client, "john-doe")

        assert result == []


@pytest.mark.asyncio
class TestFetchCommittees:
    """Tests for committee fetching."""

    async def test_fetch_committees_success(self):
        """Test successful committee fetching."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "memberships": [
                {
                    "committee": {
                        "name": {"en": "Standing Committee on Finance", "fr": "Finances"},
                        "short_name": {"en": "FINA", "fr": "FINA"},
                    }
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        result = await _fetch_committees(mock_client, "john-doe")

        assert len(result) == 1
        assert result[0].name == "Standing Committee on Finance"
        assert result[0].acronym == "FINA"

    async def test_fetch_committees_no_memberships(self):
        """Test MP with no committee memberships."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"memberships": []}
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        result = await _fetch_committees(mock_client, "john-doe")

        assert result == []

    async def test_fetch_committees_timeout(self):
        """Test timeout returns empty list."""
        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

        result = await _fetch_committees(mock_client, "john-doe")

        assert result == []


@pytest.mark.asyncio
class TestGetParliamentaryActivity:
    """Tests for the main orchestration function."""

    async def test_mp_not_found(self):
        """Test returns None when MP not found."""
        with patch(
            "api.civic_context.services.openparliament.httpx.AsyncClient"
        ) as mock_client_class:
            mock_response = MagicMock()
            mock_response.json.return_value = {"objects": []}
            mock_response.raise_for_status = MagicMock()

            mock_client = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await get_parliamentary_activity("Unknown Person")

            assert result is None

    async def test_full_activity_fetch(self):
        """Test complete flow with all data."""
        with patch(
            "api.civic_context.services.openparliament.httpx.AsyncClient"
        ) as mock_client_class:
            mock_client = MagicMock()

            # Setup responses for different endpoints
            async def get_response(url, params=None):
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.raise_for_status = MagicMock()

                if url == "/politicians/":
                    mock_response.json.return_value = {
                        "objects": [
                            {
                                "name": "John Doe",
                                "url": "/politicians/john-doe/",
                                "current_riding": {"name": {"en": "Test Riding"}},
                            }
                        ]
                    }
                elif url == "/politicians/john-doe/":
                    mock_response.json.return_value = {
                        "memberships": [
                            {
                                "committee": {
                                    "name": {"en": "Finance"},
                                    "short_name": {"en": "FINA"},
                                }
                            }
                        ]
                    }
                elif url == "/bills/":
                    mock_response.json.return_value = {
                        "objects": [
                            {
                                "number": "C-123",
                                "name": {"en": "Test Bill"},
                                "introduced": "2024-01-15",
                                "session": "44-1",
                            }
                        ]
                    }
                elif url == "/votes/ballots/":
                    mock_response.json.return_value = {
                        "objects": [
                            {
                                "ballot": "Yes",
                                "vote_url": "/votes/44-1/123/",
                                "politician_url": "/politicians/john-doe/",
                            }
                        ]
                    }
                else:
                    mock_response.json.return_value = {}

                return mock_response

            mock_client.get = AsyncMock(side_effect=get_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await get_parliamentary_activity("John Doe")

            assert result is not None
            assert result.openparliament_url == "john-doe"
            assert len(result.bills_sponsored) == 1
            assert len(result.recent_votes) == 1
            assert len(result.committees) == 1

    async def test_partial_failure_still_returns_data(self):
        """Test that failure in one request doesn't fail others."""
        with patch(
            "api.civic_context.services.openparliament.httpx.AsyncClient"
        ) as mock_client_class:
            mock_client = MagicMock()

            async def get_response(url, params=None):
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.raise_for_status = MagicMock()

                if url == "/politicians/":
                    mock_response.json.return_value = {
                        "objects": [
                            {
                                "name": "John Doe",
                                "url": "/politicians/john-doe/",
                                "current_riding": {"name": {"en": "Test Riding"}},
                            }
                        ]
                    }
                elif url == "/bills/":
                    # Bills request fails
                    raise httpx.TimeoutException("timeout")
                elif url == "/votes/ballots/":
                    mock_response.json.return_value = {
                        "objects": [
                            {
                                "ballot": "Yes",
                                "vote_url": "/votes/44-1/123/",
                                "politician_url": "/politicians/john-doe/",
                            }
                        ]
                    }
                elif url == "/politicians/john-doe/":
                    mock_response.json.return_value = {
                        "memberships": [
                            {
                                "committee": {
                                    "name": {"en": "Finance"},
                                    "short_name": {"en": "FINA"},
                                }
                            }
                        ]
                    }
                else:
                    mock_response.json.return_value = {}

                return mock_response

            mock_client.get = AsyncMock(side_effect=get_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await get_parliamentary_activity("John Doe")

            # Should still get data despite bills failing
            assert result is not None
            assert result.bills_sponsored == []  # Failed, so empty
            assert len(result.recent_votes) == 1  # Succeeded
            assert len(result.committees) == 1  # Succeeded
