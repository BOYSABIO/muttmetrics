"""GET /metrics/week and /metrics/period — range metric functions (#156 / #170)."""

from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from muttmetrics.api.deps import get_db, require_api_key
from muttmetrics.api.schemas.metrics import (
    EurPerHourCellOut,
    MetricsPeriodBlock,
    MetricsPeriodOut,
    MetricsWeekOut,
    MetricValue,
    OverrunOut,
    P90MissOut,
    PeriodKind,
    PivotOut,
    UtilizationDayOut,
    WeekSummaryOut,
)

router = APIRouter(tags=["metrics"])

DbSession = Annotated[Session, Depends(get_db)]

DEFAULT_BUFFER_MINUTES = 240
NOT_ENOUGH = "not_enough_data"
MAX_RANGE_DAYS = 366


def _monday_on_or_before(d: date) -> date:
    """Return the Monday on or before d."""
    return d - timedelta(days=d.weekday())


def resolve_week_start(start: date | None) -> date:
    """Default = current week Monday; explicit start must already be a Monday."""
    if start is None:
        return _monday_on_or_before(date.today())
    if start.weekday() != 0:
        raise HTTPException(
            status_code=422,
            detail="start must be a Monday (YYYY-MM-DD)",
        )
    return start


def _is_calendar_month(start: date, end: date) -> bool:
    """True when start..end is exactly one calendar month."""
    if start.day != 1 or start.year != end.year or start.month != end.month:
        return False
    return end.day == monthrange(start.year, start.month)[1]


def classify_period(start: date, end: date) -> PeriodKind:
    """Label a range as week / month / custom for the UI."""
    if (end - start).days == 6 and start.weekday() == 0:
        return "week"
    if _is_calendar_month(start, end):
        return "month"
    return "custom"


def _metric_value(raw: Any) -> MetricValue:
    """Package a SQL rate/average: NULL → not_enough_data."""
    if raw is None:
        return MetricValue(value=None, reason=NOT_ENOUGH)
    return MetricValue(value=float(raw), reason=None)


def _empty_summary() -> WeekSummaryOut:
    return WeekSummaryOut(
        visit_count=0,
        groomed_minutes=0,
        revenue_ex_tip=0.0,
        revenue_inc_tip=0.0,
        eur_per_hour_n=0,
        eur_per_hour_ex_tip=MetricValue(value=None, reason=NOT_ENOUGH),
        eur_per_hour_inc_tip=MetricValue(value=None, reason=NOT_ENOUGH),
    )


def _load_min_n(session: Session) -> int:
    """Product MIN_N from metric_constants (SQL), not a Python literal."""
    row = session.execute(text("SELECT min_n FROM metric_constants")).mappings().first()
    if row is None:
        raise RuntimeError("metric_constants is empty — run migrations")
    return int(row["min_n"])


