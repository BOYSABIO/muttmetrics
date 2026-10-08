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


def test_get_owner_profile_requires_api_key(client: TestClient) -> None:
    response = client.get("/owners/1")
    assert response.status_code == 401


def test_get_owner_profile_404(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/owners/999999", headers=auth_headers)
    assert response.status_code == 404


def test_get_owner_profile_includes_dogs(client: TestClient, auth_headers: dict[str, str]) -> None:
    name = f"Profile Owner {uuid.uuid4().hex[:8]}"
    created = client.post(
        "/owners",
        json={"name": name, "phone": "+49 170 1111111"},
        headers=auth_headers,
    )
    assert created.status_code == 201
    owner_id = created.json()["owner_id"]

    dog_a = client.post(
        "/dogs",
        json={"owner_id": owner_id, "name": f"Alpha {uuid.uuid4().hex[:6]}"},
        headers=auth_headers,
    )
    dog_b = client.post(
        "/dogs",
        json={"owner_id": owner_id, "name": f"Beta {uuid.uuid4().hex[:6]}"},
        headers=auth_headers,
    )
    assert dog_a.status_code == 201
    assert dog_b.status_code == 201

    profile = client.get(f"/owners/{owner_id}", headers=auth_headers)
    assert profile.status_code == 200
    body = profile.json()
    assert body["owner_id"] == owner_id
    assert body["name"] == name
    assert body["phone"] == "+49 170 1111111"
    assert "notes" in body
    assert "locale" in body
    assert "visit_count" in body  # derived present (null ok)
    dog_ids = {d["dog_id"] for d in body["dogs"]}
    assert dog_a.json()["dog_id"] in dog_ids
    assert dog_b.json()["dog_id"] in dog_ids


def test_patch_owner_requires_api_key(client: TestClient) -> None:
    response = client.patch("/owners/1", json={"notes": "x"})
    assert response.status_code == 401


def test_patch_owner_404(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.patch(
        "/owners/999999",
        json={"notes": "ghost"},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_patch_owner_updates_phone_leaves_name(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    name = f"Patch Owner {uuid.uuid4().hex[:8]}"
    created = client.post(
        "/owners",
        json={"name": name, "phone": "+49 170 1111111"},
        headers=auth_headers,
    )
    assert created.status_code == 201
    owner_id = created.json()["owner_id"]

    patched = client.patch(
        f"/owners/{owner_id}",
        json={"phone": "+49 170 2222222", "notes": "prefers mornings"},
        headers=auth_headers,
    )
    assert patched.status_code == 200
    body = patched.json()
    assert body["name"] == name
    assert body["phone"] == "+49 170 2222222"
    assert body["notes"] == "prefers mornings"


def test_patch_owner_rejects_derived_field(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    name = f"Derived Block {uuid.uuid4().hex[:8]}"
    created = client.post(
        "/owners",
        json={"name": name},
        headers=auth_headers,
    )
    assert created.status_code == 201
    owner_id = created.json()["owner_id"]

    patched = client.patch(
        f"/owners/{owner_id}",
        json={"visit_count": 99},
        headers=auth_headers,
    )
    assert patched.status_code == 422
