"""POST /dogs create-or-get."""

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


@pytest.fixture
def owner_id(client: TestClient) -> int:
    name = f"Dog Lesson Owner {uuid.uuid4().hex[:8]}"
    response = client.post(
        "/owners",
        json={"name": name},
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 201
    return response.json()["owner_id"]


def test_upsert_dog_requires_api_key(client: TestClient, owner_id: int) -> None:
    response = client.post(
        "/dogs",
        json={"owner_id": owner_id, "name": "NoKey"},
    )
    assert response.status_code == 401


def test_upsert_dog_creates_then_gets(client: TestClient, owner_id: int) -> None:
    headers = {"X-API-Key": "test-api-key"}
    dog_name = f"Bella {uuid.uuid4().hex[:8]}"

    created = client.post(
        "/dogs",
        json={"owner_id": owner_id, "name": dog_name},
        headers=headers,
    )
    assert created.status_code == 201
    dog_id = created.json()["dog_id"]
    assert created.json()["owner_id"] == owner_id

    again = client.post(
        "/dogs",
        json={"owner_id": owner_id, "name": dog_name.upper()},
        headers=headers,
    )
    assert again.status_code == 200
    assert again.json()["dog_id"] == dog_id


def test_upsert_dog_unknown_owner_404(client: TestClient) -> None:
    response = client.post(
        "/dogs",
        json={"owner_id": 999999, "name": "Ghost"},
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 404


def test_upsert_dog_blank_name_422(client: TestClient, owner_id: int) -> None:
    response = client.post(
        "/dogs",
        json={"owner_id": owner_id, "name": "   "},
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 422
