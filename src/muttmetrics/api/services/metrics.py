"""Metric loading for the dashboard API (#156 / #170 / #178, moved out of the route in #180).

Every number comes from the ADR-003 range functions in Postgres
(``metric_*(p_start, p_end)``). This module only runs those SELECTs and
packages the rows into response models; it never computes a metric itself.
Invalid ranges raise ValueError, which the route turns into a 422.
"""

from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from muttmetrics.api.schemas.metrics import (
    AllTimeOut,
    EstimateBandsOut,
    EurPerHourCellOut,
    MetricsPeriodBlock,
    MetricValue,
    OverrunOut,
    P90MissOut,
    PeriodKind,
    PeriodSummaryOut,
    PivotOut,
    UtilizationDayOut,
    UtilizationWeekOut,
)

DEFAULT_BUFFER_MINUTES = 240
NOT_ENOUGH = "not_enough_data"
MAX_RANGE_DAYS = 366
# Window for the slow questions (€ / hour by coat, estimate accuracy): long
# enough to fill the rows, short enough that old prices drop out.
RECENT_DAYS = 90


def monday_on_or_before(d: date) -> date:
    """Return the Monday on or before d."""
    return d - timedelta(days=d.weekday())


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


def _empty_summary() -> PeriodSummaryOut:
    return PeriodSummaryOut(
        visit_count=0,
        groomed_minutes=0,
        revenue_ex_tip=0.0,
        revenue_inc_tip=0.0,
        eur_per_hour_n=0,
        eur_per_hour_ex_tip=MetricValue(value=None, reason=NOT_ENOUGH),
        eur_per_hour_inc_tip=MetricValue(value=None, reason=NOT_ENOUGH),
    )


def _summary_from_row(row: Any) -> PeriodSummaryOut:
    if row is None:
        return _empty_summary()
    return PeriodSummaryOut(
        visit_count=int(row["visit_count"]),
        groomed_minutes=int(row["groomed_minutes"]),
        revenue_ex_tip=float(row["revenue_ex_tip"]),
        revenue_inc_tip=float(row["revenue_inc_tip"]),
        eur_per_hour_n=int(row["eur_per_hour_n"]),
        eur_per_hour_ex_tip=_metric_value(row["eur_per_hour_ex_tip"]),
        eur_per_hour_inc_tip=_metric_value(row["eur_per_hour_inc_tip"]),
    )


def _load_summary(session: Session, start: date, end: date) -> PeriodSummaryOut:
    row = (
        session.execute(
            text(
                """
                SELECT visit_count, groomed_minutes, revenue_ex_tip, revenue_inc_tip,
                       eur_per_hour_n, eur_per_hour_ex_tip, eur_per_hour_inc_tip
                FROM metric_summary(:p_start, :p_end)
                """
            ),
            {"p_start": start, "p_end": end},
        )
        .mappings()
        .first()
    )
    return _summary_from_row(row)


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
        raise ValueError("end must be on or after start")
    # Inclusive range: Jan 1 -> Jan 1 is 1 day, so add 1 before comparing.
    if (period_end - period_start).days + 1 > MAX_RANGE_DAYS:
        raise ValueError(f"range must be at most {MAX_RANGE_DAYS} days")

    kind = period if period is not None else classify_period(period_start, period_end)
    params = {
        "p_start": period_start,
        "p_end": period_end,
        "buffer": buffer_minutes,
    }
    min_n = _load_min_n(session)

    summary = _load_summary(session, period_start, period_end)

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
            condition_score=(None if r["condition_score"] is None else int(r["condition_score"])),
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

    bands_row = (
        session.execute(
            text(
                """
                SELECT n, within_p50, within_p90, past_p90, enough
                FROM metric_estimate_bands(:p_start, :p_end)
                """
            ),
            params,
        )
        .mappings()
        .first()
    )
    estimate_bands = (
        EstimateBandsOut(n=0, within_p50=0, within_p90=0, past_p90=0, enough=False)
        if bands_row is None
        else EstimateBandsOut.model_validate(dict(bands_row))
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

    week_rows = (
        session.execute(
            text(
                """
                SELECT week_start, range_start, range_end, day_count, n,
                       planned_p50, planned_p90, actual_minutes,
                       missing_prediction, over_buffer_days
                FROM metric_utilization_weeks(:buffer, :p_start, :p_end)
                ORDER BY week_start
                """
            ),
            params,
        )
        .mappings()
        .all()
    )
    utilization_weeks = [UtilizationWeekOut.model_validate(dict(r)) for r in week_rows]

    return MetricsPeriodBlock(
        period=kind,
        start=period_start,
        end=period_end,
        buffer_minutes=buffer_minutes,
        min_n=min_n,
        summary=summary,
        eur_per_hour=eur_per_hour,
        pivot=pivot,
        overrun=overrun,
        p90_miss=p90_miss,
        estimate_bands=estimate_bands,
        utilization=utilization,
        utilization_weeks=utilization_weeks,
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


def previous_range(start: date, end: date, kind: PeriodKind) -> tuple[date, date]:
    """The range to compare against: the previous calendar month for a month,
    otherwise the equal-length window ending the day before ``start``."""
    if kind == "month":
        prev_start = (
            date(start.year - 1, 12, 1)
            if start.month == 1
            else date(start.year, start.month - 1, 1)
        )
        return prev_start, start - timedelta(days=1)
    span_days = (end - start).days
    prev_end = start - timedelta(days=1)
    return prev_end - timedelta(days=span_days), prev_end


def comparison_range(
    start: date, end: date, kind: PeriodKind, today: date
) -> tuple[date, date, bool]:
    """The previous range, clipped to the elapsed days while ``start..end`` is running.

    Returns ``(prev_start, prev_end, partial)``. On a Tuesday, this week
    (Mon–Tue so far) is compared with last Mon–Tue, not with all of last week.
    """
    prev_start, prev_end = previous_range(start, end, kind)
    if start <= today < end:
        elapsed = (today - start).days
        return prev_start, min(prev_start + timedelta(days=elapsed), prev_end), True
    return prev_start, prev_end, False


def recent_range(end: date, today: date) -> tuple[date, date]:
    """The ``RECENT_DAYS`` window ending at ``end``, or today if ``end`` is later."""
    recent_end = min(end, today)
    return recent_end - timedelta(days=RECENT_DAYS - 1), recent_end


def load_all_time(session: Session, today: date) -> AllTimeOut | None:
    """Totals since the first completed visit (glossary rules, via metric_summary)."""
    first = session.execute(
        text(
            """
            SELECT MIN(visit_date) FROM visit
            WHERE (status IS NULL OR status = 'completed') AND visit_date <= :today
            """
        ),
        {"today": today},
    ).scalar()
    if first is None:
        return None
    return AllTimeOut(
        first_visit_date=first,
        through=today,
        summary=_load_summary(session, first, today),
    )
