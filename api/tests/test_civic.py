from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from api.civic_context.main import app
from api.civic_context.routers.civic.models import Representative, Representatives


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_representatives():
    return Representatives(
        federal=Representative(
            name="John Doe",
            party="Liberal Party",
            riding="Ottawa Centre",
            email="john.doe@parl.gc.ca",
        ),
        provincial=Representative(
            name="Jane Smith",
            party="Ontario Liberal Party",
            riding="Ottawa Centre",
            email="jane.smith@ola.org",
        ),
        municipal=Representative(
            name="Bob Wilson",
            party=None,
            riding="Ward 14",
            email="bob.wilson@ottawa.ca",
        ),
    )


class TestCivicEndpoint:
    """Tests for the /civic/ endpoint."""

    def test_civic_endpoint_success(self, client, mock_representatives):
        """Test successful civic context retrieval."""
        with (
            patch(
                "api.civic_context.routers.civic.router.get_cached_response",
                return_value=None,
            ),
            patch(
                "api.civic_context.routers.civic.router.get_representatives",
                new_callable=AsyncMock,
            ) as mock_get_reps,
            patch("api.civic_context.routers.civic.router.set_cached_response"),
        ):
            mock_get_reps.return_value = mock_representatives

            response = client.get("/civic/?lat=45.4215&lng=-75.6972")

            assert response.status_code == 200
            data = response.json()
            assert "representatives" in data
            assert "location" in data
            assert data["location"]["lat"] == 45.4215
            assert data["location"]["lng"] == -75.6972
            assert data["representatives"]["federal"]["name"] == "John Doe"

    def test_civic_endpoint_cache_hit(self, client):
        """Test that cached response is returned when available."""
        # Cached data with flattened structure
        cached_data = {
            "representatives": {
                "federal": {
                    "name": "Cached Rep",
                    "party": "Test Party",
                    "riding": "Test Riding",
                    "email": None,
                    "hoc_person_id": None,
                    "honorific": None,
                    "province": None,
                    "photo_url": None,
                    "profile_url": None,
                    "ministerial_role": None,
                    "parliamentary_secretary_role": None,
                    "committees": [],
                    "parliamentary_associations": [],
                    "openparliament_url": None,
                    "bills_sponsored": [],
                    "recent_votes": [],
                },
                "provincial": None,
                "municipal": None,
            },
            "location": {"lat": 45.4215, "lng": -75.6972},
        }

        with patch(
            "api.civic_context.routers.civic.router.get_cached_response",
            return_value=cached_data,
        ):
            response = client.get("/civic/?lat=45.4215&lng=-75.6972")

            assert response.status_code == 200
            assert response.json()["representatives"]["federal"]["name"] == "Cached Rep"

    def test_civic_endpoint_invalid_lat(self, client):
        """Test validation error for invalid latitude."""
        response = client.get("/civic/?lat=100&lng=-75.6972")

        assert response.status_code == 422  # Validation error

    def test_civic_endpoint_invalid_lng(self, client):
        """Test validation error for invalid longitude."""
        response = client.get("/civic/?lat=45.4215&lng=-200")

        assert response.status_code == 422  # Validation error

    def test_civic_endpoint_missing_params(self, client):
        """Test that missing parameters return validation error."""
        response = client.get("/civic/")

        assert response.status_code == 422
