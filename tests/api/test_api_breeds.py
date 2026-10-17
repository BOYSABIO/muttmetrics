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
