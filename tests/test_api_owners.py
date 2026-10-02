"""POST /owners create-or-get."""

import uuid

from fastapi.testclient import TestClient


def test_upsert_owner_requires_api_key(client: TestClient) -> None:
    response = client.post("/owners", json={"name": "No Key Person"})
    assert response.status_code == 401


def test_upsert_owner_creates_then_gets(client: TestClient, auth_headers: dict[str, str]) -> None:
    # Unique per run — "Test Owner" already exists from visit fixtures
    name = f"Lesson Two Owner {uuid.uuid4().hex[:8]}"

    created = client.post("/owners", json={"name": name}, headers=auth_headers)
    assert created.status_code == 201
    owner_id = created.json()["owner_id"]
    assert created.json()["name"] == name

    again = client.post(
        "/owners",
        json={"name": name.upper()},
        headers=auth_headers,
    )
    assert again.status_code == 200
    assert again.json()["owner_id"] == owner_id


def test_upsert_owner_rejects_blank_name(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post(
        "/owners",
        json={"name": "   "},
        headers=auth_headers,
    )
    assert response.status_code == 422
