"""Visit fact table - one row per groom; training labels and event capture."""

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

if TYPE_CHECKING:
    from muttmetrics.models.dog import Dog
    from muttmetrics.models.owner import Owner
    from muttmetrics.models.service import Service


class Visit(Base):
    """
    One groom event. List fields use Postgres ARRAY(Text), non JSON.

    System-computed columns (days_since_last, etc.) follow ADR-001:
    written at create/score time, not by the owner/dog recompute job.
    """

    __tablename__ = "visit"
    __table_args__ = (
        CheckConstraint(
            "condition_score IS NULL OR (condition_score >= 0 AND condition_score <= 5)",
            name="ck_visit_condition_score",
        ),
        CheckConstraint(
            "behaviour_this_visit IS NULL OR "
            "(behaviour_this_visit >= 1 AND behaviour_this_visit <= 5)",
            name="ck_visit_behaviour_this_visit",
        ),
        CheckConstraint(
            "status IS NULL OR status IN ('completed', 'cancelled', 'no_show')",
            name="ck_visit_status",
        ),
        Index("ix_visit_dog_id", "dog_id"),
        Index("ix_visit_owner_id", "owner_id"),
        Index("ix_visit_visit_date", "visit_date"),
        Index("ix_visit_booked_service_id", "booked_service_id"),
        Index("ix_visit_actual_service_id", "actual_service_id"),
    )

    # Identity
    visit_id: Mapped[int] = mapped_column(primary_key=True)
    dog_id: Mapped[int] = mapped_column(ForeignKey("dog.dog_id"), nullable=False)
    owner_id: Mapped[int] = mapped_column(ForeignKey("owner.owner_id"), nullable=False)
    visit_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Booking (expected)
    booked_service_id: Mapped[int | None] = mapped_column(
        ForeignKey("service.service_id"), nullable=True
    )
    booking_channel: Mapped[str | None] = mapped_column(String, nullable=True)
    is_emergency: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    days_since_last: Mapped[int | None] = mapped_column(Integer, nullable=True)
    intake_photos: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    predicted_min_p50: Mapped[int | None] = mapped_column(Integer, nullable=True)
    predicted_min_p90: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quoted_price: Mapped[float | None] = mapped_column(Numeric, nullable=True)

    # Intake (what showed up)
    condition_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    matting_locations: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    fleas_or_parasites: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    arrived_wet_dirty: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # Outcome (what happened)
    actual_service_id: Mapped[int | None] = mapped_column(
        ForeignKey("service.service_id"), nullable=True
    )
    pivoted: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    pivot_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    shaved_down: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    actual_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    final_price: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    tip: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    add_ons: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)

    # Qualitative
    what_surprised_me: Mapped[str | None] = mapped_column(Text, nullable=True)
    behaviour_this_visit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    after_photos: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)

    # Status
    status: Mapped[str | None] = mapped_column(String, nullable=True)
    cancelled_hours_before: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    dog: Mapped[Dog] = relationship(back_populates="visits")
    owner: Mapped[Owner] = relationship(back_populates="visits")
    booked_service: Mapped[Service | None] = relationship(foreign_keys=[booked_service_id])
    actual_service: Mapped[Service | None] = relationship(foreign_keys=[actual_service_id])
