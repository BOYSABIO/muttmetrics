"""GET /add-ons — catalog for the capture SPA picker (#192)."""

from fastapi.testclient import TestClient

from muttmetrics.seed.data import SEED_ADD_ONS


def test_list_add_ons_requires_api_key(client: TestClient) -> None:
    response = client.get("/add-ons")
    assert response.status_code == 401


def test_list_add_ons_returns_catalog(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/add-ons", headers=auth_headers)
    assert response.status_code == 200
    rows = response.json()
    assert {row["slug"] for row in rows} == {a["slug"] for a in SEED_ADD_ONS}
    hand = next(row for row in rows if row["slug"] == "hand_stripping")
    assert isinstance(hand["add_on_id"], int)
    assert hand["pricing"] == "per_hour"
    assert hand["name_en"]
