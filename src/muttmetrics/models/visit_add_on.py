"""Visit ↔ add-on join (#192)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, PrimaryKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from muttmetrics.db.base import Base

if TYPE_CHECKING:
    from muttmetrics.models.add_on import AddOn
    from muttmetrics.models.visit import Visit


class VisitAddOn(Base):
    """One technique applied on one visit. Composite PK prevents duplicates."""

    __tablename__ = "visit_add_on"
    __table_args__ = (PrimaryKeyConstraint("visit_id", "add_on_id"),)

    visit_id: Mapped[int] = mapped_column(Integer, ForeignKey("visit.visit_id"), nullable=False)
    add_on_id: Mapped[int] = mapped_column(Integer, ForeignKey("add_on.add_on_id"), nullable=False)

    visit: Mapped[Visit] = relationship(back_populates="visit_add_ons")
    add_on: Mapped[AddOn] = relationship(back_populates="visit_links")
