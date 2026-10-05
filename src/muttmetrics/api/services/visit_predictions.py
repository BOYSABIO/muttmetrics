"""Compute days_since_last + rules prior at visit create (#24)"""

from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from muttmetrics.models import Breed, Dog, Visit
from muttmetrics.prior import rules_prior

LOGGER = logging.getLogger(__name__)


def compute_visit_predictions(
    session: Session,
    *,
    dog: Dog,
    visit_date: date,
) -> tuple[int | None, int | None, int | None]:
    """Return (days_since_last, predicted_min_p50, predicted_min_p90).

    Predictions stay None when base_groom_minutes is missing - never raises.
    """
    days_since_last = _days_since_last(session, dog_id=dog.dog_id, visit_date=visit_date)

    breed: Breed | None = None
    if dog.breed_id is not None:
        breed = session.get(Breed, dog.breed_id)

    base = breed.base_groom_minutes if breed is not None else None
    if base is None or base <= 0:
        LOGGER.warning(
            "visit prior skipped: dog_id=%s, breed_id=%s (no base_groom_minutes)",
            dog.dog_id,
            dog.breed_id,
        )
        return days_since_last, None, None

    matting = breed.matting_risk if breed.matting_risk is not None else 1
    p50, p90 = rules_prior(
        base_groom_minutes=base,
        matting_risk=matting,
        size_band=dog.size_band,
        days_since_last=days_since_last,
        recommended_interval_days=breed.recommended_interval_days,
        handling_score=dog.handling_score,
    )
    return days_since_last, p50, p90


def _days_since_last(
    session: Session,
    *,
    dog_id: int,
    visit_date: date,
) -> int | None:
    prev = session.scalar(
        select(Visit.visit_date)
        .where(
            Visit.dog_id == dog_id,
            Visit.visit_date < visit_date,
            or_(Visit.status.is_(None), Visit.status == "completed"),
        )
        .order_by(Visit.visit_date.desc())
        .limit(1)
    )
    if prev is None:
        return None
    return (visit_date - prev).days
