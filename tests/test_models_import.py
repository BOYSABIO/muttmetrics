"""Smoke tests: ORM models import and metadata register without a live DB."""

from muttmetrics.db.base import Base
from muttmetrics.models import Breed, Dog, Owner, Service, Visit


def test_all_models_exported() -> None:
    """Public model exports match the five canonical tables."""
    assert {Breed, Dog, Owner, Service, Visit} == {
        Breed,
        Dog,
        Owner,
        Service,
        Visit,
    }


def test_metadata_registers_five_tables() -> None:
    """Importing models registers all tables on shared metadata for Alembic."""
    # Import side effect above must have run first (module-level imports)
    table_names = set(Base.metadata.tables.keys())
    assert table_names == {"breed", "service", "owner", "dog", "visit"}


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
