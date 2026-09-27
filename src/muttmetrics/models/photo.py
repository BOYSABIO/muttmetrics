"""Photos table - one row per stored image file."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from muttmetrics.db.base import Base

if TYPE_CHECKING:
    from muttmetrics.models.dog import Dog
    from muttmetrics.models.visit import Visit


class Photo(Base):
    """
    One row per stored image file.

    Bytes live on disk under the configured photo root; this table holds the
    metadata plus the relative storage_key that locates them. Deleting a
    row does not delete the file - see docs/privacy.md for the procedure.
    """

    __tablename__ = "photo"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('intake', 'after', 'profile')",
            name="ck_photo_kind",
        ),
        CheckConstraint(
            "(kind = 'profile' AND visit_id IS NULL) OR "
            "(kind IN ('intake', 'after') AND visit_id IS NOT NULL)",
            name="ck_photo_kind_visit",
        ),
        CheckConstraint("byte_size > 0", name="ck_photo_byte_size"),
        UniqueConstraint("storage_key", name="uq_photo_storage_key"),
        Index("ix_photo_visit_id", "visit_id"),
        Index("ix_photo_dog_id_kind", "dog_id", "kind"),
    )

    # Identity
    photo_id: Mapped[int] = mapped_column(primary_key=True)

    # What it belongs to: always a dog; a visit only for intake/after shots
    dog_id: Mapped[int] = mapped_column(ForeignKey("dog.dog_id"), nullable=False)
    visit_id: Mapped[int | None] = mapped_column(ForeignKey("visit.visit_id"), nullable=True)
    kind: Mapped[str] = mapped_column(Text, nullable=False)

    # Where the bytes are (key is relative - see ADR / docs; host move is config only)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    storage_backend: Mapped[str] = mapped_column(Text, nullable=False, server_default="local")

    # What the bytes are
    content_type: Mapped[str] = mapped_column(Text, nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(Text, nullable=False)

    # When it arrived - retention and the orphan sweep both need this
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    dog: Mapped[Dog] = relationship(back_populates="photos")
    visit: Mapped[Visit | None] = relationship(back_populates="photos")
