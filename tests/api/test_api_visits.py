"""POST /visits — auth, validation, and DB persist."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from muttmetrics.models import Breed, Dog, Owner
from muttmetrics.seed.data import SEED_ADD_ONS

MINIMAL_BASE = {
    "visit_date": "2026-09-07",
    "actual_minutes": 60,
}


def _hand_stripping_id(client: TestClient, auth_headers: dict[str, str]) -> int:
    """Resolve seeded hand_stripping id from GET /add-ons."""
    rows = client.get("/add-ons", headers=auth_headers).json()
    return next(row["add_on_id"] for row in rows if row["slug"] == "hand_stripping")


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


def test_get_visit_returns_row(
    client: TestClient,
    demo_dog_owner: tuple[int, int],
    auth_headers: dict[str, str],
) -> None:
    owner_id, dog_id = demo_dog_owner
    created = client.post(
        "/visits",
        json={"dog_id": dog_id, "owner_id": owner_id, **MINIMAL_BASE},
        headers=auth_headers,
    )
    visit_id = created.json()["visit_id"]

    got = client.get(f"/visits/{visit_id}", headers=auth_headers)
    assert got.status_code == 200
    assert got.json()["visit_id"] == visit_id
    assert got.json()["actual_minutes"] == 60


def test_get_visit_unknown_404(client: TestClient, auth_headers: dict[str, str]) -> None:
    assert client.get("/visits/999999", headers=auth_headers).status_code == 404


def test_patch_visit_updates_minutes(
    client: TestClient,
    demo_dog_owner: tuple[int, int],
    auth_headers: dict[str, str],
) -> None:
    owner_id, dog_id = demo_dog_owner
    created = client.post(
        "/visits",
        json={"dog_id": dog_id, "owner_id": owner_id, **MINIMAL_BASE},
        headers=auth_headers,
    )
    assert created.status_code == 201
    visit_id = created.json()["visit_id"]

    patched = client.patch(
        f"/visits/{visit_id}",
        json={"actual_minutes": 75},
        headers=auth_headers,
    )
    assert patched.status_code == 200
    assert patched.json()["actual_minutes"] == 75
    assert patched.json()["visit_date"] == MINIMAL_BASE["visit_date"]


def test_patch_visit_rejects_predicted_field(
    client: TestClient,
    demo_dog_owner: tuple[int, int],
    auth_headers: dict[str, str],
) -> None:
    owner_id, dog_id = demo_dog_owner
    created = client.post(
        "/visits",
        json={"dog_id": dog_id, "owner_id": owner_id, **MINIMAL_BASE},
        headers=auth_headers,
    )
    visit_id = created.json()["visit_id"]

    response = client.patch(
        f"/visits/{visit_id}",
        json={"predicted_min_p50": 99},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_patch_visit_rejects_null_actual_minutes(
    client: TestClient,
    demo_dog_owner: tuple[int, int],
    auth_headers: dict[str, str],
) -> None:
    owner_id, dog_id = demo_dog_owner
    created = client.post(
        "/visits",
        json={"dog_id": dog_id, "owner_id": owner_id, **MINIMAL_BASE},
        headers=auth_headers,
    )
    visit_id = created.json()["visit_id"]

    response = client.patch(
        f"/visits/{visit_id}",
        json={"actual_minutes": None},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_patch_visit_date_recomputs_days_since_last_keeps_predictions(
    client: TestClient,
    db_session: Session,
    auth_headers: dict[str, str],
) -> None:
    owner = Owner(name="Patch Date Owner")
    db_session.add(owner)
    db_session.flush()
    breed = Breed(
        name_en="Patch Date Breed",
        name_de="Patch Date",
        base_groom_minutes=100,
        matting_risk=4,
        recommended_interval_days=60,
    )
    db_session.add(breed)
    db_session.flush()
    dog = Dog(
        owner_id=owner.owner_id,
        name="Patch Date Dog",
        breed_id=breed.breed_id,
        size_band="l",
        handling_score=4,
    )
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
            "actual_minutes": 90,
            "status": "completed",
        },
        headers=auth_headers,
    )
    assert second.status_code == 201
    visit_id = second.json()["visit_id"]
    p50 = second.json()["predicted_min_p50"]
    p90 = second.json()["predicted_min_p90"]
    assert second.json()["days_since_last"] == 30

    patched = client.patch(
        f"/visits/{visit_id}",
        json={"visit_date": "2026-10-11"},
        headers=auth_headers,
    )
    assert patched.status_code == 200
    assert patched.json()["days_since_last"] == 40  # Sep 1 → Oct 11
    assert patched.json()["predicted_min_p50"] == p50  # frozen
    assert patched.json()["predicted_min_p90"] == p90


def test_delete_visit_returns_204_then_404(
    client: TestClient,
    demo_dog_owner: tuple[int, int],
    auth_headers: dict[str, str],
) -> None:
    owner_id, dog_id = demo_dog_owner
    created = client.post(
        "/visits",
        json={"dog_id": dog_id, "owner_id": owner_id, **MINIMAL_BASE},
        headers=auth_headers,
    )
    visit_id = created.json()["visit_id"]

    deleted = client.delete(f"/visits/{visit_id}", headers=auth_headers)
    assert deleted.status_code == 204
    assert deleted.content == b""

    again = client.delete(f"/visits/{visit_id}", headers=auth_headers)
    assert again.status_code == 404

    profile = client.get(f"/dogs/{dog_id}", headers=auth_headers)
    assert profile.status_code == 200
    assert all(v["visit_id"] != visit_id for v in profile.json()["recent_visits"])


def test_create_visit_with_add_ons_persists_and_shows_on_profile(
    client: TestClient,
    demo_dog_owner: tuple[int, int],
    auth_headers: dict[str, str],
) -> None:
    owner_id, dog_id = demo_dog_owner
    add_on_id = _hand_stripping_id(client, auth_headers)

    response = client.post(
        "/visits",
        json={
            "dog_id": dog_id,
            "owner_id": owner_id,
            "add_on_ids": [add_on_id, add_on_id],  # dedupe
            **MINIMAL_BASE,
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data["add_ons"]) == 1
    assert data["add_ons"][0]["slug"] == "hand_stripping"
    assert data["add_ons"][0]["pricing"] == "per_hour"

    got = client.get(f"/visits/{data['visit_id']}", headers=auth_headers)
    assert got.status_code == 200
    assert got.json()["add_ons"][0]["add_on_id"] == add_on_id

    profile = client.get(f"/dogs/{dog_id}", headers=auth_headers)
    assert profile.status_code == 200
    recent = profile.json()["recent_visits"][0]
    assert recent["visit_id"] == data["visit_id"]
    assert recent["add_ons"][0]["slug"] == "hand_stripping"
    assert {a["slug"] for a in SEED_ADD_ONS}  # catalog still seeded


def test_create_visit_unknown_add_on_returns_404_not_500(
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
            "add_on_ids": [999999],
            **MINIMAL_BASE,
        },
        headers=auth_headers,
    )
    assert response.status_code == 404
    assert "Add-on 999999" in response.json()["detail"]


def test_patch_visit_replaces_and_clears_add_ons(
    client: TestClient,
    demo_dog_owner: tuple[int, int],
    auth_headers: dict[str, str],
) -> None:
    owner_id, dog_id = demo_dog_owner
    add_on_id = _hand_stripping_id(client, auth_headers)

    created = client.post(
        "/visits",
        json={
            "dog_id": dog_id,
            "owner_id": owner_id,
            "add_on_ids": [add_on_id],
            **MINIMAL_BASE,
        },
        headers=auth_headers,
    )
    assert created.status_code == 201
    visit_id = created.json()["visit_id"]

    cleared = client.patch(
        f"/visits/{visit_id}",
        json={"add_on_ids": []},
        headers=auth_headers,
    )
    assert cleared.status_code == 200
    assert cleared.json()["add_ons"] == []

    restored = client.patch(
        f"/visits/{visit_id}",
        json={"add_on_ids": [add_on_id]},
        headers=auth_headers,
    )
    assert restored.status_code == 200
    assert restored.json()["add_ons"][0]["slug"] == "hand_stripping"

    # Omit add_on_ids → leave join rows alone
    minutes_only = client.patch(
        f"/visits/{visit_id}",
        json={"actual_minutes": 70},
        headers=auth_headers,
    )
    assert minutes_only.status_code == 200
    assert minutes_only.json()["actual_minutes"] == 70
    assert minutes_only.json()["add_ons"][0]["slug"] == "hand_stripping"
