"""Add-on / technique catalog schemas (#192)."""

from pydantic import BaseModel, ConfigDict


class AddOnListItem(BaseModel):
    """One row from the add-on catalog for the capture SPA picker."""

    model_config = ConfigDict(from_attributes=True)

    add_on_id: int
    slug: str
    name_en: str | None = None
    name_de: str | None = None
    pricing: str
    # price_base may be NULL without private pricing.json
    price_base: float | None = None


class AddOnSummary(BaseModel):
    """Add-on nested on a visit response / dog recent visit."""

    model_config = ConfigDict(from_attributes=True)

    add_on_id: int
    slug: str
    name_en: str | None = None
    name_de: str | None = None
    pricing: str
