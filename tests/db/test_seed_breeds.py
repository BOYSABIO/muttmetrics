"""Seeding breeds: catalog rows match on species + name, any capitalisation,
and a breed first added in the salon is promoted to a catalog breed."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from muttmetrics.models import Breed
from muttmetrics.pet_vocab import COAT_TYPES_BY_SPECIES, SIZE_BANDS
from muttmetrics.seed.data import SEED_BREEDS
from muttmetrics.seed.run import _upsert_breed


def test_seed_breeds_are_clean() -> None:
    seen = set()
    for row in SEED_BREEDS:
        key = (row["species"], row["name_en"].lower())
        assert key not in seen, key
        seen.add(key)
        coat = row["default_coat_type"]
        assert coat is None or coat in COAT_TYPES_BY_SPECIES[row["species"]], row["name_en"]
        assert row["typical_size_band"] in SIZE_BANDS, row["name_en"]
        assert row["base_groom_minutes"] > 0 and 1 <= row["matting_risk"] <= 5


def test_upsert_promotes_a_salon_breed(db_session: Session) -> None:
    salon = Breed(species="dog", name_en="syn promoted hound", source="salon")
    db_session.add(salon)
    db_session.flush()
    _upsert_breed(
        db_session,
        {
            "species": "dog",
            "name_en": "Syn Promoted Hound",
            "base_groom_minutes": 70,
            "matting_risk": 2,
        },
    )
    db_session.flush()
    rows = db_session.scalars(select(Breed).where(Breed.name_en.ilike("syn promoted hound"))).all()
    assert len(rows) == 1
    assert rows[0].source == "catalog"
    assert rows[0].base_groom_minutes == 70


def test_upsert_keeps_species_apart(db_session: Session) -> None:
    db_session.add(Breed(species="cat", name_en="Syn Both Kinds"))
    db_session.flush()
    _upsert_breed(db_session, {"species": "dog", "name_en": "Syn Both Kinds"})
    db_session.flush()
    species = sorted(
        db_session.scalars(select(Breed.species).where(Breed.name_en == "Syn Both Kinds"))
    )
    assert species == ["cat", "dog"]
