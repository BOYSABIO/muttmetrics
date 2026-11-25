"""metric_rent() and the rent blocks on /metrics/period (#229), hand-computed.

Made-up amounts. Rent 1000 from October, 1200 from November; nothing before.

    Sep 20  50            (before any rent)
    Oct  3  300 + 20 tip  → 320 so far
    Oct 10  400           → 720
    Oct 12  500 cancelled (not counted)
    Oct 15  no price      (not counted)
    Oct 18  300 + 10 tip  → 1030  ← rent (1000) covered
    Oct 25  200           → 1230
    Nov  2  100           → 100 of 1200, not covered
"""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from muttmetrics.api.services.metrics import load_all_time, load_rent_month, rent_month_for
from muttmetrics.models import FixedCost, Owner, Pet, Visit

VISITS = [
    # (date, price, tip, status)
    (date(2026, 9, 20), 50, None, "completed"),
    (date(2026, 10, 3), 300, 20, "completed"),
    (date(2026, 10, 10), 400, None, "completed"),
    (date(2026, 10, 12), 500, None, "cancelled"),
    (date(2026, 10, 15), None, None, "completed"),
    (date(2026, 10, 18), 300, 10, None),
    (date(2026, 10, 25), 200, None, "completed"),
    (date(2026, 11, 2), 100, None, "completed"),
]


@pytest.fixture
def rent_visits(db_session: Session) -> None:
    owner = Owner(name="Syn Rent Owner")
    db_session.add(owner)
    db_session.flush()
    pet = Pet(owner_id=owner.owner_id, name="SynDog Rent", species="dog")
    db_session.add(pet)
    db_session.flush()
    for d, price, tip, status in VISITS:
        db_session.add(
            Visit(
                owner_id=owner.owner_id,
                pet_id=pet.pet_id,
                visit_date=d,
                actual_minutes=60,
                final_price=price,
                tip=tip,
                status=status,
            )
        )
    db_session.flush()


@pytest.fixture
def rent_rows(db_session: Session) -> None:
    db_session.add(FixedCost(kind="rent", monthly_amount=1000, valid_from=date(2026, 10, 1)))
    db_session.add(FixedCost(kind="rent", monthly_amount=1200, valid_from=date(2026, 11, 1)))
    db_session.flush()


def _rows(session: Session, start: date, end: date) -> list[dict]:
    return [
        dict(r)
        for r in session.execute(
            text("SELECT * FROM metric_rent(:s, :e)"), {"s": start, "e": end}
        ).mappings()
    ]


def test_months_against_rent(db_session: Session, rent_visits: None, rent_rows: None) -> None:
    rows = _rows(db_session, date(2026, 9, 5), date(2026, 11, 20))
    assert [r["month_start"] for r in rows] == [
        date(2026, 9, 1),
        date(2026, 10, 1),
        date(2026, 11, 1),
    ]
    sep, oct_, nov = rows

    assert sep["rent"] is None
    assert float(sep["take_home"]) == 50
    assert sep["covered_on"] is None

    assert float(oct_["rent"]) == 1000
    assert float(oct_["take_home"]) == 1230  # cancelled and unpriced visits left out
    assert oct_["covered_on"] == date(2026, 10, 18)

    assert float(nov["rent"]) == 1200  # the later row wins from its month on
    assert float(nov["take_home"]) == 100
    assert nov["covered_on"] is None


def test_whole_month_even_for_a_mid_month_range(
    db_session: Session, rent_visits: None, rent_rows: None
) -> None:
    (row,) = _rows(db_session, date(2026, 10, 20), date(2026, 10, 21))
    assert float(row["take_home"]) == 1230
    assert row["covered_on"] == date(2026, 10, 18)


def test_no_rent_set_means_no_bar(db_session: Session, rent_visits: None) -> None:
    assert load_rent_month(db_session, date(2026, 10, 1)) is None
    all_time = load_all_time(db_session, date(2026, 11, 20))
    assert all_time is not None
    assert all_time.rent_since is None
    assert all_time.rent_paid is None
    assert all_time.after_rent is None


def test_load_rent_month(db_session: Session, rent_visits: None, rent_rows: None) -> None:
    oct_ = load_rent_month(db_session, date(2026, 10, 1))
    assert oct_ is not None
    assert (oct_.rent, oct_.take_home, oct_.covered_on) == (1000, 1230, date(2026, 10, 18))
    assert load_rent_month(db_session, date(2026, 9, 1)) is None  # before any rent


def test_all_time_after_rent(db_session: Session, rent_visits: None, rent_rows: None) -> None:
    all_time = load_all_time(db_session, date(2026, 11, 20))
    assert all_time is not None
    assert all_time.rent_since == date(2026, 10, 1)
    assert all_time.rent_paid == 2200  # November counts in full: due on the 1st
    assert all_time.summary.revenue_inc_tip == pytest.approx(1380)
    assert all_time.after_rent == pytest.approx(1380 - 2200)


@pytest.mark.parametrize(
    ("start", "end", "today", "month"),
    [
        # A week that is running: today's month.
        (date(2026, 11, 23), date(2026, 11, 29), date(2026, 11, 25), date(2026, 11, 1)),
        # A past week across two months: the month it ended in.
        (date(2026, 10, 26), date(2026, 11, 1), date(2026, 11, 25), date(2026, 11, 1)),
        # A past month: that month.
        (date(2026, 10, 1), date(2026, 10, 31), date(2026, 11, 25), date(2026, 10, 1)),
        # A week still ahead: the month it starts in.
        (date(2026, 12, 28), date(2027, 1, 3), date(2026, 11, 25), date(2026, 12, 1)),
    ],
)
def test_rent_month_for(start: date, end: date, today: date, month: date) -> None:
    assert rent_month_for(start, end, today) == month


def test_period_endpoint_has_rent(
    client, auth_headers: dict[str, str], rent_visits: None, rent_rows: None
) -> None:
    r = client.get(
        "/metrics/period",
        params={"start": "2026-10-01", "end": "2026-10-31"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    rent = r.json()["rent"]
    assert rent == {
        "month_start": "2026-10-01",
        "rent": 1000.0,
        "take_home": 1230.0,
        "covered_on": "2026-10-18",
    }
    assert r.json()["all_time"]["rent_since"] == "2026-10-01"


def test_period_endpoint_without_rent(
    client, auth_headers: dict[str, str], rent_visits: None
) -> None:
    r = client.get(
        "/metrics/period",
        params={"start": "2026-10-01", "end": "2026-10-31"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["rent"] is None
    assert r.json()["all_time"]["after_rent"] is None
