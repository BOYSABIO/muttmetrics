"""GET /services - catalog for the capture SPA picker."""

from fastapi.testclient import TestClient


def test_list_services_requires_api_key(client: TestClient) -> None:
    response = client.get("/services")
    assert response.status_code == 401


def test_list_services_returns_catalog(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/services", headers=auth_headers)
    assert response.status_code == 200
    rows = response.json()
    assert isinstance(rows, list)
    assert len(rows) >= 1

    first = rows[0]
    assert "service_id" in first
    assert "slug" in first
    assert "name_en" in first

    slugs = {row["slug"] for row in rows}
    assert "full_groom" in slugs
