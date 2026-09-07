"""Visit create/response schemas — thin post-groom capture contract."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


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
    what_surprised_me: str | None = None
    intake_photos: list[str] | None = None
    after_photos: list[str] | None = None
    quoted_price: float | None = None
    final_price: float | None = None
    tip: float | None = None
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
    what_surprised_me: str | None = None
    status: Literal["completed", "cancelled", "no_show"] | None = None
