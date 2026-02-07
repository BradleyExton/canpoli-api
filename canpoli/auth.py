"""Authentication dependencies for Clerk JWTs."""

import asyncio
from typing import Any

import jwt
from fastapi import Depends, Header, HTTPException
from jwt import PyJWKClient
from sqlalchemy.ext.asyncio import AsyncSession

from canpoli.config import get_settings
from canpoli.database import get_session
from canpoli.repositories import UserRepository


_jwks_client: PyJWKClient | None = None


def _get_jwks_client(jwks_url: str) -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(jwks_url)
    return _jwks_client


async def _verify_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    if not settings.clerk_jwks_url or not settings.clerk_issuer or not settings.clerk_audience:
        raise HTTPException(status_code=500, detail="Clerk auth is not configured")

    client = _get_jwks_client(settings.clerk_jwks_url)
    try:
        signing_key = await asyncio.to_thread(client.get_signing_key_from_jwt, token)
        payload = await asyncio.to_thread(
            jwt.decode,
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.clerk_audience,
            issuer=settings.clerk_issuer,
        )
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token") from None


def _extract_email(claims: dict[str, Any]) -> str | None:
    if "email" in claims:
        return claims["email"]
    if "email_address" in claims:
        return claims["email_address"]
    if "primary_email_address" in claims:
        return claims["primary_email_address"]
    return None


async def get_current_user(
    session: AsyncSession = Depends(get_session),
    authorization: str | None = Header(default=None),
):
    """Validate Clerk JWT and upsert user."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing bearer token")

    claims = await _verify_token(token)
    auth_user_id = claims.get("sub")
    if not auth_user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    email = _extract_email(claims)
    repo = UserRepository(session)
    user = await repo.get_by_auth_user_id(auth_user_id)
    if not user:
        user = await repo.create(
            auth_provider="clerk",
            auth_user_id=auth_user_id,
            email=email,
        )
    else:
        if email and user.email != email:
            user.email = email
            await session.flush()

    return user
