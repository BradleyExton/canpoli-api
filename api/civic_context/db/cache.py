import json
from datetime import UTC, datetime, timedelta

import boto3

from api.civic_context.config import get_settings
from api.civic_context.logging_config import get_logger

logger = get_logger()
settings = get_settings()

# Create DynamoDB client using settings
dynamodb = boto3.resource("dynamodb", region_name=settings.aws_region)
table = dynamodb.Table(settings.dynamodb_table_name)


def _make_cache_key(lat: float, lng: float) -> str:
    """Create a cache key from coordinates (rounded to 4 decimal places)."""
    return f"{lat:.4f},{lng:.4f}"


def get_cached_response(lat: float, lng: float) -> dict | None:
    """Get cached response for a location."""
    cache_key = _make_cache_key(lat, lng)

    try:
        response = table.get_item(Key={"cache_key": cache_key})
        item = response.get("Item")

        if not item:
            return None

        # Check if expired
        expires_at = datetime.fromisoformat(item["expires_at"])
        if expires_at < datetime.now(UTC):
            return None

        result: dict = json.loads(item["response_json"])
        return result

    except Exception as e:
        logger.warning(f"Cache read error: {e}")
        return None


def set_cached_response(lat: float, lng: float, response_data: dict) -> None:
    """Cache a response for a location."""
    cache_key = _make_cache_key(lat, lng)
    expires_at = datetime.now(UTC) + timedelta(seconds=settings.cache_ttl_seconds)

    try:
        table.put_item(
            Item={
                "cache_key": cache_key,
                "response_json": json.dumps(response_data),
                "expires_at": expires_at.isoformat(),
                "created_at": datetime.now(UTC).isoformat(),
            }
        )
    except Exception as e:
        logger.warning(f"Cache write error: {e}")
