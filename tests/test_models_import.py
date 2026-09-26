"""Smoke tests: ORM models import and metadata register without a live DB."""

from muttmetrics import models
from muttmetrics.db.base import Base
from muttmetrics.models import Dog, Owner, Photo, Visit


def test_all_models_exported() -> None:
    """Public model exports stay in sync with the tables."""
    assert set(models.__all__) == {"Breed", "Dog", "Owner", "Photo", "Service", "Visit"}


def test_metadata_registers_all_tables() -> None:
    """Importing models registers all tables on shared metadata for Alembic."""
    # Import side effect above must have run first (module-level imports)
    table_names = set(Base.metadata.tables.keys())
    assert table_names == {"breed", "service", "owner", "dog", "visit", "photo"}


def test_owner_dog_visit_relationship_chain() -> None:
    """Relationships are bidirectional along owner → dogs → visits."""
    assert Owner.dogs.property.back_populates == "owner"
    assert Dog.owner.property.back_populates == "dogs"
    assert Dog.visits.property.back_populates == "dog"
    assert Visit.dog.property.back_populates == "visits"
    assert Owner.visits.property.back_populates == "owner"
    assert Visit.owner.property.back_populates == "visits"


def test_visit_required_columns() -> None:
    """Training label and visit date are NOT NULL per schema design."""
    assert Visit.__table__.c.actual_minutes.nullable is False
    assert Visit.__table__.c.visit_date.nullable is False


def test_photo_visit_optional_dog_required() -> None:
    """Profile photos have no visit; every photo belongs to a dog."""
    assert Photo.__table__.c.visit_id.nullable is True
    assert Photo.__table__.c.dog_id.nullable is False


def test_photo_storage_key_unique() -> None:
    """One row per stored file - no two rows point at the same bytes."""
    assert any(c.name == "uq_photo_storage_key" for c in Photo.__table__.constraints)
