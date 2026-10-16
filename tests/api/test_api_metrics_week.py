"""GET /metrics/week — reads views; matches Syn* EXPECTED (#156)."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from tests.fixtures.metric_week import (
    BUFFER_MINUTES,
    EMPTY_WEEK_START,
    EXPECTED,
    MIN_N,
    WEEK_START,
)


def test_metrics_week_requires_api_key(client: TestClient) -> None:
    assert client.get("/metrics/week", params={"start": str(WEEK_START)}).status_code == 401


def test_metrics_week_rejects_non_monday(client: TestClient, auth_headers: dict[str, str]) -> None:
    tuesday = WEEK_START + timedelta(days=1)
    r = client.get(
        "/metrics/week",
        params={"start": str(tuesday)},
        headers=auth_headers,
    )
    assert r.status_code == 422
    assert "Monday" in r.json()["detail"]


def test_metrics_week_full_fixture(
    client: TestClient, auth_headers: dict[str, str], metric_week: dict
) -> None:
    r = client.get(
        "/metrics/week",
        params={"start": str(WEEK_START), "buffer_minutes": BUFFER_MINUTES},
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()

    assert data["week_start"] == str(WEEK_START)
    assert data["week_end"] == str(WEEK_START + timedelta(days=6))
    assert data["buffer_minutes"] == BUFFER_MINUTES

    assert data["min_n"] == MIN_N

    exp_sum = EXPECTED["week_summary"][WEEK_START]
    assert data["summary"]["visit_count"] == exp_sum["visit_count"]
    assert data["summary"]["groomed_minutes"] == exp_sum["groomed_minutes"]
    assert data["summary"]["revenue_ex_tip"] == pytest.approx(exp_sum["revenue_ex_tip"])
    assert data["summary"]["revenue_inc_tip"] == pytest.approx(exp_sum["revenue_inc_tip"])
    assert data["summary"]["eur_per_hour_n"] == exp_sum["eur_per_hour_n"]
    assert data["summary"]["eur_per_hour_ex_tip"]["reason"] is None
    assert data["summary"]["eur_per_hour_ex_tip"]["value"] == pytest.approx(
        exp_sum["eur_per_hour_ex_tip"]
    )
    assert data["summary"]["eur_per_hour_inc_tip"]["value"] == pytest.approx(
        exp_sum["eur_per_hour_inc_tip"]
    )

    by_cell = {(c["condition_score"], c["shaved_down"]): c for c in data["eur_per_hour"]}
    show = by_cell[(0, True)]
    exp_show = EXPECTED["eur_per_hour"][(0, True)]
    assert show["n"] == 5
    assert show["eur_per_hour_ex_tip"]["reason"] is None
    assert show["eur_per_hour_ex_tip"]["value"] == pytest.approx(exp_show["eur_per_hour_ex_tip"])
    assert show["eur_per_hour_inc_tip"]["value"] == pytest.approx(exp_show["eur_per_hour_inc_tip"])

    hide = by_cell[(4, True)]
    assert hide["n"] == 1
    assert hide["eur_per_hour_ex_tip"]["value"] is None
    assert hide["eur_per_hour_ex_tip"]["reason"] == "not_enough_data"

    assert data["pivot"]["n"] == EXPECTED["pivot"]["n"]
    assert data["pivot"]["pivoted_count"] == EXPECTED["pivot"]["pivoted_count"]
    assert data["pivot"]["rate"]["value"] == pytest.approx(EXPECTED["pivot"]["rate"])

    assert data["overrun"]["n"] == EXPECTED["overrun"]["n"]
    assert data["overrun"]["avg_minutes"]["value"] == pytest.approx(
        EXPECTED["overrun"]["avg_minutes"]
    )

    assert data["p90_miss"]["n"] == EXPECTED["p90_miss"]["n"]
    assert data["p90_miss"]["miss_count"] == EXPECTED["p90_miss"]["miss_count"]
    assert data["p90_miss"]["rate"]["value"] == pytest.approx(EXPECTED["p90_miss"]["rate"])

    util = {date.fromisoformat(u["visit_date"]): u for u in data["utilization"]}
    tue = util[date(2026, 3, 3)]
    assert tue["over_buffer"] is True
    assert tue["planned_p90"] == 350
    fri = util[date(2026, 3, 6)]
    assert fri["missing_prediction"] == 1

    # Week before Syn* has no rows
    prev = data["previous_week"]
    assert prev is not None
    assert prev["week_start"] == str(WEEK_START - timedelta(days=7))
    assert prev["summary"]["visit_count"] == 0


def test_metrics_week_empty_week_returns_200(
    client: TestClient, auth_headers: dict[str, str], metric_week: dict
) -> None:
    """Empty week → 200 with zero summary, not 404 (#156)."""
    r = client.get(
        "/metrics/week",
        params={"start": str(EMPTY_WEEK_START), "buffer_minutes": BUFFER_MINUTES},
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["min_n"] == MIN_N
    assert data["summary"]["visit_count"] == 0
    assert data["summary"]["groomed_minutes"] == 0
    assert data["summary"]["eur_per_hour_n"] == 0
    assert data["summary"]["eur_per_hour_inc_tip"]["value"] is None
    assert data["summary"]["eur_per_hour_inc_tip"]["reason"] == "not_enough_data"
    assert data["eur_per_hour"] == []
    assert data["pivot"]["n"] == 0
    assert data["pivot"]["rate"]["value"] is None
    assert data["pivot"]["rate"]["reason"] == "not_enough_data"
    assert data["utilization"] == []

    # Asking for the empty week → previous_week is the Syn* fixture week
    prev = data["previous_week"]
    assert prev is not None
    assert prev["week_start"] == str(WEEK_START)
    assert prev["summary"]["visit_count"] == EXPECTED["week_summary"][WEEK_START]["visit_count"]
