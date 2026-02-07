"""Tests for authentication helpers."""

import pytest
from fastapi import HTTPException

from canpoli import auth
from canpoli.config import get_settings


@pytest.mark.asyncio
async def test_verify_token_missing_config(monkeypatch):
    """Missing Clerk configuration returns 500."""
    monkeypatch.setenv("CLERK_JWKS_URL", "")
    monkeypatch.setenv("CLERK_ISSUER", "")
    monkeypatch.setenv("CLERK_AUDIENCE", "")
    get_settings.cache_clear()

    with pytest.raises(HTTPException) as excinfo:
        await auth._verify_token("token")

    assert excinfo.value.status_code == 500


@pytest.mark.asyncio
async def test_verify_token_valid(monkeypatch):
    """Valid tokens return decoded claims."""
    monkeypatch.setenv("CLERK_JWKS_URL", "https://example.com/jwks.json")
    monkeypatch.setenv("CLERK_ISSUER", "https://issuer.example")
    monkeypatch.setenv("CLERK_AUDIENCE", "audience")
    get_settings.cache_clear()

    class DummyKey:
        def __init__(self):
            self.key = "public-key"

    class DummyClient:
        def get_signing_key_from_jwt(self, token):
            return DummyKey()

    monkeypatch.setattr(auth, "_get_jwks_client", lambda _url: DummyClient())
    monkeypatch.setattr(auth.jwt, "decode", lambda *args, **kwargs: {"sub": "user-1"})

    claims = await auth._verify_token("token")
    assert claims["sub"] == "user-1"


@pytest.mark.asyncio
async def test_verify_token_invalid(monkeypatch):
    """Invalid tokens raise 401."""
    monkeypatch.setenv("CLERK_JWKS_URL", "https://example.com/jwks.json")
    monkeypatch.setenv("CLERK_ISSUER", "https://issuer.example")
    monkeypatch.setenv("CLERK_AUDIENCE", "audience")
    get_settings.cache_clear()

    class DummyKey:
        def __init__(self):
            self.key = "public-key"

    class DummyClient:
        def get_signing_key_from_jwt(self, token):
            return DummyKey()

    monkeypatch.setattr(auth, "_get_jwks_client", lambda _url: DummyClient())

    def _raise(*_args, **_kwargs):
        raise ValueError("bad token")

    monkeypatch.setattr(auth.jwt, "decode", _raise)

    with pytest.raises(HTTPException) as excinfo:
        await auth._verify_token("token")

    assert excinfo.value.status_code == 401


def test_extract_email_priority():
    """Email extraction prefers explicit email fields in order."""
    assert auth._extract_email({"email": "a@b.com"}) == "a@b.com"
    assert auth._extract_email({"email_address": "b@c.com"}) == "b@c.com"
    assert auth._extract_email({"primary_email_address": "c@d.com"}) == "c@d.com"
    assert auth._extract_email({}) is None


@pytest.mark.asyncio
async def test_get_current_user_creates_and_updates(test_session, monkeypatch):
    """Current user is created on first auth and updated on email change."""
    async def _verify_one(_token):
        return {"sub": "user-123", "email": "one@example.com"}

    monkeypatch.setattr(auth, "_verify_token", _verify_one)

    user = await auth.get_current_user(
        session=test_session,
        authorization="Bearer token",
    )
    assert user.auth_user_id == "user-123"
    assert user.email == "one@example.com"

    async def _verify_two(_token):
        return {"sub": "user-123", "email": "two@example.com"}

    monkeypatch.setattr(auth, "_verify_token", _verify_two)
    updated_user = await auth.get_current_user(
        session=test_session,
        authorization="Bearer token",
    )
    assert updated_user.id == user.id
    assert updated_user.email == "two@example.com"


@pytest.mark.asyncio
async def test_get_current_user_missing_bearer(test_session):
    """Missing or malformed bearer tokens are rejected."""
    with pytest.raises(HTTPException) as excinfo:
        await auth.get_current_user(session=test_session, authorization=None)
    assert excinfo.value.status_code == 401

    with pytest.raises(HTTPException) as excinfo:
        await auth.get_current_user(session=test_session, authorization="Token abc")
    assert excinfo.value.status_code == 401
