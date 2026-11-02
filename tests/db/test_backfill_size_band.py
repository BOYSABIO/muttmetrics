"""ops/backfill_size_band.py: dry run reports, --apply writes (#171, tests #180)."""

from __future__ import annotations

from decimal import Decimal

from ops.backfill_size_band import backfill
from sqlalchemy.orm import Session

from muttmetrics.models import Owner, Pet


def _dogs(db_session: Session) -> tuple[Pet, Pet]:
    owner = Owner(name="Syn Backfill Owner")
    db_session.add(owner)
    db_session.flush()
    weighed = Pet(owner_id=owner.owner_id, name="Syn Weighed", weight_kg=Decimal("7.5"))
    unweighed = Pet(owner_id=owner.owner_id, name="Syn Unweighed")
    db_session.add_all([weighed, unweighed])
    db_session.flush()
    return weighed, unweighed


def test_dry_run_reports_but_writes_nothing(db_session: Session) -> None:
    weighed, unweighed = _dogs(db_session)

    report = backfill(db_session, apply=False)

    assert (weighed.pet_id, 7.5, None, "s") in report.changes
    assert all(change[0] != unweighed.pet_id for change in report.changes)
    db_session.refresh(weighed)
    assert weighed.size_band is None


def test_apply_writes_the_band_and_is_idempotent(db_session: Session) -> None:
    weighed, unweighed = _dogs(db_session)

    backfill(db_session, apply=True)
    db_session.refresh(weighed)
    db_session.refresh(unweighed)
    assert weighed.size_band == "s"
    assert unweighed.size_band is None  # no weight: left alone

    again = backfill(db_session, apply=False)
    assert all(change[0] != weighed.pet_id for change in again.changes)
