"""Health endpoint smoke tests"""

from fastapi.testclient import TestClient

from muttmetrics import __version__
from muttmetrics.api.app import create_app


def test_health_returns_ok_and_version() -> None:
    """Process up + version for deploy checks (#197)."""
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == __version__
    assert "alembic_head" in body  # may be null if DB unreachable


def test_openapi_docs_available() -> None:
    """Test that the OpenAPI docs are available"""
    client = TestClient(create_app())
    response = client.get("/docs")
    assert response.status_code == 200
