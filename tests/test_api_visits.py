"""POST /visits — auth, validation, and DB persist."""

import pytest
from fastapi.testclient import TestClient

from muttmetrics.api.app import create_app
from muttmetrics.db.session import session_scope
from muttmetrics.models import Dog, Owner

MINIMAL_BASE = {
    "visit_date": "2026-09-07",
    "actual_minutes": 60,
}


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://muttmetrics:muttmetrics@localhost:5432/muttmetrics",
    )
    monkeypatch.setenv("API_KEY", "test-api-key")
    return TestClient(create_app())


@pytest.fixture
def demo_dog_owner() -> tuple[int, int]:
    """Insert a throwaway owner+dog; return (owner_id, dog_id)."""
    with session_scope() as session:
        owner = Owner(name="Test Owner")
        session.add(owner)
        session.flush()
        dog = Dog(owner_id=owner.owner_id, name="Test Dog")
        session.add(dog)
        session.flush()
        return owner.owner_id, dog.dog_id


def test_create_visit_requires_api_key(client: TestClient) -> None:
    response = client.post(
        "/visits",
        json={"dog_id": 1, "owner_id": 1, **MINIMAL_BASE},
    )
    assert response.status_code == 401


def test_create_visit_invalid_body_returns_422(client: TestClient) -> None:
    response = client.post(
        "/visits",
        json={"dog_id": 1, "owner_id": 1, "visit_date": "2026-09-07", "actual_minutes": 0},
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 422


def test_create_visit_unknown_dog_returns_404(
    client: TestClient, demo_dog_owner: tuple[int, int]
) -> None:
    owner_id, _ = demo_dog_owner
    response = client.post(
        "/visits",
        json={"dog_id": 999999, "owner_id": owner_id, **MINIMAL_BASE},
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 404


def test_create_visit_persists(client: TestClient, demo_dog_owner: tuple[int, int]) -> None:
    owner_id, dog_id = demo_dog_owner
    response = client.post(
        "/visits",
        json={"dog_id": dog_id, "owner_id": owner_id, **MINIMAL_BASE},
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["visit_id"] >= 1
    assert data["dog_id"] == dog_id
    assert data["actual_minutes"] == 60
