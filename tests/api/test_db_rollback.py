"""Prove db_session writes are visible in-test and gone after rollback."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from muttmetrics.models import Owner

PROBE_NAME = "Syn Rollback Probe"


def test_db_session_can_insert_owner(db_session: Session) -> None:
    db_session.add(Owner(name=PROBE_NAME))
    db_session.flush()  # send INSERT to Postgres without sealing the outer pad

    count = db_session.scalar(
        select(func.count()).select_from(Owner).where(Owner.name == PROBE_NAME)
    )
    assert count == 1


def test_db_session_rollback_left_no_probe_owner(db_session: Session) -> None:
    """Runs after the insert test (same file order). Must see zero committed rows."""
    count = db_session.scalar(
        select(func.count()).select_from(Owner).where(Owner.name == PROBE_NAME)
    )
    assert count == 0
