"""POST /dogs create-or-get. and GET /dogs directory search."""

import uuid

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def owner_id(client: TestClient, auth_headers: dict[str, str]) -> int:
    name = f"Dog Lesson Owner {uuid.uuid4().hex[:8]}"
    response = client.post(
        "/owners",
        json={"name": name},
        headers=auth_headers,
    )
    assert response.status_code == 201
    return response.json()["owner_id"]


def test_upsert_dog_requires_api_key(client: TestClient, owner_id: int) -> None:
    response = client.post(
        "/dogs",
        json={"owner_id": owner_id, "name": "NoKey"},
    )
    assert response.status_code == 401


def test_upsert_dog_creates_then_gets(
    client: TestClient, owner_id: int, auth_headers: dict[str, str]
) -> None:
    dog_name = f"Bella {uuid.uuid4().hex[:8]}"

    created = client.post(
        "/dogs",
        json={"owner_id": owner_id, "name": dog_name},
        headers=auth_headers,
    )
    assert created.status_code == 201
    dog_id = created.json()["dog_id"]
    assert created.json()["owner_id"] == owner_id

    again = client.post(
        "/dogs",
        json={"owner_id": owner_id, "name": dog_name.upper()},
        headers=auth_headers,
    )
    assert again.status_code == 200
    assert again.json()["dog_id"] == dog_id


