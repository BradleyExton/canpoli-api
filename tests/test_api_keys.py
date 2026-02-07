"""Tests for API key helpers."""

import pytest

from canpoli import api_keys
from canpoli.config import get_settings


def test_require_api_key_secret_missing(monkeypatch):
    """Missing API key secret raises a clear error."""
    monkeypatch.setenv("API_KEY_HMAC_SECRET", "")
    get_settings.cache_clear()

    with pytest.raises(RuntimeError, match="API_KEY_HMAC_SECRET"):
        api_keys.require_api_key_secret()


def test_generate_and_hash_api_key(monkeypatch):
    """Generated keys include prefix and valid HMAC hash."""
    monkeypatch.setenv("API_KEY_HMAC_SECRET", "test-secret")
    get_settings.cache_clear()

    plaintext, prefix, key_hash = api_keys.generate_api_key()

    assert plaintext.startswith(api_keys.API_KEY_PREFIX)
    assert prefix == plaintext[: api_keys.API_KEY_PREFIX_LEN]
    assert key_hash == api_keys.hash_api_key(plaintext, "test-secret")
    assert len(key_hash) == 64


def test_mask_api_key():
    """Masking keeps prefix and hides the rest."""
    assert api_keys.mask_api_key("cpk_live_1234") == "cpk_live_1234..."
