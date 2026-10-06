"""Duration-range preview response (#26)."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class DurationRangeResponse(BaseModel):
    """P50/P90 for a dog as of a date - same rules as visit create."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "dog_id": 1,
                    "service_id": 4,
                    "as_of": "2026-10-06",
                    "days_since_last": 30,
                    "predicted_min_p50": 157,
                    "predicted_min_p90": 212,
                    "skipped_reason": None,
                }
            ]
        }
    )

    dog_id: int
    service_id: int | None = None
    as_of: date
    days_since_last: int | None = None
    predicted_min_p50: int | None = Field(default=None, description="Rules prior P50 minutes")
    predicted_min_p90: int | None = Field(default=None, description="Rules prior P90 minutes")
    skipped_reason: str | None = Field(
        default=None, description="Set when predictions are null (e.g. missing breed base minutes)"
    )
