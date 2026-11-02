"""Breed reference table - hand-encoded priors for cold start."""

from sqlalchemy import Boolean, CheckConstraint, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from muttmetrics.db.base import Base
from muttmetrics.species import DEFAULT_SPECIES, SPECIES_CHECK_SQL


class Breed(Base):
    """
    Domain priors per breed (DE/EN names, coat defaults, duration, matting risk).

    ``species`` must match the pet (ADR-004). List/array fields on other models
    use Postgres ARRAY (see ADR / model docstrings).
    """

    __tablename__ = "breed"
    __table_args__ = (CheckConstraint(SPECIES_CHECK_SQL, name="ck_breed_species"),)

    breed_id: Mapped[int] = mapped_column(primary_key=True)
    species: Mapped[str] = mapped_column(String, nullable=False, server_default=DEFAULT_SPECIES)
    name_de: Mapped[str | None] = mapped_column(String, nullable=True)
    name_en: Mapped[str | None] = mapped_column(String, nullable=True)
    default_coat_type: Mapped[str | None] = mapped_column(String, nullable=True)
    default_hair_or_fur: Mapped[str | None] = mapped_column(String, nullable=True)
    typical_size_band: Mapped[str | None] = mapped_column(String, nullable=True)
    base_groom_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    matting_risk: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1..5
    blows_coat: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    recommended_interval_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_care_protocol: Mapped[str | None] = mapped_column(Text, nullable=True)
