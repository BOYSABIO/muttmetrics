"""ops/demo_recent.py: rolling synthetic weeks for the dev database."""

from __future__ import annotations

from datetime import date, timedelta

from ops.demo_recent import WEEKS, load_recent
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from muttmetrics.models import Owner, Pet, Visit

TODAY = date(2026, 11, 14)


def test_recent_demo_is_synthetic_recent_and_has_history(db_session: Session) -> None:
    added = load_recent(db_session, today=TODAY)
    assert added >= 50  # a salon-like ~6 a week over 12 weeks

    visits = list(db_session.scalars(select(Visit)))
    assert all(TODAY - timedelta(weeks=WEEKS) <= v.visit_date <= TODAY for v in visits)
    assert all(1 <= v.visit_date.weekday() <= 5 for v in visits)  # Tue–Sat

    names = [o.name for o in db_session.scalars(select(Owner))]
    names += [p.name for p in db_session.scalars(select(Pet))]
    assert all(n.startswith("Syn") for n in names)

    assert any(v.days_since_last is not None for v in visits)  # dogs come back
    assert any(v.predicted_min_p50 is not None for v in visits)  # estimates from breeds
    assert db_session.scalar(select(func.count()).select_from(Pet).where(Pet.species == "cat"))

    # Owners with two dogs bring them on the same day
    same_day = db_session.execute(
        select(Visit.owner_id, Visit.visit_date)
        .group_by(Visit.owner_id, Visit.visit_date)
        .having(func.count(func.distinct(Visit.pet_id)) > 1)
    ).all()
    assert same_day
