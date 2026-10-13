"""Health endpoint smoke tests (no Postgres required)"""

from fastapi.testclient import TestClient

from muttmetrics.api.app import create_app


def test_health_returns_ok() -> None:
    """Test that the health endpoint returns OK"""
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_openapi_docs_available() -> None:
    """Test that the OpenAPI docs are available"""
    client = TestClient(create_app())
    response = client.get("/docs")
    assert response.status_code == 200
