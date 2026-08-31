"""Owner entity = client contact info and derived visit-history aggregates."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from muttmetrics.db.base import Base

if TYPE_CHECKING:
    from muttmetrics.models.dog import Dog
    from muttmetrics.models.visit import Visit


class Owner(Base):
    """
    Grooming client (human). Derived columns are recomputed from visits
    """

    __tablename__ = "owner"

    # Hand entered fields:
    owner_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    locale: Mapped[str] = mapped_column(String, nullable=False, server_default="de")
    address_area: Mapped[str | None] = mapped_column(String, nullable=True)
    preferred_channel: Mapped[str | None] = mapped_column(String, nullable=True)
    client_since: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Derived columns:
    visit_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    avg_rebook_days: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    neglect_rate: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    cancellation_rate: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    no_show_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    avg_tip_pct: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    lifetime_value: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    reliability_score: Mapped[float | None] = mapped_column(Numeric, nullable=True)

    # Relationships
    dogs: Mapped[list[Dog]] = relationship(back_populates="owner")
    visits: Mapped[list[Visit]] = relationship(back_populates="owner")
