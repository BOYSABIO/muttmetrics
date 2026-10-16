"""POST /visits — auth, validation, and DB persist."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from muttmetrics.models import Breed, Dog, Owner

MINIMAL_BASE = {
    "visit_date": "2026-09-07",
    "actual_minutes": 60,
}


@pytest.fixture
def demo_dog_owner(db_session: Session) -> tuple[int, int]:
    """Insert a throwaway owner+dog on the rollback pad; return (owner_id, dog_id)."""
    owner = Owner(name="Test Owner")
    db_session.add(owner)
    db_session.flush()
    dog = Dog(owner_id=owner.owner_id, name="Test Dog")
    db_session.add(dog)
    db_session.flush()
    return owner.owner_id, dog.dog_id


def test_create_visit_requires_api_key(client: TestClient) -> None:
    response = client.post(
        "/visits",
        json={"dog_id": 1, "owner_id": 1, **MINIMAL_BASE},
    )
    assert response.status_code == 401


def test_create_visit_invalid_body_returns_422(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        "/visits",
        json={"dog_id": 1, "owner_id": 1, "visit_date": "2026-09-07", "actual_minutes": 0},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_create_visit_unknown_dog_returns_404(
    client: TestClient,
    demo_dog_owner: tuple[int, int],
    auth_headers: dict[str, str],
) -> None:
    owner_id, _ = demo_dog_owner
    response = client.post(
        "/visits",
        json={"dog_id": 999999, "owner_id": owner_id, **MINIMAL_BASE},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_create_visit_persists(
    client: TestClient,
    demo_dog_owner: tuple[int, int],
    auth_headers: dict[str, str],
) -> None:
    owner_id, dog_id = demo_dog_owner
    response = client.post(
        "/visits",
        json={"dog_id": dog_id, "owner_id": owner_id, **MINIMAL_BASE},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["visit_id"] >= 1
    assert data["dog_id"] == dog_id
    assert data["actual_minutes"] == 60


def test_create_visit_without_breed_leaves_predictions_null(
    client: TestClient,
    demo_dog_owner: tuple[int, int],
    auth_headers: dict[str, str],
) -> None:
    owner_id, dog_id = demo_dog_owner
    response = client.post(
        "/visits",
        json={"dog_id": dog_id, "owner_id": owner_id, **MINIMAL_BASE},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["predicted_min_p50"] is None
    assert data["predicted_min_p90"] is None
    assert data["days_since_last"] is None


def test_create_visit_with_breed_sets_predictions(
    client: TestClient,
    db_session: Session,
    auth_headers: dict[str, str],
) -> None:
    owner = Owner(name="Prior Owner")
    db_session.add(owner)
    db_session.flush()
    breed = Breed(
        name_en="Prior Test Breed",
        name_de="Prior Test",
        base_groom_minutes=100,
        matting_risk=4,
        recommended_interval_days=60,
    )
    db_session.add(breed)
    db_session.flush()
    dog = Dog(
        owner_id=owner.owner_id,
        name="Prior Dog",
        breed_id=breed.breed_id,
        size_band="l",
        handling_score=4,
    )
    db_session.add(dog)
    db_session.flush()
    owner_id, dog_id = owner.owner_id, dog.dog_id

    response = client.post(
        "/visits",
        json={
            "dog_id": dog_id,
            "owner_id": owner_id,
            "visit_date": "2026-10-01",
            "actual_minutes": 90,
            "status": "completed",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["days_since_last"] is None
    assert data["predicted_min_p50"] == 157
    assert data["predicted_min_p90"] == 212
    assert data["predicted_min_p90"] >= data["predicted_min_p50"]


def test_create_visit_sets_days_since_last(
    client: TestClient,
    db_session: Session,
    auth_headers: dict[str, str],
) -> None:
    owner = Owner(name="Interval Owner")
    db_session.add(owner)
    db_session.flush()
    dog = Dog(owner_id=owner.owner_id, name="Interval Dog")
    db_session.add(dog)
    db_session.flush()
    owner_id, dog_id = owner.owner_id, dog.dog_id

    first = client.post(
        "/visits",
        json={
            "dog_id": dog_id,
            "owner_id": owner_id,
            "visit_date": "2026-09-01",
            "actual_minutes": 60,
            "status": "completed",
        },
        headers=auth_headers,
    )
    assert first.status_code == 201

    second = client.post(
        "/visits",
        json={
            "dog_id": dog_id,
            "owner_id": owner_id,
            "visit_date": "2026-10-01",
            "actual_minutes": 60,
            "status": "completed",
        },
        headers=auth_headers,
    )
    assert second.status_code == 201
    assert second.json()["days_since_last"] == 30


# --- #177: validation at the edge -------------------------------------------


def test_create_visit_dog_of_another_owner_returns_422(
    client: TestClient,
    db_session: Session,
    demo_dog_owner: tuple[int, int],
    auth_headers: dict[str, str],
) -> None:
    """Both rows exist, but the dog isn't this owner's: refuse, don't mis-file."""
    _, dog_id = demo_dog_owner
    other_owner = Owner(name="Someone Else")
    db_session.add(other_owner)
    db_session.flush()

    response = client.post(
        "/visits",
        json={"dog_id": dog_id, "owner_id": other_owner.owner_id, **MINIMAL_BASE},
        headers=auth_headers,
    )
    assert response.status_code == 422
    assert "belongs to owner" in response.json()["detail"]


def test_create_visit_unknown_service_returns_404_not_500(
    client: TestClient,
    demo_dog_owner: tuple[int, int],
    auth_headers: dict[str, str],
) -> None:
    owner_id, dog_id = demo_dog_owner
    response = client.post(
        "/visits",
        json={
            "dog_id": dog_id,
            "owner_id": owner_id,
            "actual_service_id": 999999,
            **MINIMAL_BASE,
        },
        headers=auth_headers,
    )
    assert response.status_code == 404
    assert "Service 999999" in response.json()["detail"]


@pytest.mark.parametrize("field", ["quoted_price", "final_price", "tip"])
def test_create_visit_negative_money_returns_422(
    client: TestClient,
    demo_dog_owner: tuple[int, int],
    auth_headers: dict[str, str],
    field: str,
) -> None:
    owner_id, dog_id = demo_dog_owner
    response = client.post(
        "/visits",
        json={"dog_id": dog_id, "owner_id": owner_id, field: -5, **MINIMAL_BASE},
        headers=auth_headers,
    )
    assert response.status_code == 422
