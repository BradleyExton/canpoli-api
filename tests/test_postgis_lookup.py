"""PostGIS lookup integration tests."""

import json

import pytest
from sqlalchemy import text

from canpoli.models import Representative, Riding
from canpoli.repositories import RepresentativeRepository, RidingRepository

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_get_by_point_inside_polygon(postgis_session):
    """Point-in-polygon lookup finds the riding."""
    riding = Riding(name="Polygon Riding", province="Ontario", fed_number=1)
    postgis_session.add(riding)
    await postgis_session.flush()

    polygon = {
        "type": "Polygon",
        "coordinates": [
            [
                [-75.0, 45.0],
                [-74.0, 45.0],
                [-74.0, 46.0],
                [-75.0, 46.0],
                [-75.0, 45.0],
            ]
        ],
    }
    await postgis_session.execute(
        text(
            """
            UPDATE ridings
            SET geom = ST_SetSRID(ST_Multi(ST_GeomFromGeoJSON(:geojson)), 4326)
            WHERE id = :id
            """
        ),
        {"geojson": json.dumps(polygon), "id": riding.id},
    )
    await postgis_session.commit()

    repo = RidingRepository(postgis_session)
    found = await repo.get_by_point(lat=45.5, lng=-74.5)
    assert found is not None
    assert found.id == riding.id


@pytest.mark.asyncio
async def test_get_by_point_boundary_excluded(postgis_session):
    """ST_Contains excludes boundary points."""
    riding = Riding(name="Boundary Riding", province="Ontario", fed_number=1)
    postgis_session.add(riding)
    await postgis_session.flush()

    polygon = {
        "type": "Polygon",
        "coordinates": [
            [
                [-75.0, 45.0],
                [-74.0, 45.0],
                [-74.0, 46.0],
                [-75.0, 46.0],
                [-75.0, 45.0],
            ]
        ],
    }
    await postgis_session.execute(
        text(
            """
            UPDATE ridings
            SET geom = ST_SetSRID(ST_Multi(ST_GeomFromGeoJSON(:geojson)), 4326)
            WHERE id = :id
            """
        ),
        {"geojson": json.dumps(polygon), "id": riding.id},
    )
    await postgis_session.commit()

    repo = RidingRepository(postgis_session)
    found = await repo.get_by_point(lat=45.0, lng=-75.0)
    assert found is None


@pytest.mark.asyncio
async def test_lookup_representative_postgis_flow(postgis_session):
    """Representative lookup works end-to-end with PostGIS geometry."""
    riding = Riding(name="Rep Riding", province="Ontario", fed_number=1)
    postgis_session.add(riding)
    await postgis_session.flush()

    rep = Representative(
        hoc_id=2001,
        name="PostGIS Rep",
        riding_id=riding.id,
        is_active=True,
    )
    postgis_session.add(rep)

    polygon = {
        "type": "Polygon",
        "coordinates": [
            [
                [-75.0, 45.0],
                [-74.0, 45.0],
                [-74.0, 46.0],
                [-75.0, 46.0],
                [-75.0, 45.0],
            ]
        ],
    }
    await postgis_session.execute(
        text(
            """
            UPDATE ridings
            SET geom = ST_SetSRID(ST_Multi(ST_GeomFromGeoJSON(:geojson)), 4326)
            WHERE id = :id
            """
        ),
        {"geojson": json.dumps(polygon), "id": riding.id},
    )
    await postgis_session.commit()

    riding_repo = RidingRepository(postgis_session)
    rep_repo = RepresentativeRepository(postgis_session)

    found_riding = await riding_repo.get_by_point(lat=45.5, lng=-74.5)
    assert found_riding is not None
    found_rep = await rep_repo.get_by_riding_id(found_riding.id)
    assert found_rep is not None
    assert found_rep.hoc_id == 2001
