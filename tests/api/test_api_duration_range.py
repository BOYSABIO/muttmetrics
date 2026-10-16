"""GET /dogs/{id}/duration-range (#26)."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from muttmetrics.models import Breed, Dog, Owner


def test_duration_range_requires_api_key(client: TestClient) -> None:
    assert client.get("/dogs/1/duration-range").status_code == 401


def test_duration_range_unknown_dog_404(client: TestClient, auth_headers: dict[str, str]) -> None:
    r = client.get("/dogs/999999/duration-range", headers=auth_headers)
    assert r.status_code == 404


def test_duration_range_with_breed(
    client: TestClient, db_session: Session, auth_headers: dict[str, str]
) -> None:
    owner = Owner(name="Range Owner")
    db_session.add(owner)
    db_session.flush()
    breed = Breed(
        name_en="Range Breed",
        name_de="Range",
        base_groom_minutes=100,
        matting_risk=4,
        recommended_interval_days=60,
    )
    db_session.add(breed)
    db_session.flush()
    dog = Dog(
        owner_id=owner.owner_id,
        name="Range Dog",
        breed_id=breed.breed_id,
        size_band="l",
        handling_score=4,
    )
    db_session.add(dog)
    db_session.flush()
    dog_id = dog.dog_id

    r = client.get(
        f"/dogs/{dog_id}/duration-range",
        params={"as_of": "2026-10-01"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["predicted_min_p50"] == 157
    assert data["predicted_min_p90"] == 212
    assert data["skipped_reason"] is None


def test_duration_range_matches_visit_create(
    client: TestClient, db_session: Session, auth_headers: dict[str, str]
) -> None:
    """Same dog + as_of as first visit → same P50/P90."""
    owner = Owner(name="Sync Owner")
    db_session.add(owner)
    db_session.flush()
    breed = Breed(
        name_en="Sync Breed",
        name_de="Sync",
        base_groom_minutes=100,
        matting_risk=4,
        recommended_interval_days=60,
    )
    db_session.add(breed)
    db_session.flush()
    dog = Dog(
        owner_id=owner.owner_id,
        name="Sync Dog",
        breed_id=breed.breed_id,
        size_band="l",
        handling_score=4,
    )
    db_session.add(dog)
    db_session.flush()
    owner_id, dog_id = owner.owner_id, dog.dog_id

    preview = client.get(
        f"/dogs/{dog_id}/duration-range",
        params={"as_of": "2026-10-01"},
        headers=auth_headers,
    )
    created = client.post(
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
    assert preview.status_code == 200
    assert created.status_code == 201
    p, c = preview.json(), created.json()
    assert p["predicted_min_p50"] == c["predicted_min_p50"]
    assert p["predicted_min_p90"] == c["predicted_min_p90"]
    assert p["days_since_last"] == c["days_since_last"]


def test_duration_range_weight_changes_prediction(
    client: TestClient, db_session: Session, auth_headers: dict[str, str]
) -> None:
    """Same breed, different weights → different P50/P90 via size_band_from_weight (#171)."""
    owner = Owner(name="Size Owner")
    db_session.add(owner)
    db_session.flush()
    breed = Breed(
        name_en="Size Breed",
        name_de="Size",
        base_groom_minutes=100,
        matting_risk=1,
        recommended_interval_days=60,
    )
    db_session.add(breed)
    db_session.flush()

    small = Dog(
        owner_id=owner.owner_id,
        name="Small Dog",
        breed_id=breed.breed_id,
        weight_kg=8,  # → s → 0.85
    )
    giant = Dog(
        owner_id=owner.owner_id,
        name="Giant Dog",
        breed_id=breed.breed_id,
        weight_kg=50,  # → xl → 1.30
    )
    db_session.add_all([small, giant])
    db_session.flush()

    r_small = client.get(
        f"/dogs/{small.dog_id}/duration-range",
        params={"as_of": "2026-10-16"},
        headers=auth_headers,
    )
    r_giant = client.get(
        f"/dogs/{giant.dog_id}/duration-range",
        params={"as_of": "2026-10-16"},
        headers=auth_headers,
    )
    assert r_small.status_code == 200
    assert r_giant.status_code == 200
    assert r_small.json()["predicted_min_p50"] == 85
    assert r_giant.json()["predicted_min_p50"] == 130
    assert r_small.json()["predicted_min_p50"] != r_giant.json()["predicted_min_p50"]
