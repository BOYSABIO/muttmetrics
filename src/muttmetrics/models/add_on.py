"""Add-on / technique catalog — hand stripping, de-shed, etc. (#192)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from muttmetrics.db.base import Base

if TYPE_CHECKING:
    from muttmetrics.models.visit_add_on import VisitAddOn


class AddOn(Base):
    """
    Catalog of techniques billed or recorded on top of a package service.

    `slug` is the stable API/seed key. `pricing` records how the salon thinks
    about it (flat vs per hour); #192 does not auto-compute final_price from it.
    `price_base` stays NULL in git — optional overlay via pricing.json later.
    """

    __tablename__ = "add_on"
    __table_args__ = (
        CheckConstraint(
            "pricing IN ('flat', 'per_hour')",
            name="ck_add_on_pricing",
        ),
    )

    add_on_id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name_de: Mapped[str | None] = mapped_column(String, nullable=True)
    name_en: Mapped[str | None] = mapped_column(String, nullable=True)
    pricing: Mapped[str] = mapped_column(String, nullable=False)
    price_base: Mapped[float | None] = mapped_column(Numeric, nullable=True)

    visit_links: Mapped[list[VisitAddOn]] = relationship(back_populates="add_on")
