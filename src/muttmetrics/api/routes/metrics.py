"""GET /metrics/week and /metrics/period (#156 / #170).

Thin HTTP layer: parse and validate the query, call ``api.services.metrics``,
return the response model. The SQL lives in the service, the formulas in
Postgres (ADR-003).
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from muttmetrics.api.deps import get_db, require_api_key
from muttmetrics.api.schemas.metrics import MetricsPeriodOut, MetricsWeekOut
from muttmetrics.api.services.metrics import (
    DEFAULT_BUFFER_MINUTES,
    load_period_metrics,
    load_week_metrics,
    monday_on_or_before,
    previous_range,
)

router = APIRouter(tags=["metrics"])

DbSession = Annotated[Session, Depends(get_db)]


def resolve_week_start(start: date | None) -> date:
    """Default = current week Monday; explicit start must already be a Monday."""
    if start is None:
        return monday_on_or_before(date.today())
    if start.weekday() != 0:
        raise HTTPException(
            status_code=422,
            detail="start must be a Monday (YYYY-MM-DD)",
        )
    return start


@router.get("/metrics/week", dependencies=[Depends(require_api_key)])
def get_metrics_week(
    session: DbSession,
    start: Annotated[
        date | None,
        Query(description="Monday of the week; default = current week"),
    ] = None,
    buffer_minutes: Annotated[
        int,
        Query(ge=1, description="Closing buffer for utilization"),
    ] = DEFAULT_BUFFER_MINUTES,
) -> MetricsWeekOut:
    """Current week + previous_week (same shape) for vs-last-week UI."""
    week_start = resolve_week_start(start)
    current = load_week_metrics(session, week_start, buffer_minutes)
    previous = load_week_metrics(session, week_start - timedelta(days=7), buffer_minutes)
    return MetricsWeekOut(**current.model_dump(), previous_week=previous)


@router.get("/metrics/period", dependencies=[Depends(require_api_key)])
def get_metrics_period(
    session: DbSession,
    start: Annotated[date, Query(description="Inclusive range start (YYYY-MM-DD)")],
    end: Annotated[date, Query(description="Inclusive range end (YYYY-MM-DD)")],
    buffer_minutes: Annotated[
        int,
        Query(ge=1, description="Closing buffer for utilization"),
    ] = DEFAULT_BUFFER_MINUTES,
) -> MetricsPeriodOut:
    """Arbitrary inclusive range + previous_period (#170).

    Prefer this over inventing a month-only twin: week is ``start`` Monday and
    ``end`` = Monday+6; a calendar month is the 1st through the last day.
    Previous for a calendar month is the prior calendar month; otherwise the
    equal-length window ending the day before ``start``.
    """
    try:
        current = load_period_metrics(session, start, end, buffer_minutes)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    prev_start, prev_end = previous_range(start, end, current.period)
    previous = load_period_metrics(session, prev_start, prev_end, buffer_minutes)
    return MetricsPeriodOut(**current.model_dump(), previous_period=previous)
