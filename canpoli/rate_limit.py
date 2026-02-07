"""Rate limiting configuration."""

from slowapi import Limiter
from slowapi.util import get_remote_address


def get_limiter() -> Limiter:
    """Get rate limiter with configured limits."""
    from canpoli.config import get_settings

    settings = get_settings()
    return Limiter(
        key_func=get_remote_address,
        default_limits=[f"{settings.rate_limit_per_minute}/minute"],
    )
