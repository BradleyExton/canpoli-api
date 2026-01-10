from fastapi.testclient import TestClient

from api.civic_context.main import app


def test_health_check():
    """Test that health endpoint returns ok status."""
    client = TestClient(app)
    response = client.get("/health/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_check_no_trailing_slash():
    """Test health endpoint without trailing slash redirects."""
    client = TestClient(app)
    response = client.get("/health", follow_redirects=False)

    # FastAPI redirects to trailing slash version
    assert response.status_code in (200, 307)
