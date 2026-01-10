import pytest
from fastapi.testclient import TestClient

from api.civic_context.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def sample_representative_response():
    """Sample response from Represent API."""
    return {
        "objects": [
            {
                "name": "John Doe",
                "party_name": "Liberal Party",
                "district_name": "Ottawa Centre",
                "elected_office": "MP",
                "email": "john.doe@parl.gc.ca",
            },
            {
                "name": "Jane Smith",
                "party_name": "Ontario Liberal Party",
                "district_name": "Ottawa Centre",
                "elected_office": "MPP",
                "email": "jane.smith@ola.org",
            },
            {
                "name": "Bob Wilson",
                "party_name": None,
                "district_name": "Ward 14",
                "elected_office": "Councillor",
                "email": "bob.wilson@ottawa.ca",
            },
        ]
    }
