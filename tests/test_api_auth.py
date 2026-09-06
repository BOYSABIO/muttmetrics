"""API key auth tests (no Postgres required)."""

import pytest
from fastapi.testclient import TestClient

from muttmetrics.api.app import create_app


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """App client with a known API_KEY (and dummy DATABASE_URL for Settings)."""
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://muttmetrics:muttmetrics@localhost:5432/muttmetrics",
    )
    monkeypatch.setenv("API_KEY", "test-api-key")
    return TestClient(create_app())


def test_ping_missing_key_returns_401(client: TestClient) -> None:
    """Verify 401 for missing or incorrect X-API-Key header."""
    response = client.get("/ping")
    assert response.status_code == 401


def test_ping_wrong_key_returns_401(client: TestClient) -> None:
    """Verify 401 for incorrect X-API-Key header."""
    response = client.get("/ping", headers={"X-API-Key": "wrong-key"})
    assert response.status_code == 401


def test_ping_valid_key_returns_ok(client: TestClient) -> None:
    """Verify 200 for valid X-API-Key header."""
    response = client.get("/ping", headers={"X-API-Key": "test-api-key"})
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_health_still_public(client: TestClient) -> None:
    """Verify health endpoint is still public (no auth required)."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
