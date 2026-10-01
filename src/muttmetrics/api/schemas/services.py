"""Service catalog schemas - list packages for the capture SPA"""

from pydantic import BaseModel, ConfigDict


class ServiceListItem(BaseModel):
    """One row from the service catalog for a picker."""

    model_config = ConfigDict(from_attributes=True)

    service_id: int
    slug: str | None = None
    name_en: str | None = None
    name_de: str | None = None
    base_minutes: int | None = None
    # price_base may be NULL in CI / clones without private pricing.json
    price_base: float | None = None
