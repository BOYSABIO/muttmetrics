"""Breed catalog schemas — list breeds for pickers, add one in the salon."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class BreedListItem(BaseModel):
    """One row from the breed catalog for a picker. The app shows name_en;
    name_de stays searchable (typing "Schäferhund" finds German Shepherd)."""

    model_config = ConfigDict(from_attributes=True)

    breed_id: int
    species: str
    name_de: str | None = None
    name_en: str | None = None
    source: Literal["catalog", "salon"] = "catalog"


class CreateBreedRequest(BaseModel):
    """Add a breed the catalog doesn't have (breed.source = 'salon')."""

    model_config = ConfigDict(extra="forbid")

    species: Literal["dog", "cat"]
    name_en: str = Field(..., min_length=2, max_length=60, description="English name")
