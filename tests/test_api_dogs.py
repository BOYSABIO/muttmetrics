"""POST /dogs create-or-get. and GET /dogs directory search."""

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


def test_list_dogs_requires_api_key(client: TestClient) -> None:
    response = client.get("/dogs")
    assert response.status_code == 401


def test_list_dogs_browse_includes_owner_name(client: TestClient, owner_id: int) -> None:
    headers = {"X-API-Key": "test-api-key"}
    dog_name = f"BrowseDog {uuid.uuid4().hex[:8]}"

    created = client.post(
        "/dogs",
        json={"owner_id": owner_id, "name": dog_name},
        headers=headers,
    )
    assert created.status_code == 201
    dog_id = created.json()["dog_id"]

    listed = client.get("/dogs", headers=headers)
    assert listed.status_code == 200
    rows = listed.json()
    assert isinstance(rows, list)

    match = next(row for row in rows if row["dog_id"] == dog_id)
    assert match["name"] == dog_name
    assert match["owner_id"] == owner_id
    assert isinstance(match["owner_name"], str)
    assert match["owner_name"]  # not empty
    assert "last_visit_date" in match


def test_list_dogs_q_filters_by_name_substring(client: TestClient, owner_id: int) -> None:
    headers = {"X-API-Key": "test-api-key"}
    token = uuid.uuid4().hex[:8]
    dog_name = f"Bella{token}"

    created = client.post(
        "/dogs",
        json={"owner_id": owner_id, "name": dog_name},
        headers=headers,
    )

    assert created.status_code == 201
    dog_id = created.json()["dog_id"]

    hit = client.get(f"/dogs?q={token}", headers=headers)
    assert hit.status_code == 200
    ids = [row["dog_id"] for row in hit.json()]
    assert dog_id in ids

    miss = client.get("/dogs?q=zzznomatch999", headers=headers)
    assert miss.status_code == 200
    assert miss.json() == []