def test_upsert_dog_unknown_owner_404(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post(
        "/dogs",
        json={"owner_id": 999999, "name": "Ghost"},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_upsert_dog_blank_name_422(
    client: TestClient, owner_id: int, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        "/dogs",
        json={"owner_id": owner_id, "name": "   "},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_list_dogs_requires_api_key(client: TestClient) -> None:
    response = client.get("/dogs")
    assert response.status_code == 401


def test_list_dogs_browse_includes_owner_name(
    client: TestClient, owner_id: int, auth_headers: dict[str, str]
) -> None:
    dog_name = f"BrowseDog {uuid.uuid4().hex[:8]}"

    created = client.post(
        "/dogs",
        json={"owner_id": owner_id, "name": dog_name},
        headers=auth_headers,
    )
    assert created.status_code == 201
    dog_id = created.json()["dog_id"]

    listed = client.get("/dogs", headers=auth_headers)
    assert listed.status_code == 200
    rows = listed.json()
    assert isinstance(rows, list)

    match = next(row for row in rows if row["dog_id"] == dog_id)
    assert match["name"] == dog_name
    assert match["owner_id"] == owner_id
    assert isinstance(match["owner_name"], str)
    assert match["owner_name"]  # not empty
    assert "last_visit_date" in match


def test_list_dogs_q_filters_by_name_substring(
    client: TestClient, owner_id: int, auth_headers: dict[str, str]
) -> None:
    token = uuid.uuid4().hex[:8]
    dog_name = f"Bella{token}"

    created = client.post(
        "/dogs",
        json={"owner_id": owner_id, "name": dog_name},
        headers=auth_headers,
    )

    assert created.status_code == 201
    dog_id = created.json()["dog_id"]

    hit = client.get(f"/dogs?q={token}", headers=auth_headers)
    assert hit.status_code == 200
    ids = [row["dog_id"] for row in hit.json()]
    assert dog_id in ids

    miss = client.get("/dogs?q=zzznomatch999", headers=auth_headers)
    assert miss.status_code == 200
    assert miss.json() == []


def test_get_dog_profile_requires_api_key(client: TestClient) -> None:
    response = client.get("/dogs/1")
    assert response.status_code == 401


def test_get_dog_profile_404(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/dogs/999999", headers=auth_headers)
    assert response.status_code == 404


def test_get_dog_profile_includes_owner_and_visits(
    client: TestClient, owner_id: int, auth_headers: dict[str, str]
) -> None:
    dog_name = f"ProfileDog {uuid.uuid4().hex[:8]}"
    created = client.post(
        "/dogs",
        json={"owner_id": owner_id, "name": dog_name},
        headers=auth_headers,
    )
    assert created.status_code == 201
    dog_id = created.json()["dog_id"]

    visit = client.post(
        "/visits",
        json={
            "dog_id": dog_id,
            "owner_id": owner_id,
            "visit_date": "2026-10-01",
            "actual_minutes": 90,
            "condition_score": 3,
            "status": "completed",
        },
        headers=auth_headers,
    )
    assert visit.status_code == 201
    visit_id = visit.json()["visit_id"]

    profile = client.get(f"/dogs/{dog_id}", headers=auth_headers)
    assert profile.status_code == 200
    body = profile.json()
    assert body["dog_id"] == dog_id
    assert body["name"] == dog_name
    assert body["owner"]["owner_id"] == owner_id
    assert body["owner"]["name"]
    assert "coat_type" in body
    assert "handling_score" in body
    assert "size_band" in body  # derived present (null ok)
    assert "avatar_photo_id" in body  # null until a profile/intake photo exists
    assert isinstance(body["recent_visits"], list)
    assert body["recent_visits"][0]["visit_id"] == visit_id
    assert body["recent_visits"][0]["actual_minutes"] == 90
    assert body["recent_visits"][0]["condition_score"] == 3

    empty = client.get(f"/dogs/{dog_id}?recent_limit=0", headers=auth_headers)
    assert empty.status_code == 200
    assert empty.json()["recent_visits"] == []


def test_get_dog_duration_range_still_works(
    client: TestClient, owner_id: int, auth_headers: dict[str, str]
) -> None:
    """Static path /duration-range must not be stolen by /dogs/{id}."""
    created = client.post(
        "/dogs",
        json={"owner_id": owner_id, "name": f"RangeDog {uuid.uuid4().hex[:8]}"},
        headers=auth_headers,
    )
    assert created.status_code == 201
    dog_id = created.json()["dog_id"]
    response = client.get(f"/dogs/{dog_id}/duration-range", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["dog_id"] == dog_id


def test_patch_dog_requires_api_key(client: TestClient) -> None:
    response = client.patch("/dogs/1", json={"coat_type": "curly"})
    assert response.status_code == 401


def test_patch_dog_404(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.patch(
        "/dogs/999999",
        json={"coat_type": "curly"},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_patch_dog_updates_coat_and_handling(
    client: TestClient, owner_id: int, auth_headers: dict[str, str]
) -> None:
    dog_name = f"PatchDog {uuid.uuid4().hex[:8]}"
    created = client.post(
        "/dogs",
        json={"owner_id": owner_id, "name": dog_name},
        headers=auth_headers,
    )
    assert created.status_code == 201
    dog_id = created.json()["dog_id"]

    patched = client.patch(
        f"/dogs/{dog_id}",
        json={
            "coat_type": "curly",
            "handling_score": 4,
            "temperament_notes": "nervous around dryers",
        },
        headers=auth_headers,
    )
    assert patched.status_code == 200
    body = patched.json()
    assert body["name"] == dog_name  # omitted → unchanged
    assert body["coat_type"] == "curly"
    assert body["handling_score"] == 4
    assert body["temperament_notes"] == "nervous around dryers"
    assert "owner" in body  # still a full profile


def test_patch_dog_rejects_derived_field(
    client: TestClient, owner_id: int, auth_headers: dict[str, str]
) -> None:
    created = client.post(
        "/dogs",
        json={"owner_id": owner_id, "name": f"DerivedDog {uuid.uuid4().hex[:8]}"},
        headers=auth_headers,
    )
    assert created.status_code == 201
    dog_id = created.json()["dog_id"]

    response = client.patch(
        f"/dogs/{dog_id}",
        json={"size_band": "xl"},
        headers=auth_headers,
    )
    assert response.status_code == 422
