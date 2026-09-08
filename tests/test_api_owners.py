"""POST /owners create-or-get."""

import uuid

import pytest
from fastapi.testclient import TestClient

from muttmetrics.api.app import create_app


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://muttmetrics:muttmetrics@localhost:5432/muttmetrics",
    )
    monkeypatch.setenv("API_KEY", "test-api-key")
    return TestClient(create_app())


def test_upsert_owner_requires_api_key(client: TestClient) -> None:
    response = client.post("/owners", json={"name": "No Key Person"})
    assert response.status_code == 401


def test_upsert_owner_creates_then_gets(client: TestClient) -> None:
    headers = {"X-API-Key": "test-api-key"}
    # Unique per run — "Test Owner" already exists from visit fixtures
    name = f"Lesson Two Owner {uuid.uuid4().hex[:8]}"

    created = client.post("/owners", json={"name": name}, headers=headers)
    assert created.status_code == 201
    owner_id = created.json()["owner_id"]
    assert created.json()["name"] == name

    again = client.post(
        "/owners",
        json={"name": name.upper()},
        headers=headers,
    )
    assert again.status_code == 200
    assert again.json()["owner_id"] == owner_id


def test_upsert_owner_rejects_blank_name(client: TestClient) -> None:
    response = client.post(
        "/owners",
        json={"name": "   "},
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 422
