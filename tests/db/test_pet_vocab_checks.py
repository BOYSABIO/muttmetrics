"""The database itself refuses values off the lists (pet_vocab.py), so SQL
edits and future code paths can't sneak in a second spelling."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from muttmetrics.models import Breed, Owner, Pet


def _pet(db_session: Session, **fields) -> Pet:
    owner = Owner(name="Syn Check Owner")
    db_session.add(owner)
    db_session.flush()
    pet = Pet(owner_id=owner.owner_id, name="SynCheck Pet", **fields)
    db_session.add(pet)
    return pet


@pytest.mark.parametrize(
    "fields",
    [
        {"species": "dog", "coat_type": "short"},
        {"species": "cat", "coat_type": "wire"},
        {"coat_type": "single"},
        {"coat_thickness": 4},
        {"size_band": "xs", "size_source": "eye"},
        {"size_band": "m"},  # a size must say where it came from
        {"size_source": "eye"},  # and a source never floats alone
        {"sex": "unknown"},
    ],
)
def test_pet_checks_refuse(db_session: Session, fields: dict) -> None:
    nested = db_session.begin_nested()
    _pet(db_session, **fields)
    with pytest.raises(IntegrityError):
        db_session.flush()
    nested.rollback()


def test_pet_checks_accept_clean_row(db_session: Session) -> None:
    _pet(
        db_session,
        species="dog",
        coat_type="combination",
        coat_thickness=2,
        size_band="l",
        size_source="eye",
        sex="male",
    )
    db_session.flush()


def test_breed_names_unique_per_species_any_case(db_session: Session) -> None:
    db_session.add(Breed(species="dog", name_en="Syn Unique Hound"))
    db_session.flush()
    db_session.add(Breed(species="cat", name_en="Syn Unique Hound"))  # other species: fine
    db_session.flush()
    nested = db_session.begin_nested()
    db_session.add(Breed(species="dog", name_en="syn unique HOUND"))
    with pytest.raises(IntegrityError):
        db_session.flush()
    nested.rollback()


def test_breed_source_defaults_to_catalog(db_session: Session) -> None:
    breed = Breed(species="dog", name_en="Syn Source Hound")
    db_session.add(breed)
    db_session.flush()
    source = db_session.scalar(
        text("SELECT source FROM breed WHERE breed_id = :id"), {"id": breed.breed_id}
    )
    assert source == "catalog"
