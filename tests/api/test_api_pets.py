"""POST /pets create-or-get. and GET /pets directory search."""

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
        "/pets",
        json={"owner_id": owner_id, "name": "NoKey"},
    )
    assert response.status_code == 401


def test_upsert_dog_creates_then_gets(
    client: TestClient, owner_id: int, auth_headers: dict[str, str]
) -> None:
    dog_name = f"Bella {uuid.uuid4().hex[:8]}"

    created = client.post(
        "/pets",
        json={"owner_id": owner_id, "name": dog_name},
        headers=auth_headers,
    )
    assert created.status_code == 201
    pet_id = created.json()["pet_id"]
    assert created.json()["owner_id"] == owner_id
    assert created.json()["species"] == "dog"

    again = client.post(
        "/pets",
        json={"owner_id": owner_id, "name": dog_name.upper()},
        headers=auth_headers,
    )
    assert again.status_code == 200
    assert again.json()["pet_id"] == pet_id


def test_upsert_dog_unknown_owner_404(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post(
        "/pets",
        json={"owner_id": 999999, "name": "Ghost"},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_upsert_dog_blank_name_422(
    client: TestClient, owner_id: int, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        "/pets",
        json={"owner_id": owner_id, "name": "   "},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_list_dogs_requires_api_key(client: TestClient) -> None:
    response = client.get("/pets")
    assert response.status_code == 401


def test_list_dogs_browse_includes_owner_name(
    client: TestClient, owner_id: int, auth_headers: dict[str, str]
) -> None:
    dog_name = f"BrowseDog {uuid.uuid4().hex[:8]}"

    created = client.post(
        "/pets",
        json={"owner_id": owner_id, "name": dog_name},
        headers=auth_headers,
    )
    assert created.status_code == 201
    pet_id = created.json()["pet_id"]

    listed = client.get("/pets", headers=auth_headers)
    assert listed.status_code == 200
    rows = listed.json()
    assert isinstance(rows, list)

    match = next(row for row in rows if row["pet_id"] == pet_id)
    assert match["name"] == dog_name
    assert match["owner_id"] == owner_id
    assert isinstance(match["owner_name"], str)
    assert match["owner_name"]  # not empty
    assert match["last_visit_date"] is None  # new dog, no visits


def test_list_dogs_q_filters_by_name_substring(
    client: TestClient, owner_id: int, auth_headers: dict[str, str]
) -> None:
    token = uuid.uuid4().hex[:8]
    dog_name = f"Bella{token}"

    created = client.post(
        "/pets",
        json={"owner_id": owner_id, "name": dog_name},
        headers=auth_headers,
    )

    assert created.status_code == 201
    pet_id = created.json()["pet_id"]

    hit = client.get(f"/pets?q={token}", headers=auth_headers)
    assert hit.status_code == 200
    ids = [row["pet_id"] for row in hit.json()]
    assert pet_id in ids

    miss = client.get("/pets?q=zzznomatch999", headers=auth_headers)
    assert miss.status_code == 200
    assert miss.json() == []


def test_get_dog_profile_requires_api_key(client: TestClient) -> None:
    response = client.get("/pets/1")
    assert response.status_code == 401


def test_get_dog_profile_404(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/pets/999999", headers=auth_headers)
    assert response.status_code == 404


def test_get_dog_profile_includes_owner_and_visits(
    client: TestClient, owner_id: int, auth_headers: dict[str, str]
) -> None:
    dog_name = f"ProfileDog {uuid.uuid4().hex[:8]}"
    created = client.post(
        "/pets",
        json={"owner_id": owner_id, "name": dog_name},
        headers=auth_headers,
    )
    assert created.status_code == 201
    pet_id = created.json()["pet_id"]

    visit = client.post(
        "/visits",
        json={
            "pet_id": pet_id,
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

    profile = client.get(f"/pets/{pet_id}", headers=auth_headers)
    assert profile.status_code == 200
    body = profile.json()
    assert body["pet_id"] == pet_id
    assert body["name"] == dog_name
    assert body["owner"]["owner_id"] == owner_id
    assert body["owner"]["name"]
    assert body["coat_type"] is None
    assert body["handling_score"] is None
    assert body["size_band"] is None  # no weight yet (#171)
    assert body["avatar_photo_id"] is None  # no profile/intake photo yet
    assert body["visit_count"] == 1
    assert body["last_visit_date"] == "2026-10-01"
    assert isinstance(body["recent_visits"], list)
    assert body["recent_visits"][0]["visit_id"] == visit_id
    assert body["recent_visits"][0]["actual_minutes"] == 90
    assert body["recent_visits"][0]["condition_score"] == 3

    empty = client.get(f"/pets/{pet_id}?recent_limit=0", headers=auth_headers)
    assert empty.status_code == 200
    assert empty.json()["recent_visits"] == []


def test_get_dog_duration_range_still_works(
    client: TestClient, owner_id: int, auth_headers: dict[str, str]
) -> None:
    """Static path /duration-range must not be stolen by /pets/{id}."""
    created = client.post(
        "/pets",
        json={"owner_id": owner_id, "name": f"RangeDog {uuid.uuid4().hex[:8]}"},
        headers=auth_headers,
    )
    assert created.status_code == 201
    pet_id = created.json()["pet_id"]
    response = client.get(f"/pets/{pet_id}/duration-range", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["pet_id"] == pet_id


def test_patch_dog_requires_api_key(client: TestClient) -> None:
    response = client.patch("/pets/1", json={"coat_type": "curly"})
    assert response.status_code == 401


def test_patch_dog_404(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.patch(
        "/pets/999999",
        json={"coat_type": "curly"},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_patch_dog_updates_coat_and_handling(
    client: TestClient, owner_id: int, auth_headers: dict[str, str]
) -> None:
    dog_name = f"PatchDog {uuid.uuid4().hex[:8]}"
    created = client.post(
        "/pets",
        json={"owner_id": owner_id, "name": dog_name},
        headers=auth_headers,
    )
    assert created.status_code == 201
    pet_id = created.json()["pet_id"]

    patched = client.patch(
        f"/pets/{pet_id}",
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
    assert body["owner"]["owner_id"] == owner_id  # still a full profile


def test_patch_dog_rejects_derived_field(
    client: TestClient, owner_id: int, auth_headers: dict[str, str]
) -> None:
    created = client.post(
        "/pets",
        json={"owner_id": owner_id, "name": f"DerivedDog {uuid.uuid4().hex[:8]}"},
        headers=auth_headers,
    )
    assert created.status_code == 201
    pet_id = created.json()["pet_id"]

    response = client.patch(
        f"/pets/{pet_id}",
        json={"visit_count": 9},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_patch_weight_sets_size_band(
    client: TestClient, owner_id: int, auth_headers: dict[str, str]
) -> None:
    created = client.post(
        "/pets",
        json={"owner_id": owner_id, "name": f"Sizedog {uuid.uuid4().hex[:8]}"},
        headers=auth_headers,
    )
    assert created.status_code == 201
    pet_id = created.json()["pet_id"]

    patched = client.patch(
        f"/pets/{pet_id}",
        json={"weight_kg": 8},
        headers=auth_headers,
    )
    assert patched.status_code == 200
    assert patched.json()["size_band"] == "s"
    assert patched.json()["size_source"] == "weight"

    # A weighed dog's size comes from the weight; a size sent by hand is ignored.
    ignored = client.patch(
        f"/pets/{pet_id}",
        json={"size_band": "xl"},
        headers=auth_headers,
    )
    assert ignored.status_code == 200
    assert ignored.json()["size_band"] == "s"


@pytest.mark.parametrize("weight", [-3, 0, 7500])
def test_patch_dog_rejects_impossible_weight(
    client: TestClient, owner_id: int, auth_headers: dict[str, str], weight: float
) -> None:
    """#177: negative, zero, and grams-typed-as-kg are all refused."""
    created = client.post(
        "/pets",
        json={"owner_id": owner_id, "name": f"Weight {uuid.uuid4().hex[:8]}"},
        headers=auth_headers,
    )
    pet_id = created.json()["pet_id"]

    response = client.patch(f"/pets/{pet_id}", json={"weight_kg": weight}, headers=auth_headers)
    assert response.status_code == 422


# --- #180: cancelled / no-show never count as a visit --------------------------


def test_cancelled_and_no_show_do_not_count_as_visits(
    client: TestClient, owner_id: int, auth_headers: dict[str, str]
) -> None:
    """last_visit_date, visit_count (dog, owner, list) and days_since_last all
    use the same rule: completed (or legacy NULL) only."""
    created = client.post(
        "/pets",
        json={"owner_id": owner_id, "name": f"Status {uuid.uuid4().hex[:8]}"},
        headers=auth_headers,
    )
    pet_id = created.json()["pet_id"]

    def visit(day: str, status: str) -> dict:
        response = client.post(
            "/visits",
            json={
                "pet_id": pet_id,
                "owner_id": owner_id,
                "visit_date": day,
                "actual_minutes": 60,
                "status": status,
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        return response.json()

    visit("2026-09-01", "completed")
    visit("2026-09-20", "cancelled")
    visit("2026-09-25", "no_show")

    dog = client.get(f"/pets/{pet_id}", headers=auth_headers).json()
    assert dog["last_visit_date"] == "2026-09-01"
    assert dog["visit_count"] == 1

    owner = client.get(f"/owners/{owner_id}", headers=auth_headers).json()
    assert owner["visit_count"] == 1

    listed = client.get("/pets", headers=auth_headers).json()
    assert next(r for r in listed if r["pet_id"] == pet_id)["last_visit_date"] == "2026-09-01"

    # Counted from the last *completed* visit, not the cancelled one on 09-20.
    assert visit("2026-10-01", "completed")["days_since_last"] == 30


def test_list_dogs_q_treats_wildcards_literally(
    client: TestClient, owner_id: int, auth_headers: dict[str, str]
) -> None:
    """#180: "%" and "_" in a search are characters, not LIKE wildcards."""
    tag = uuid.uuid4().hex[:6]
    for name in (f"Rex_{tag}", f"RexA{tag}", f"100% {tag}"):
        client.post("/pets", json={"owner_id": owner_id, "name": name}, headers=auth_headers)

    underscore = client.get("/pets", params={"q": f"Rex_{tag}"}, headers=auth_headers).json()
    assert [d["name"] for d in underscore] == [f"Rex_{tag}"]  # not RexA…

    percent = client.get("/pets", params={"q": f"100% {tag}"}, headers=auth_headers).json()
    assert [d["name"] for d in percent] == [f"100% {tag}"]
    assert client.get("/pets", params={"q": f"%{tag}"}, headers=auth_headers).json() == []


def test_create_cat_and_same_name_dog_are_distinct(
    client: TestClient, owner_id: int, auth_headers: dict[str, str]
) -> None:
    name = f"Bella {uuid.uuid4().hex[:8]}"
    dog = client.post(
        "/pets",
        json={"owner_id": owner_id, "name": name, "species": "dog"},
        headers=auth_headers,
    )
    cat = client.post(
        "/pets",
        json={"owner_id": owner_id, "name": name, "species": "cat"},
        headers=auth_headers,
    )
    assert dog.status_code == 201
    assert cat.status_code == 201
    assert dog.json()["pet_id"] != cat.json()["pet_id"]
    assert cat.json()["species"] == "cat"


def test_breed_must_match_species(
    client: TestClient, owner_id: int, auth_headers: dict[str, str]
) -> None:
    breeds = client.get("/breeds", params={"species": "cat"}, headers=auth_headers)
    assert breeds.status_code == 200
    cat_breed_id = breeds.json()[0]["breed_id"]

    mismatch = client.post(
        "/pets",
        json={
            "owner_id": owner_id,
            "name": f"WrongBreed {uuid.uuid4().hex[:8]}",
            "species": "dog",
            "breed_id": cat_breed_id,
        },
        headers=auth_headers,
    )
    assert mismatch.status_code == 422

    created = client.post(
        "/pets",
        json={
            "owner_id": owner_id,
            "name": f"OkCat {uuid.uuid4().hex[:8]}",
            "species": "cat",
            "breed_id": cat_breed_id,
        },
        headers=auth_headers,
    )
    assert created.status_code == 201
    assert created.json()["breed_id"] == cat_breed_id
