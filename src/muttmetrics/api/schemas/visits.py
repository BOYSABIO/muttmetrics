"""Visit create/response schemas — thin post-groom capture contract."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from muttmetrics.api.schemas.add_ons import AddOnSummary


class CreateVisitRequest(BaseModel):
    """Body for POST /visits — only what an exhausted groomer should type."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "dog_id": 1,
                    "owner_id": 1,
                    "visit_date": "2026-09-07",
                    "actual_minutes": 90,
                    "condition_score": 3,
                    "booked_service_id": 4,
                    "actual_service_id": 4,
                    "add_on_ids": [1],
                    "what_surprised_me": "calmer than last time",
                    "status": "completed",
                }
            ]
        }
    )

    dog_id: int = Field(..., description="Existing dog primary key")
    owner_id: int = Field(..., description="Existing owner primary key")
    visit_date: date
    actual_minutes: int = Field(..., gt=0, description="Wall-clock minutes for the groom")

    condition_score: int | None = Field(default=None, ge=0, le=5)
    booked_service_id: int | None = None
    actual_service_id: int | None = None
    add_on_ids: list[int] = Field(
        default_factory=list,
        description="Technique / add-on catalog ids (#192); unknown → 404",
    )
    what_surprised_me: str | None = None
    quoted_price: float | None = Field(default=None, ge=0)
    final_price: float | None = Field(default=None, ge=0)
    tip: float | None = Field(default=None, ge=0)
    shaved_down: bool | None = None
    status: Literal["completed", "cancelled", "no_show"] | None = None


class VisitResponse(BaseModel):
    """Subset returned after a successful create."""

    model_config = ConfigDict(from_attributes=True)

    visit_id: int
    dog_id: int
    owner_id: int
    visit_date: date
    actual_minutes: int
    condition_score: int | None = None
    booked_service_id: int | None = None
    actual_service_id: int | None = None
    add_ons: list[AddOnSummary] = Field(default_factory=list)
    what_surprised_me: str | None = None
    quoted_price: float | None = Field(default=None, ge=0)
    final_price: float | None = Field(default=None, ge=0)
    tip: float | None = Field(default=None, ge=0)
    shaved_down: bool | None = None
    status: Literal["completed", "cancelled", "no_show"] | None = None
    days_since_last: int | None = None
    predicted_min_p50: int | None = None
    predicted_min_p90: int | None = None


class PatchVisitRequest(BaseModel):
    """Partial update - event facts only (ADR-001)

    System-computed columns (days_since_last, predicted_min_*) are omitted
    on purpose; extra=\"forbid\" rejects them if a client sends them.

    `add_on_ids`: omit → leave join rows; send (including []) → replace the set.
    """

    model_config = ConfigDict(extra="forbid")

    visit_date: date | None = None
    actual_minutes: int | None = Field(default=None, gt=0)

    condition_score: int | None = Field(default=None, ge=0, le=5)
    booked_service_id: int | None = None
    actual_service_id: int | None = None
    add_on_ids: list[int] | None = None
    what_surprised_me: str | None = None
    quoted_price: float | None = Field(default=None, ge=0)
    final_price: float | None = Field(default=None, ge=0)
    tip: float | None = Field(default=None, ge=0)
    shaved_down: bool | None = None
    status: Literal["completed", "cancelled", "no_show"] | None = None
