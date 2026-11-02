"""GET /services - catalog for the capture SPA picker."""

from fastapi.testclient import TestClient

from muttmetrics.seed.data import SEED_SERVICES


def test_list_services_requires_api_key(client: TestClient) -> None:
    response = client.get("/services")
    assert response.status_code == 401


def test_list_services_returns_catalog(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/services", headers=auth_headers)
    assert response.status_code == 200
    rows = response.json()
    assert {row["slug"] for row in rows} == {s["slug"] for s in SEED_SERVICES}
    full = next(row for row in rows if row["slug"] == "full_groom")
    assert isinstance(full["service_id"], int)
    assert full["name_en"]
    assert full["species"] is None  # NULL = all species (ADR-004)


def test_list_services_species_includes_untagged(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """NULL services stay in the picker for both dog and cat."""
    dogs = client.get("/services", params={"species": "dog"}, headers=auth_headers)
    cats = client.get("/services", params={"species": "cat"}, headers=auth_headers)
    assert dogs.status_code == 200
    assert cats.status_code == 200
    assert {row["slug"] for row in dogs.json()} == {s["slug"] for s in SEED_SERVICES}
    assert {row["slug"] for row in cats.json()} == {s["slug"] for s in SEED_SERVICES}

    bad = client.get("/services", params={"species": "lemur"}, headers=auth_headers)
    assert bad.status_code == 422
