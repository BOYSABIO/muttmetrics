"""Pet profile data rules (pet-data.md): fixed lists, size by eye vs weight,
blank stays blank, and the change log."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from muttmetrics.models import PetChange


@pytest.fixture
def owner_id(client: TestClient, auth_headers: dict[str, str]) -> int:
    response = client.post(
        "/owners", json={"name": f"Syn Vocab Owner {uuid.uuid4().hex[:8]}"}, headers=auth_headers
    )
    assert response.status_code == 201
    return response.json()["owner_id"]


def _new_pet(client: TestClient, headers: dict[str, str], owner_id: int, species: str = "dog"):
    created = client.post(
        "/pets",
        json={"owner_id": owner_id, "name": f"SynVocab {uuid.uuid4().hex[:8]}", "species": species},
        headers=headers,
    )
    assert created.status_code == 201
    return created.json()["pet_id"]


def _patch(client: TestClient, headers: dict[str, str], pet_id: int, body: dict):
    return client.patch(f"/pets/{pet_id}", json=body, headers=headers)


def _changes(db_session: Session, pet_id: int) -> list[tuple[str, str | None, str | None]]:
    rows = db_session.scalars(
        select(PetChange).where(PetChange.pet_id == pet_id).order_by(PetChange.change_id)
    )
    return [(r.field, r.old_value, r.new_value) for r in rows]


# --- size ---------------------------------------------------------------------


def test_size_by_eye_without_weight(client, auth_headers, owner_id) -> None:
    pet_id = _new_pet(client, auth_headers, owner_id)
    body = _patch(client, auth_headers, pet_id, {"size_band": "l"}).json()
    assert (body["size_band"], body["size_source"]) == ("l", "eye")

    cleared = _patch(client, auth_headers, pet_id, {"size_band": None}).json()
    assert (cleared["size_band"], cleared["size_source"]) == (None, None)


def test_weight_overrides_eye_and_clearing_weight_blanks_size(
    client, auth_headers, owner_id
) -> None:
    pet_id = _new_pet(client, auth_headers, owner_id)
    _patch(client, auth_headers, pet_id, {"size_band": "xl"})
    weighed = _patch(client, auth_headers, pet_id, {"weight_kg": 8}).json()
    assert (weighed["size_band"], weighed["size_source"]) == ("s", "weight")

    unweighed = _patch(client, auth_headers, pet_id, {"weight_kg": None}).json()
    assert (unweighed["size_band"], unweighed["size_source"]) == (None, None)

    # Clearing the weight while picking a size keeps the picked one.
    _patch(client, auth_headers, pet_id, {"weight_kg": 8})
    both = _patch(client, auth_headers, pet_id, {"weight_kg": None, "size_band": "m"}).json()
    assert (both["size_band"], both["size_source"]) == ("m", "eye")


@pytest.mark.parametrize("bad", ["xs", "medium", "M"])
def test_size_band_must_be_on_the_list(client, auth_headers, owner_id, bad: str) -> None:
    pet_id = _new_pet(client, auth_headers, owner_id)
    assert _patch(client, auth_headers, pet_id, {"size_band": bad}).status_code == 422


# --- coat ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "species,coat,ok",
    [
        ("dog", "wire", True),
        ("dog", "silky", True),
        ("dog", "short", False),  # a cat coat
        ("dog", "single", False),  # retired spelling
        ("cat", "long", True),
        ("cat", "curly", False),
        ("dog", "Curly", False),  # one spelling per meaning
    ],
)
def test_coat_type_per_species(client, auth_headers, owner_id, species, coat, ok) -> None:
    pet_id = _new_pet(client, auth_headers, owner_id, species)
    response = _patch(client, auth_headers, pet_id, {"coat_type": coat})
    assert (response.status_code == 200) is ok
    if ok:
        assert response.json()["coat_type"] == coat


def test_changing_species_drops_a_coat_that_no_longer_fits(client, auth_headers, owner_id) -> None:
    pet_id = _new_pet(client, auth_headers, owner_id)
    _patch(client, auth_headers, pet_id, {"coat_type": "curly"})
    body = _patch(client, auth_headers, pet_id, {"species": "cat"}).json()
    assert body["species"] == "cat"
    assert body["coat_type"] is None


@pytest.mark.parametrize("value,status", [(1, 200), (3, 200), (0, 422), (4, 422)])
def test_coat_thickness_is_one_to_three(client, auth_headers, owner_id, value, status) -> None:
    pet_id = _new_pet(client, auth_headers, owner_id)
    assert _patch(client, auth_headers, pet_id, {"coat_thickness": value}).status_code == status


# --- other fields -------------------------------------------------------------


@pytest.mark.parametrize("bad", ["unknown", "F", "Female"])
def test_sex_is_female_male_or_blank(client, auth_headers, owner_id, bad: str) -> None:
    pet_id = _new_pet(client, auth_headers, owner_id)
    assert _patch(client, auth_headers, pet_id, {"sex": bad}).status_code == 422
    assert _patch(client, auth_headers, pet_id, {"sex": "female"}).status_code == 200


@pytest.mark.parametrize(
    "retired", ["hair_or_fur", "coat_density", "undercoat", "sheds", "mobility_notes", "vet_notes"]
)
def test_retired_fields_are_refused(client, auth_headers, owner_id, retired: str) -> None:
    pet_id = _new_pet(client, auth_headers, owner_id)
    value = True if retired in ("undercoat", "sheds") else "x"
    assert _patch(client, auth_headers, pet_id, {retired: value}).status_code == 422


def test_usual_cut_and_health_notes_round_trip(client, auth_headers, owner_id) -> None:
    pet_id = _new_pet(client, auth_headers, owner_id)
    body = _patch(
        client,
        auth_headers,
        pet_id,
        {"usual_cut": "teddy face, 1 cm body", "health_notes": "itchy skin"},
    ).json()
    assert body["usual_cut"] == "teddy face, 1 cm body"
    assert body["health_notes"] == "itchy skin"


def test_blank_stays_blank_when_other_fields_are_saved(client, auth_headers, owner_id) -> None:
    """Saving the name must not turn 'nobody checked' into 'no'."""
    pet_id = _new_pet(client, auth_headers, owner_id)
    body = _patch(client, auth_headers, pet_id, {"name": "SynVocab Renamed"}).json()
    for field in ("muzzle_required", "two_person_job", "senior_flag", "coat_type", "size_band"):
        assert body[field] is None, field


# --- change log ---------------------------------------------------------------


def test_change_log_records_only_real_changes(
    client, auth_headers, owner_id, db_session: Session
) -> None:
    pet_id = _new_pet(client, auth_headers, owner_id)
    _patch(client, auth_headers, pet_id, {"handling_score": 2, "muzzle_required": False})
    _patch(client, auth_headers, pet_id, {"handling_score": 2})  # same value: no row
    _patch(client, auth_headers, pet_id, {"handling_score": 4, "temperament_notes": "x"})
    _patch(client, auth_headers, pet_id, {"weight_kg": "7.50"})

    assert _changes(db_session, pet_id) == [
        ("handling_score", None, "2"),
        ("muzzle_required", None, "false"),
        ("handling_score", "2", "4"),
        ("weight_kg", None, "7.5"),
        ("size_band", None, "s"),
        ("size_source", None, "weight"),
    ]


def test_change_log_skips_names_and_notes(
    client, auth_headers, owner_id, db_session: Session
) -> None:
    pet_id = _new_pet(client, auth_headers, owner_id)
    _patch(
        client,
        auth_headers,
        pet_id,
        {"name": "SynVocab Other", "usual_cut": "short", "health_notes": "x"},
    )
    assert _changes(db_session, pet_id) == []
