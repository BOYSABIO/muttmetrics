"""Breed catalog schemas — list breeds for Directory pickers."""

from pydantic import BaseModel, ConfigDict


class BreedListItem(BaseModel):
    """One row from the breed catalog for a picker."""

    model_config = ConfigDict(from_attributes=True)

    breed_id: int
    name_de: str | None = None
    name_en: str | None = None
