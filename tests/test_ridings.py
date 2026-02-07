"""Ridings endpoint tests."""

import pytest
from httpx import AsyncClient

from canpoli.models import Riding
from canpoli.repositories import RidingRepository


@pytest.mark.asyncio
async def test_list_ridings_empty(client: AsyncClient):
    """List ridings returns empty list when no data."""
    response = await client.get("/v1/ridings")
    assert response.status_code == 200
    data = response.json()
    assert data["ridings"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_list_ridings_pagination_params(client: AsyncClient):
    """List ridings respects pagination parameters."""
    response = await client.get("/v1/ridings?limit=10&offset=5")
    assert response.status_code == 200
    data = response.json()
    assert data["limit"] == 10
    assert data["offset"] == 5


@pytest.mark.asyncio
async def test_list_ridings_invalid_limit(client: AsyncClient):
    """List ridings rejects invalid limit values."""
    response = await client.get("/v1/ridings?limit=200")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_riding_not_found(client: AsyncClient):
    """Get riding returns 404 for non-existent ID."""
    response = await client.get("/v1/ridings/99999")
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


@pytest.mark.asyncio
async def test_get_by_name_and_province_case_insensitive(test_session):
    """Repository lookup matches riding name/province case-insensitively."""
    riding = Riding(name="Ottawa Centre", province="Ontario", fed_number=1)
    test_session.add(riding)
    await test_session.commit()

    repo = RidingRepository(test_session)
    found = await repo.get_by_name_and_province(name="ottawa centre", province="ontario")
    assert found is not None
    assert found.id == riding.id


@pytest.mark.asyncio
async def test_get_or_create_same_name_different_province(test_session):
    """Repository get_or_create does not conflate provinces."""
    repo = RidingRepository(test_session)
    riding_on = await repo.get_or_create(
        name="Springfield",
        province="Ontario",
        fed_number=None,
    )
    riding_mb = await repo.get_or_create(
        name="Springfield",
        province="Manitoba",
        fed_number=None,
    )
    assert riding_on.id != riding_mb.id
