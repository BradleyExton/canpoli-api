"""Parties endpoint tests."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_parties_empty(client: AsyncClient):
    """List parties returns empty list when no data."""
    response = await client.get("/v1/parties")
    assert response.status_code == 200
    data = response.json()
    assert data["parties"] == []
    assert data["total"] == 0
    assert data["limit"] == 50
    assert data["offset"] == 0
