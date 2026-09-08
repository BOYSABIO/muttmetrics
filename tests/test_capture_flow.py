"""End-to-end onboarding + visit capture (issue #21 acceptance)."""

import uuid
from datetime import date

import pytest
from fastapi.testclient import TestClient

from muttmetrics.api.app import create_app


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://muttmetrics:muttmetrics@localhost:5432/muttmetrics",
    )
    monkeypatch.setenv("API_KEY", "test-api-key")
    return TestClient(create_app())


def test_new_client_dog_then_visit(client: TestClient) -> None:
    """Register owner+dog without SQL, then POST /visits."""
    headers = {"X-API-Key": "test-api-key"}
    suffix = uuid.uuid4().hex[:8]
    owner_name = f"Flow Owner {suffix}"
    dog_name = f"Flow Dog {suffix}"

    owner_resp = client.post("/owners", json={"name": owner_name}, headers=headers)
    assert owner_resp.status_code == 201
    owner_id = owner_resp.json()["owner_id"]

    # create-or-get: second call must reuse
    owner_again = client.post(
        "/owners",
        json={"name": owner_name.upper()},
        headers=headers,
    )
    assert owner_again.status_code == 200
    assert owner_again.json()["owner_id"] == owner_id

    dog_resp = client.post(
        "/dogs",
        json={"owner_id": owner_id, "name": dog_name},
        headers=headers,
    )
    assert dog_resp.status_code == 201
    dog_id = dog_resp.json()["dog_id"]

    dog_again = client.post(
        "/dogs",
        json={"owner_id": owner_id, "name": dog_name.upper()},
        headers=headers,
    )
    assert dog_again.status_code == 200
    assert dog_again.json()["dog_id"] == dog_id

    visit_resp = client.post(
        "/visits",
        json={
            "dog_id": dog_id,
            "owner_id": owner_id,
            "visit_date": date.today().isoformat(),
            "actual_minutes": 75,
            "condition_score": 2,
            "what_surprised_me": "first visit via create-or-get flow",
            "status": "completed",
        },
        headers=headers,
    )
    assert visit_resp.status_code == 201
    body = visit_resp.json()
    assert body["visit_id"] >= 1
    assert body["dog_id"] == dog_id
    assert body["owner_id"] == owner_id
    assert body["actual_minutes"] == 75
