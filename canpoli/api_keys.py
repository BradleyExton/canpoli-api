"""API key generation and hashing utilities."""

import hashlib
import hmac
import secrets

from canpoli.config import get_settings

API_KEY_PREFIX = "cpk_live_"
API_KEY_PREFIX_LEN = 12


def require_api_key_secret() -> str:
    """Ensure API key secret is configured."""
    settings = get_settings()
    if not settings.api_key_hmac_secret:
        raise RuntimeError("API_KEY_HMAC_SECRET is not configured")
    return settings.api_key_hmac_secret


def generate_api_key() -> tuple[str, str, str]:
    """Generate a new API key and return (plaintext, prefix, hash)."""
    secret = require_api_key_secret()
    token = secrets.token_urlsafe(32)
    plaintext = f"{API_KEY_PREFIX}{token}"
    key_prefix = plaintext[:API_KEY_PREFIX_LEN]
    key_hash = hash_api_key(plaintext, secret)
    return plaintext, key_prefix, key_hash


def hash_api_key(plaintext: str, secret: str | None = None) -> str:
    """Hash an API key using HMAC-SHA256."""
    secret_value = secret or require_api_key_secret()
    digest = hmac.new(
        secret_value.encode("utf-8"),
        plaintext.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return digest


def mask_api_key(key_prefix: str) -> str:
    """Return a masked representation for display."""
    return f"{key_prefix}..."
