"""Sanity checks for the synthetic metric-week fixture itself (#16).

These assert that EXPECTED matches arithmetic from VISITS and that the loader
writes those rows. They say nothing about the SQL functions; the other files
in tests/db/ check those against EXPECTED.
"""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from tests.fixtures.metric_week import (
    BUFFER_MINUTES,
    EXPECTED,
    MIN_N,
    VISITS,
    WEEK_END,
    WEEK_START,
)

from muttmetrics.models import Breed, Dog, Owner, Visit


def _in_week(v: dict) -> bool:
    return WEEK_START <= v["visit_date"] <= WEEK_END


def _eligible(v: dict) -> bool:
    return v["status"] is None or v["status"] == "completed"


def test_fixture_covers_required_cases() -> None:
    statuses = {v["status"] for v in VISITS}
    assert "cancelled" in statuses
    assert "no_show" in statuses
    assert "completed" in statuses

    assert any(v["pivoted"] is True for v in VISITS)
    assert any(v["tip"] is None for v in VISITS)
    assert any(v["final_price"] is None for v in VISITS)
    assert any(v["predicted_min_p50"] is None and _eligible(v) for v in VISITS)
    assert any(v["condition_score"] == 0 and v["shaved_down"] is True for v in VISITS)
    assert any(v["condition_score"] == 5 for v in VISITS)

    tue = EXPECTED["utilization"][date(2026, 3, 3)]
    assert tue["over_buffer"] is True
    assert tue["planned_p90"] > BUFFER_MINUTES


def test_eur_per_hour_0_shaved_hand_math() -> None:
    cell = [
        v
        for v in VISITS
        if _in_week(v)
        and _eligible(v)
        and v["condition_score"] == 0
        and v["shaved_down"] is True
        and v["final_price"] is not None
        and v["actual_minutes"] > 0
    ]
    assert len(cell) == 5

    minutes = sum(v["actual_minutes"] for v in cell)
    rev_ex = sum(float(v["final_price"]) for v in cell)
    rev_inc = sum(
        float(v["final_price"]) + (0.0 if v["tip"] is None else float(v["tip"])) for v in cell
    )
    hours = minutes / 60.0

    expected = EXPECTED["eur_per_hour"][(0, True)]
    assert expected["n"] == 5
    assert expected["show_rate"] is True
    assert expected["hours"] == pytest.approx(hours)
    assert expected["revenue_ex_tip"] == pytest.approx(rev_ex)
    assert expected["revenue_inc_tip"] == pytest.approx(rev_inc)
    assert expected["eur_per_hour_ex_tip"] == pytest.approx(rev_ex / hours)
    assert expected["eur_per_hour_inc_tip"] == pytest.approx(rev_inc / hours)


def test_below_min_n_cells_hide_rate() -> None:
    for key, cell in EXPECTED["eur_per_hour"].items():
        if cell["n"] < MIN_N:
            assert cell["show_rate"] is False, key
            assert cell["eur_per_hour_ex_tip"] is None, key
        else:
            assert cell["show_rate"] is True, key
            assert cell["eur_per_hour_ex_tip"] is not None, key


def test_pivot_overrun_p90_hand_math() -> None:
    eligible = [v for v in VISITS if _in_week(v) and _eligible(v)]
    assert EXPECTED["pivot"]["n"] == len(eligible)
    assert EXPECTED["pivot"]["pivoted_count"] == sum(1 for v in eligible if v["pivoted"] is True)
    assert EXPECTED["pivot"]["rate"] == pytest.approx(1 / 11)

    overrun = [
        v
        for v in eligible
        if v["predicted_min_p50"] is not None and v["actual_minutes"] is not None
    ]
    deltas = [v["actual_minutes"] - v["predicted_min_p50"] for v in overrun]
    assert EXPECTED["overrun"]["n"] == 10
    assert EXPECTED["overrun"]["avg_minutes"] == pytest.approx(sum(deltas) / len(deltas))

    p90 = [
        v
        for v in eligible
        if v["predicted_min_p90"] is not None and v["actual_minutes"] is not None
    ]
    misses = sum(1 for v in p90 if v["actual_minutes"] > v["predicted_min_p90"])
    assert EXPECTED["p90_miss"]["n"] == 10
    assert EXPECTED["p90_miss"]["miss_count"] == misses
    assert EXPECTED["p90_miss"]["rate"] == pytest.approx(misses / len(p90))


def test_week_summary_hand_math() -> None:
    """#155 answer key: totals from VISITS (no DB, no view yet)."""
    eligible = [v for v in VISITS if _in_week(v) and _eligible(v)]
    priced = [v for v in eligible if v["final_price"] is not None]

    minutes = sum(v["actual_minutes"] for v in eligible)
    rev_ex = sum(float(v["final_price"]) for v in priced)
    rev_inc = sum(
        float(v["final_price"]) + (0.0 if v["tip"] is None else float(v["tip"])) for v in priced
    )

    expected = EXPECTED["week_summary"][date(2026, 3, 2)]
    assert expected["visit_count"] == 11 == len(eligible)
    assert expected["groomed_minutes"] == 840 == minutes
    assert expected["revenue_ex_tip"] == pytest.approx(rev_ex)
    assert expected["revenue_inc_tip"] == pytest.approx(rev_inc)
    assert expected["revenue_inc_tip"] == pytest.approx(633.0)


def test_utilization_tue_over_buffer() -> None:
    tue_visits = [v for v in VISITS if v["visit_date"] == date(2026, 3, 3) and _eligible(v)]
    assert len(tue_visits) == 3
    p90 = sum(v["predicted_min_p90"] or 0 for v in tue_visits)
    assert p90 == 350
    assert p90 > BUFFER_MINUTES
    assert EXPECTED["utilization"][date(2026, 3, 3)]["over_buffer"] is True


def test_metric_week_loads_all_visits(db_session: Session, metric_week: dict) -> None:
    """Load onto the pad; count only Syn* rows (real DB may already have visits)."""
    syn_owners = db_session.scalars(select(Owner).where(Owner.name.like("Syn Owner%"))).all()
    assert len(syn_owners) == 2
    assert len(metric_week["dog_ids"]) == 3

    syn_dog_ids = list(metric_week["dog_ids"].values())
    syn_visit_count = db_session.scalar(
        select(func.count()).select_from(Visit).where(Visit.dog_id.in_(syn_dog_ids))
    )
    assert syn_visit_count == len(VISITS) == 13


def test_metric_week_avg_duration_by_breed(db_session: Session, metric_week: dict) -> None:
    """#16 acceptance: enough Syn* rows to query average duration by breed."""
    rows = db_session.execute(
        select(
            Breed.name_en,
            func.avg(Visit.actual_minutes),
            func.count(),
        )
        .join(Dog, Visit.dog_id == Dog.dog_id)
        .join(Breed, Dog.breed_id == Breed.breed_id)
        .where(Breed.name_en.like("Syn Breed%"))
        .group_by(Breed.name_en)
        .order_by(Breed.name_en)
    ).all()

    assert len(rows) >= 2
    by_breed = {name: (float(avg), n) for name, avg, n in rows}
    assert "Syn Breed Matted" in by_breed
    assert by_breed["Syn Breed Matted"][1] >= 5  # most of the 0×shaved week
    assert by_breed["Syn Breed Fluff"][1] >= 1
    assert by_breed["Syn Breed Mix"][1] >= 1
