"""Breed reference table - hand-encoded priors for cold start."""

from sqlalchemy import Boolean, CheckConstraint, Index, Integer, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from muttmetrics.db.base import Base
from muttmetrics.pet_vocab import (
    BREED_COAT_TYPE_CHECK_SQL,
    BREED_SIZE_BAND_CHECK_SQL,
    BREED_SOURCE_CHECK_SQL,
)
from muttmetrics.species import DEFAULT_SPECIES, SPECIES_CHECK_SQL


class Breed(Base):
    """
    Domain priors per breed (DE/EN names, coat defaults, duration, matting risk).

    ``species`` must match the pet (ADR-004). List/array fields on other models
    use Postgres ARRAY (see ADR / model docstrings).
    """

    __tablename__ = "breed"
    __table_args__ = (
        CheckConstraint(SPECIES_CHECK_SQL, name="ck_breed_species"),
        CheckConstraint(BREED_COAT_TYPE_CHECK_SQL, name="ck_breed_default_coat_type"),
        CheckConstraint(BREED_SIZE_BAND_CHECK_SQL, name="ck_breed_typical_size_band"),
        CheckConstraint(BREED_SOURCE_CHECK_SQL, name="ck_breed_source"),
        # One breed per English name per species, whatever the capitalisation,
        # so "golden retriever" can't become a second Golden Retriever.
        Index(
            "uq_breed_species_name_en",
            "species",
            func.lower(text("name_en")),
            unique=True,
        ),
    )

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
    # catalog = shipped with the app (has priors); salon = added in the shop,
    # no typical minutes until someone sets them.
    source: Mapped[str] = mapped_column(String, nullable=False, server_default="catalog")
