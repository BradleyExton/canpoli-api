"""Representatives endpoint tests."""

import pytest
from httpx import AsyncClient

from canpoli.models import Representative, Riding
from canpoli.repositories import RidingRepository


@pytest.mark.asyncio
async def test_list_representatives_empty(client: AsyncClient):
    """List representatives returns empty list when no data."""
    response = await client.get("/v1/representatives")
    assert response.status_code == 200
    data = response.json()
    assert data["representatives"] == []
    assert data["total"] == 0
    assert data["limit"] == 20
    assert data["offset"] == 0


@pytest.mark.asyncio
async def test_list_representatives_pagination_params(client: AsyncClient):
    """List representatives respects pagination parameters."""
    response = await client.get("/v1/representatives?limit=10&offset=5")
    assert response.status_code == 200
    data = response.json()
    assert data["limit"] == 10
    assert data["offset"] == 5


@pytest.mark.asyncio
async def test_list_representatives_invalid_limit(client: AsyncClient):
    """List representatives rejects invalid limit values."""
    # Limit too high
    response = await client.get("/v1/representatives?limit=200")
    assert response.status_code == 422

    # Limit too low
    response = await client.get("/v1/representatives?limit=0")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_representative_not_found(client: AsyncClient):
    """Get representative returns 404 for non-existent ID."""
    response = await client.get("/v1/representatives/99999")
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


@pytest.mark.asyncio
async def test_lookup_representative_not_implemented(client: AsyncClient):
    """Lookup representative returns 501 Not Implemented."""
    response = await client.get("/v1/representatives/lookup?postal_code=K1A0A6")
    assert response.status_code == 501


@pytest.mark.asyncio
async def test_lookup_representative_missing_inputs(client: AsyncClient):
    """Lookup representative rejects missing inputs."""
    response = await client.get("/v1/representatives/lookup")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_lookup_representative_both_inputs(client: AsyncClient):
    """Lookup representative rejects postal code with lat/lng."""
    response = await client.get(
        "/v1/representatives/lookup?postal_code=K1A0A6&lat=45.4&lng=-75.7"
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_lookup_representative_partial_coordinates(client: AsyncClient):
    """Lookup representative rejects partial coordinates."""
    response = await client.get("/v1/representatives/lookup?lat=45.4")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_lookup_representative_invalid_lat(client: AsyncClient):
    """Lookup representative rejects invalid latitude."""
    response = await client.get("/v1/representatives/lookup?lat=91&lng=-75.7")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_lookup_representative_invalid_lng(client: AsyncClient):
    """Lookup representative rejects invalid longitude."""
    response = await client.get("/v1/representatives/lookup?lat=45.4&lng=181")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_lookup_representative_latlng_success(
    client: AsyncClient,
    test_session,
    monkeypatch,
):
    """Lookup representative returns representative for valid coordinates."""
    riding = Riding(name="Ottawa Centre", province="Ontario", fed_number=1)
    test_session.add(riding)
    await test_session.flush()

    rep = Representative(
        hoc_id=1001,
        name="Test Representative",
        first_name="Test",
        last_name="Representative",
        riding_id=riding.id,
        is_active=True,
    )
    test_session.add(rep)
    await test_session.commit()

    async def fake_get_by_point(self, lat, lng):
        return riding

    monkeypatch.setattr(RidingRepository, "get_by_point", fake_get_by_point)

    response = await client.get("/v1/representatives/lookup?lat=45.4&lng=-75.7")
    assert response.status_code == 200
    data = response.json()
    assert data["hoc_id"] == 1001
    assert data["riding"]["name"] == "Ottawa Centre"


@pytest.mark.asyncio
async def test_lookup_representative_latlng_no_riding(client, monkeypatch):
    """Lookup representative returns 404 if upstream returns no riding."""

    async def fake_get_by_point(self, lat, lng):
        return None

    monkeypatch.setattr(RidingRepository, "get_by_point", fake_get_by_point)

    response = await client.get("/v1/representatives/lookup?lat=45.4&lng=-75.7")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_lookup_representative_latlng_no_rep(
    client: AsyncClient,
    test_session,
    monkeypatch,
):
    """Lookup representative returns 404 if riding has no representative."""
    riding = Riding(name="Ottawa Centre", province="Ontario", fed_number=1)
    test_session.add(riding)
    await test_session.commit()

    async def fake_get_by_point(self, lat, lng):
        return riding

    monkeypatch.setattr(RidingRepository, "get_by_point", fake_get_by_point)

    response = await client.get("/v1/representatives/lookup?lat=45.4&lng=-75.7")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_lookup_representative_latlng_inactive_rep(
    client: AsyncClient,
    test_session,
    monkeypatch,
):
    """Lookup representative ignores inactive representative."""
    riding = Riding(name="Ottawa Centre", province="Ontario", fed_number=1)
    test_session.add(riding)
    await test_session.flush()

    rep = Representative(
        hoc_id=1002,
        name="Inactive Rep",
        riding_id=riding.id,
        is_active=False,
    )
    test_session.add(rep)
    await test_session.commit()

    async def fake_get_by_point(self, lat, lng):
        return riding

    monkeypatch.setattr(RidingRepository, "get_by_point", fake_get_by_point)

    response = await client.get("/v1/representatives/lookup?lat=45.4&lng=-75.7")
    assert response.status_code == 404
