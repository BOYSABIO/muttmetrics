"""GET /breeds — catalog for Directory pickers."""

from fastapi.testclient import TestClient


def test_list_breeds_requires_api_key(client: TestClient) -> None:
    response = client.get("/breeds")
    assert response.status_code == 401


def test_list_breeds_returns_catalog(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/breeds", headers=auth_headers)
    assert response.status_code == 200
    rows = response.json()
    assert isinstance(rows, list)
    assert len(rows) >= 1

    first = rows[0]
    assert "breed_id" in first
    assert "name_en" in first or "name_de" in first
