import json
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from api.civic_context.db.cache import (
    _make_cache_key,
    get_cached_response,
    set_cached_response,
)


class TestCacheKey:
    """Tests for cache key generation."""

    def test_make_cache_key_rounds_to_4_decimals(self):
        """Test that coordinates are rounded to 4 decimal places."""
        key = _make_cache_key(45.42156789, -75.69728901)
        assert key == "45.4216,-75.6973"

    def test_make_cache_key_handles_negative_coords(self):
        """Test handling of negative coordinates."""
        key = _make_cache_key(-33.8688, 151.2093)
        assert key == "-33.8688,151.2093"


class TestGetCachedResponse:
    """Tests for cache retrieval."""

    def test_get_cached_response_hit(self):
        """Test successful cache hit."""
        mock_table = MagicMock()
        future_time = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
        mock_table.get_item.return_value = {
            "Item": {
                "cache_key": "45.4216,-75.6973",
                "response_json": json.dumps({"test": "data"}),
                "expires_at": future_time,
            }
        }

        with patch("api.civic_context.db.cache.table", mock_table):
            result = get_cached_response(45.4216, -75.6973)

        assert result == {"test": "data"}
        mock_table.get_item.assert_called_once_with(
            Key={"cache_key": "45.4216,-75.6973"}
        )

    def test_get_cached_response_miss(self):
        """Test cache miss when no item exists."""
        mock_table = MagicMock()
        mock_table.get_item.return_value = {}

        with patch("api.civic_context.db.cache.table", mock_table):
            result = get_cached_response(45.4216, -75.6973)

        assert result is None

    def test_get_cached_response_expired(self):
        """Test that expired cache entries return None."""
        mock_table = MagicMock()
        past_time = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        mock_table.get_item.return_value = {
            "Item": {
                "cache_key": "45.4216,-75.6973",
                "response_json": json.dumps({"test": "data"}),
                "expires_at": past_time,
            }
        }

        with patch("api.civic_context.db.cache.table", mock_table):
            result = get_cached_response(45.4216, -75.6973)

        assert result is None

    def test_get_cached_response_error_handling(self):
        """Test that errors return None instead of raising."""
        mock_table = MagicMock()
        mock_table.get_item.side_effect = Exception("DynamoDB error")

        with patch("api.civic_context.db.cache.table", mock_table):
            result = get_cached_response(45.4216, -75.6973)

        assert result is None


class TestSetCachedResponse:
    """Tests for cache storage."""

    def test_set_cached_response_success(self):
        """Test successful cache write."""
        mock_table = MagicMock()

        with patch("api.civic_context.db.cache.table", mock_table):
            set_cached_response(45.4216, -75.6973, {"test": "data"})

        mock_table.put_item.assert_called_once()
        call_args = mock_table.put_item.call_args
        item = call_args.kwargs["Item"]

        assert item["cache_key"] == "45.4216,-75.6973"
        assert json.loads(item["response_json"]) == {"test": "data"}
        assert "expires_at" in item
        assert "created_at" in item

    def test_set_cached_response_error_handling(self):
        """Test that write errors are logged but don't raise."""
        mock_table = MagicMock()
        mock_table.put_item.side_effect = Exception("DynamoDB error")

        with patch("api.civic_context.db.cache.table", mock_table):
            # Should not raise
            set_cached_response(45.4216, -75.6973, {"test": "data"})
