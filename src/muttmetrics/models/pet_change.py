"""Pet change log: one row per structured field a profile save changed.

Profiles are often filled in after the visits (offline, by hand), and some
facts change (handling, a puppy's size). This log lets an analysis ask what
was known on a visit's date instead of using today's value for every past
visit. Only pet_vocab.TRACKED_PET_FIELDS are logged: no names, no notes.
Values are stored as text (NULL = blank).
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from muttmetrics.db.base import Base

if TYPE_CHECKING:
    from muttmetrics.models.pet import Pet


class PetChange(Base):
    __tablename__ = "pet_change"
    __table_args__ = (Index("ix_pet_change_pet_id_changed_at", "pet_id", "changed_at"),)

    change_id: Mapped[int] = mapped_column(primary_key=True)
    pet_id: Mapped[int] = mapped_column(
        ForeignKey("pet.pet_id", ondelete="CASCADE"), nullable=False
    )
    field: Mapped[str] = mapped_column(String, nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    pet: Mapped[Pet] = relationship(back_populates="changes")
