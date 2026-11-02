"""Pet entity — one animal (dog, cat, later species) + derived visit aggregates."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from muttmetrics.db.base import Base
from muttmetrics.species import DEFAULT_SPECIES, SPECIES_CHECK_SQL

if TYPE_CHECKING:
    from muttmetrics.models.breed import Breed
    from muttmetrics.models.owner import Owner
    from muttmetrics.models.photo import Photo
    from muttmetrics.models.visit import Visit


class Pet(Base):
    """
    A groomer's client animal. Temperament fields are internal-only.

    ``species`` discriminates dog/cat (ADR-004). List fields use Postgres ARRAY.
    Derived columns follow ADR-001 - nullable, recompute only.
    """

    __tablename__ = "pet"
    __table_args__ = (
        CheckConstraint(
            "handling_score IS NULL OR (handling_score >= 1 AND handling_score <= 5)",
            name="ck_pet_handling_score",
        ),
        CheckConstraint(SPECIES_CHECK_SQL, name="ck_pet_species"),
        Index("ix_pet_owner_id", "owner_id"),
        Index("ix_pet_breed_id", "breed_id"),
        Index("ix_pet_breed_secondary_id", "breed_secondary_id"),
    )

    pet_id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("owner.owner_id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    species: Mapped[str] = mapped_column(String, nullable=False, server_default=DEFAULT_SPECIES)
    breed_id: Mapped[int | None] = mapped_column(ForeignKey("breed.breed_id"), nullable=True)
    breed_secondary_id: Mapped[int | None] = mapped_column(
        ForeignKey("breed.breed_id"), nullable=True
    )
    sex: Mapped[str | None] = mapped_column(String, nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Numeric, nullable=True)

    coat_type: Mapped[str | None] = mapped_column(String, nullable=True)
    hair_or_fur: Mapped[str | None] = mapped_column(String, nullable=True)
    coat_density: Mapped[str | None] = mapped_column(String, nullable=True)
    undercoat: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    sheds: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    handling_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fear_triggers: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    muzzle_required: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    two_person_job: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    temperament_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    skin_conditions: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    senior_flag: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    mobility_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    vet_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    size_band: Mapped[str | None] = mapped_column(String, nullable=True)
    visit_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    avg_duration_min: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    duration_stddev_min: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    typical_interval_days: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    last_visit_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    next_due_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    owner: Mapped[Owner] = relationship(back_populates="pets")
    breed: Mapped[Breed | None] = relationship(foreign_keys=[breed_id])
    breed_secondary: Mapped[Breed | None] = relationship(foreign_keys=[breed_secondary_id])
    visits: Mapped[list[Visit]] = relationship(back_populates="pet")
    photos: Mapped[list[Photo]] = relationship(back_populates="pet")
