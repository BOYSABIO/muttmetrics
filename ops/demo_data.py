"""Load the synthetic test fixtures into an EMPTY local database, for demos and
screenshots (#16, #180).

The rows are the same Syn* owners, dogs and visits the metric tests use, with
hand-computed answers in tests/fixtures/. They land in March and April 2026, so
open the dashboard and step back to those weeks / that month.

    python ops/demo_data.py            # refuses if the database already has visits

Refusing on existing visits is the safety net: the salon database always has
some, so this can never mix fake rows into real ones. Point DATABASE_URL at a
throwaway database first (e.g. muttmetrics_demo, migrated and seeded).
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from muttmetrics.db.session import session_scope
from muttmetrics.models import Visit

# The fixtures live in tests/, importable from the repo root. Running
# `python ops/demo_data.py` puts ops/ on the path instead, so add the root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tests.fixtures.load_metric_month import load_metric_month  # noqa: E402
from tests.fixtures.load_metric_week import load_metric_week  # noqa: E402


def load_demo(session: Session) -> int:
    """Insert the week + month fixtures. Returns the number of visits added.

    Raises RuntimeError if any visit already exists.
    """
    existing = session.scalar(select(func.count()).select_from(Visit)) or 0
    if existing:
        raise RuntimeError(
            f"Refusing: this database already has {existing} visit(s). "
            "Demo data only goes into an empty database."
        )
    load_metric_week(session)
    load_metric_month(session)
    session.flush()
    return session.scalar(select(func.count()).select_from(Visit)) or 0


def main() -> int:
    try:
        with session_scope() as session:  # commits on success
            added = load_demo(session)
    except RuntimeError as exc:
        print(exc)
        return 1
    print(f"Loaded {added} synthetic visits (weeks of 2026-03-02 and April 2026).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
