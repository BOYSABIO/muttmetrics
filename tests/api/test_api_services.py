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
