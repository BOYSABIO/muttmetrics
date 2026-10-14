"""metric_eur_per_hour view vs hand-computed EXPECTED."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session
from tests.fixtures.metric_week import EXPECTED, MIN_N, WEEK_START


def test_eur_per_hour_show_and_hide_cells(db_session: Session, metric_week: dict) -> None:
    rows = (
        db_session.execute(
            text(
                """
                SELECT condition_score, shaved_down, n,
                       revenue_ex_tip, revenue_inc_tip, hours,
                       eur_per_hour_ex_tip, eur_per_hour_inc_tip
                FROM metric_eur_per_hour
                WHERE week_start = :week_start
                """
            ),
            {"week_start": WEEK_START},
        )
        .mappings()
        .all()
    )

    by_cell = {(r["condition_score"], r["shaved_down"]): r for r in rows}

    # Cell with n >= MIN_N - rates must match hand math
    show = by_cell[(0, True)]
    expected_show = EXPECTED["eur_per_hour"][(0, True)]
    assert show["n"] == expected_show["n"] == 5
    assert float(show["revenue_ex_tip"]) == pytest.approx(expected_show["revenue_ex_tip"])
    assert float(show["revenue_inc_tip"]) == pytest.approx(expected_show["revenue_inc_tip"])
    assert float(show["hours"]) == pytest.approx(expected_show["hours"])
    assert float(show["eur_per_hour_ex_tip"]) == pytest.approx(expected_show["eur_per_hour_ex_tip"])
    assert float(show["eur_per_hour_inc_tip"]) == pytest.approx(
        expected_show["eur_per_hour_inc_tip"]
    )

    # Cell below MIN_N — totals ok, rates NULL
    hide = by_cell[(4, True)]
    expected_hide = EXPECTED["eur_per_hour"][(4, True)]
    assert hide["n"] == expected_hide["n"] == 1
    assert hide["n"] < MIN_N
    assert hide["eur_per_hour_ex_tip"] is None
    assert hide["eur_per_hour_inc_tip"] is None
