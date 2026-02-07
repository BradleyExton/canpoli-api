"""Health endpoint tests."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check_returns_ok(client: AsyncClient):
    """Health check should return ok status when database is available."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "ok"


@pytest.mark.asyncio
async def test_health_check_no_error_details(client: AsyncClient):
    """Health check response should not expose internal error details."""
    response = await client.get("/health")
    data = response.json()
    # Ensure no exception details leak through
    response_str = str(data).lower()
    assert "exception" not in response_str
    assert "traceback" not in response_str
    assert "postgresql" not in response_str
