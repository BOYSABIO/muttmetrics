"""ops/demo_data.py loads fixtures only into a database with no visits (#180)."""

from __future__ import annotations

import pytest
from ops.demo_data import load_demo
from sqlalchemy.orm import Session
from tests.fixtures.metric_month import VISITS as MONTH_VISITS
from tests.fixtures.metric_week import VISITS as WEEK_VISITS

from muttmetrics.models import Dog, Owner, Visit


def test_loads_both_fixtures_into_an_empty_database(db_session: Session) -> None:
    assert load_demo(db_session) == len(WEEK_VISITS) + len(MONTH_VISITS)


def test_refuses_when_visits_already_exist(db_session: Session) -> None:
    owner = Owner(name="Syn Real Client")
    db_session.add(owner)
    db_session.flush()
    dog = Dog(owner_id=owner.owner_id, name="Syn Real Dog")
    db_session.add(dog)
    db_session.flush()
    db_session.add(
        Visit(
            dog_id=dog.dog_id,
            owner_id=owner.owner_id,
            visit_date=WEEK_VISITS[0]["visit_date"],
            actual_minutes=60,
        )
    )
    db_session.flush()

    with pytest.raises(RuntimeError, match="already has 1 visit"):
        load_demo(db_session)
