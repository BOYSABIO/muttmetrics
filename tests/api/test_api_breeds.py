"""GET /breeds — catalog for Directory pickers."""

from fastapi.testclient import TestClient

from muttmetrics.seed.data import SEED_BREEDS


def test_list_breeds_requires_api_key(client: TestClient) -> None:
    response = client.get("/breeds")
    assert response.status_code == 401


def test_list_breeds_returns_catalog(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/breeds", headers=auth_headers)
    assert response.status_code == 200
    rows = response.json()
    assert {row["name_en"] for row in rows} >= {b["name_en"] for b in SEED_BREEDS}
    assert all(isinstance(row["breed_id"], int) for row in rows)
    assert {row["species"] for row in rows} <= {"dog", "cat"}


def test_list_breeds_filters_by_species(client: TestClient, auth_headers: dict[str, str]) -> None:
    cats = client.get("/breeds", params={"species": "cat"}, headers=auth_headers)
    assert cats.status_code == 200
    assert cats.json()
    assert all(row["species"] == "cat" for row in cats.json())

    dogs = client.get("/breeds", params={"species": "dog"}, headers=auth_headers)
    assert dogs.status_code == 200
    assert dogs.json()
    assert all(row["species"] == "dog" for row in dogs.json())

    bad = client.get("/breeds", params={"species": "lemur"}, headers=auth_headers)
    assert bad.status_code == 422


# --- POST /breeds: adding a breed in the salon ---------------------------------


def test_create_breed_is_salon_and_listed(client: TestClient, auth_headers) -> None:
    created = client.post(
        "/breeds", json={"species": "dog", "name_en": "syn  salon   hound"}, headers=auth_headers
    )
    assert created.status_code == 201
    body = created.json()
    assert body["name_en"] == "Syn Salon Hound"  # spaces collapsed, all-lower capitalised
    assert body["source"] == "salon"
    listed = client.get("/breeds", params={"species": "dog"}, headers=auth_headers).json()
    assert any(row["breed_id"] == body["breed_id"] for row in listed)


def test_create_breed_keeps_typed_capitals(client: TestClient, auth_headers) -> None:
    created = client.post(
        "/breeds", json={"species": "dog", "name_en": "Syn Coton de Test"}, headers=auth_headers
    )
    assert created.json()["name_en"] == "Syn Coton de Test"


def test_create_breed_refuses_a_twin_any_case(client: TestClient, auth_headers) -> None:
    first = client.post(
        "/breeds", json={"species": "dog", "name_en": "Syn Twin Terrier"}, headers=auth_headers
    )
    again = client.post(
        "/breeds", json={"species": "dog", "name_en": "SYN TWIN TERRIER"}, headers=auth_headers
    )
    assert again.status_code == 409
    assert again.json()["detail"]["breed"]["breed_id"] == first.json()["breed_id"]

    # Same name for the other species is a different breed.
    cat = client.post(
        "/breeds", json={"species": "cat", "name_en": "Syn Twin Terrier"}, headers=auth_headers
    )
    assert cat.status_code == 201


def test_create_breed_matches_the_german_name(client: TestClient, auth_headers) -> None:
    """Typing the German name of a catalog breed finds it instead of adding a twin."""
    response = client.post(
        "/breeds", json={"species": "dog", "name_en": "deutscher schäferhund"}, headers=auth_headers
    )
    assert response.status_code == 409
    assert response.json()["detail"]["breed"]["name_en"] == "German Shepherd"


def test_create_breed_validation(client: TestClient, auth_headers) -> None:
    assert (
        client.post(
            "/breeds", json={"species": "dog", "name_en": "x"}, headers=auth_headers
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/breeds", json={"species": "lemur", "name_en": "Syn"}, headers=auth_headers
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/breeds",
            json={"species": "dog", "name_en": "Syn ok", "source": "catalog"},
            headers=auth_headers,
        ).status_code
        == 422
    )
    assert client.post("/breeds", json={"species": "dog", "name_en": "Syn ok"}).status_code == 401


def test_breeds_listed_by_english_name(client: TestClient, auth_headers) -> None:
    """Ordered by the English name (the one on screen). Checked on pairs whose
    order no collation disagrees on; the last one flips if sorted by German
    (Zwergspitz / Mops)."""
    rows = client.get("/breeds", params={"species": "dog"}, headers=auth_headers).json()
    names = [r["name_en"] for r in rows]
    assert names.index("Beagle") < names.index("Yorkshire Terrier")
    assert names.index("English Bulldog") < names.index("French Bulldog")
    assert names.index("Pomeranian") < names.index("Pug")
