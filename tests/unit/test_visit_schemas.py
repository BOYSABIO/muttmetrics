"""CreateVisitRequest validation (no HTTP, no Postgres)."""

from datetime import date

import pytest
from pydantic import ValidationError

from muttmetrics.api.schemas import CreateVisitRequest


def test_minimal_valid_payload() -> None:
    """A minimal valid payload."""
    body = CreateVisitRequest.model_validate(
        {
            "dog_id": 1,
            "owner_id": 1,
            "visit_date": "2026-09-07",
            "actual_minutes": 60,
        }
    )
    assert body.dog_id == 1
    assert body.visit_date == date(2026, 9, 7)
    assert body.actual_minutes == 60
    assert body.condition_score is None


def test_actual_minutes_must_be_positive() -> None:
    """Actual minutes must be positive."""
    with pytest.raises(ValidationError):
        CreateVisitRequest.model_validate(
            {
                "dog_id": 1,
                "owner_id": 1,
                "visit_date": "2026-09-07",
                "actual_minutes": 0,
            }
        )


def test_condition_score_out_of_range() -> None:
    """Condition score must be between 0 and 5."""
    with pytest.raises(ValidationError):
        CreateVisitRequest.model_validate(
            {
                "dog_id": 1,
                "owner_id": 1,
                "visit_date": "2026-09-07",
                "actual_minutes": 45,
                "condition_score": 9,
            }
        )


def test_missing_required_fields() -> None:
    """Missing required fields should raise a validation error."""
    with pytest.raises(ValidationError):
        CreateVisitRequest.model_validate(
            {
                "dog_id": 1,
                "owner_id": 1,
                "visit_date": "2026-09-07",
                # actual_minutes missing
            }
        )
