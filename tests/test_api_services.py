"""GET /services - catalog for the capture SPA picker."""

import pytest
from fastapi.testclient import TestClient

from muttmetrics.api.app import create_app

AUTH = {"x-api-key": "test-api-key"}


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+psycopg://muttmetrics:muttmetrics@127.0.0.1:5432/muttmetrics"
    )
    monkeypatch.setenv("API_KEY", "test-api-key")
    return TestClient(create_app())


def test_list_services_requires_api_key(client: TestClient) -> None:
    response = client.get("/services")
    assert response.status_code == 401


def test_list_services_returns_catalog(client: TestClient) -> None:
    response = client.get("/services", headers=AUTH)
    assert response.status_code == 200
    rows = response.json()
    assert isinstance(rows, list)
    assert len(rows) >= 1

    first = rows[0]
    assert "service_id" in first
    assert "slug" in first
    assert "name_en" in first

    slugs = {row["slug"] for row in rows}
    assert "full_groom" in slugs