def load_period_metrics(
    session: Session,
    period_start: date,
    period_end: date,
    buffer_minutes: int,
    *,
    period: PeriodKind | None = None,
) -> MetricsPeriodBlock:
    """SELECT from ADR-003 range functions for an inclusive date range; package only."""
    if period_end < period_start:
        raise HTTPException(status_code=422, detail="end must be on or after start")
    if (period_end - period_start).days > MAX_RANGE_DAYS:
        raise HTTPException(
            status_code=422,
            detail=f"range must be at most {MAX_RANGE_DAYS} days",
        )

    kind = period if period is not None else classify_period(period_start, period_end)
    params = {
        "p_start": period_start,
        "p_end": period_end,
        "buffer": buffer_minutes,
    }
    min_n = _load_min_n(session)

    summary_row = (
        session.execute(
            text(
                """
                SELECT visit_count, groomed_minutes, revenue_ex_tip, revenue_inc_tip,
                       eur_per_hour_n, eur_per_hour_ex_tip, eur_per_hour_inc_tip
                FROM metric_summary(:p_start, :p_end)
                """
            ),
            params,
        )
        .mappings()
        .first()
    )
    if summary_row is None:
        summary = _empty_summary()
    else:
        summary = WeekSummaryOut(
            visit_count=int(summary_row["visit_count"]),
            groomed_minutes=int(summary_row["groomed_minutes"]),
            revenue_ex_tip=float(summary_row["revenue_ex_tip"]),
            revenue_inc_tip=float(summary_row["revenue_inc_tip"]),
            eur_per_hour_n=int(summary_row["eur_per_hour_n"]),
            eur_per_hour_ex_tip=_metric_value(summary_row["eur_per_hour_ex_tip"]),
            eur_per_hour_inc_tip=_metric_value(summary_row["eur_per_hour_inc_tip"]),
        )

    eur_rows = (
        session.execute(
            text(
                """
                SELECT condition_score, shaved_down, n, groomed_minutes, hours,
                       revenue_ex_tip, revenue_inc_tip,
                       eur_per_hour_ex_tip, eur_per_hour_inc_tip
                FROM metric_eur_per_hour(:p_start, :p_end)
                """
            ),
            params,
        )
        .mappings()
        .all()
    )
    eur_per_hour = [
        EurPerHourCellOut(
            condition_score=int(r["condition_score"]),
            shaved_down=bool(r["shaved_down"]),
            n=int(r["n"]),
            groomed_minutes=int(r["groomed_minutes"]),
            hours=float(r["hours"]),
            revenue_ex_tip=float(r["revenue_ex_tip"]),
            revenue_inc_tip=float(r["revenue_inc_tip"]),
            eur_per_hour_ex_tip=_metric_value(r["eur_per_hour_ex_tip"]),
            eur_per_hour_inc_tip=_metric_value(r["eur_per_hour_inc_tip"]),
        )
        for r in eur_rows
    ]

    pivot_row = (
        session.execute(
            text(
                """
                SELECT n, pivoted_count, pivot_rate
                FROM metric_pivot_rate(:p_start, :p_end)
                """
            ),
            params,
        )
        .mappings()
        .first()
    )
    if pivot_row is None:
        pivot = PivotOut(
            n=0,
            pivoted_count=0,
            rate=MetricValue(value=None, reason=NOT_ENOUGH),
        )
    else:
        pivot = PivotOut(
            n=int(pivot_row["n"]),
            pivoted_count=int(pivot_row["pivoted_count"]),
            rate=_metric_value(pivot_row["pivot_rate"]),
        )

    overrun_row = (
        session.execute(
            text(
                """
                SELECT n, avg_overrun_minutes
                FROM metric_overrun(:p_start, :p_end)
                """
            ),
            params,
        )
        .mappings()
        .first()
    )
    if overrun_row is None:
        overrun = OverrunOut(
            n=0,
            avg_minutes=MetricValue(value=None, reason=NOT_ENOUGH),
        )
    else:
        overrun = OverrunOut(
            n=int(overrun_row["n"]),
            avg_minutes=_metric_value(overrun_row["avg_overrun_minutes"]),
        )

    p90_row = (
        session.execute(
            text(
                """
                SELECT n, miss_count, miss_rate
                FROM metric_p90_miss(:p_start, :p_end)
                """
            ),
            params,
        )
        .mappings()
        .first()
    )
    if p90_row is None:
        p90_miss = P90MissOut(
            n=0,
            miss_count=0,
            rate=MetricValue(value=None, reason=NOT_ENOUGH),
        )
    else:
        p90_miss = P90MissOut(
            n=int(p90_row["n"]),
            miss_count=int(p90_row["miss_count"]),
            rate=_metric_value(p90_row["miss_rate"]),
        )

    util_rows = (
        session.execute(
            text(
                """
                SELECT visit_date, n, planned_p50, planned_p90,
                       actual_minutes, missing_prediction, over_buffer
                FROM metric_utilization(:buffer, :p_start, :p_end)
                ORDER BY visit_date
                """
            ),
            params,
        )
        .mappings()
        .all()
    )
    utilization = [
        UtilizationDayOut(
            visit_date=r["visit_date"],
            n=int(r["n"]),
            planned_p50=int(r["planned_p50"]),
            planned_p90=int(r["planned_p90"]),
            actual_minutes=int(r["actual_minutes"]),
            missing_prediction=int(r["missing_prediction"]),
            over_buffer=bool(r["over_buffer"]),
        )
        for r in util_rows
    ]

    return MetricsPeriodBlock(
        period=kind,
        week_start=period_start,
        week_end=period_end,
        buffer_minutes=buffer_minutes,
        min_n=min_n,
        summary=summary,
        eur_per_hour=eur_per_hour,
        pivot=pivot,
        overrun=overrun,
        p90_miss=p90_miss,
        utilization=utilization,
    )


def load_week_metrics(
    session: Session, week_start: date, buffer_minutes: int
) -> MetricsPeriodBlock:
    """Mon–Sun week as a thin wrapper over range functions (#170)."""
    return load_period_metrics(
        session,
        week_start,
        week_start + timedelta(days=6),
        buffer_minutes,
        period="week",
    )


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
    current = load_period_metrics(session, start, end, buffer_minutes)
    if current.period == "month":
        if start.month == 1:
            prev_start = date(start.year - 1, 12, 1)
        else:
            prev_start = date(start.year, start.month - 1, 1)
        prev_end = start - timedelta(days=1)
    else:
        span_days = (end - start).days
        prev_end = start - timedelta(days=1)
        prev_start = prev_end - timedelta(days=span_days)
    previous = load_period_metrics(session, prev_start, prev_end, buffer_minutes)
    return MetricsPeriodOut(**current.model_dump(), previous_period=previous)
