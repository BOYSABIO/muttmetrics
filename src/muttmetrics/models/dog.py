"""Dog entity - stable physical/temperament priors + derived visit aggregates."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from muttmetrics.db.base import Base

if TYPE_CHECKING:
    from muttmetrics.models.breed import Breed
    from muttmetrics.models.owner import Owner
    from muttmetrics.models.visit import Visit


class Dog(Base):
    """
    A groomer's client dog. Temperament fields are internal-only.

    List fields use Postgres ARRAY(Text), non JSON.
    Derived columns follow ADR-001 - nullable, recompute only.
    """

    __tablename__ = "dog"
    __table_args__ = (
        CheckConstraint(
            "handling_score IS NULL OR (handling_score >= 1 AND handling_score <= 5)",
            name="ck_dog_handling_score",
        ),
    )

    # Identity + Ownership
    dog_id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("owner.owner_id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    breed_id: Mapped[int | None] = mapped_column(ForeignKey("breed.breed_id"), nullable=True)
    breed_secondary_id: Mapped[int | None] = mapped_column(
        ForeignKey("breed.breed_id"), nullable=True
    )
    sex: Mapped[str | None] = mapped_column(String, nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Numeric, nullable=True)

    # Coat (Physical Predictors)
    coat_type: Mapped[str | None] = mapped_column(String, nullable=True)
    hair_or_fur: Mapped[str | None] = mapped_column(String, nullable=True)
    coat_density: Mapped[str | None] = mapped_column(String, nullable=True)
    undercoat: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    sheds: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # Temperament (Internal-Only)
    handling_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fear_triggers: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    muzzle_required: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    two_person_job: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    temperament_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Medical / risk
    skin_conditions: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    senior_flag: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    mobility_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    vet_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Derived (ADR-001)
    size_band: Mapped[str | None] = mapped_column(String, nullable=True)
    visit_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    avg_duration_min: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    duration_stddev_min: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    typical_interval_days: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    last_visit_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    next_due_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Relationships (TYPE_CHECKING imports above — no circular import at runtime)
    owner: Mapped[Owner] = relationship(back_populates="dogs")
    breed: Mapped[Breed | None] = relationship(foreign_keys=[breed_id])
    breed_secondary: Mapped[Breed | None] = relationship(foreign_keys=[breed_secondary_id])
    visits: Mapped[list[Visit]] = relationship(back_populates="dog")
