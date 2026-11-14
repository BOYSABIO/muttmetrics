"""Load the synthetic test fixtures into an EMPTY local database, for demos and
screenshots (#16, #180).

The rows are the same Syn* owners, pets and visits the metric tests use, with
hand-computed answers in tests/fixtures/. They land in March and April 2026, so
open the dashboard and step back to those weeks / that month.

    python ops/demo_data.py            # refuses if the database already has visits
    python ops/demo_data.py --recent   # also ~12 weeks of rolling Syn* visits ending today

Refusing on existing visits is the safety net: the salon database always has
some, so this can never mix fake rows into real ones. Point DATABASE_URL at a
throwaway database first (e.g. muttmetrics_demo, migrated and seeded).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from muttmetrics.db.session import session_scope
from muttmetrics.models import Visit

# The fixtures live in tests/, importable from the repo root. Running
# `python ops/demo_data.py` puts ops/ on the path instead, so add the root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ops.demo_recent import load_recent  # noqa: E402
from tests.fixtures.load_metric_month import load_metric_month  # noqa: E402
from tests.fixtures.load_metric_week import load_metric_week  # noqa: E402


def load_demo(session: Session, *, recent: bool = False) -> int:
    """Insert the week + month fixtures (and, with ``recent``, the rolling weeks).
    Returns the number of visits in the database afterwards.

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
    if recent:
        load_recent(session)
    session.flush()
    return session.scalar(select(func.count()).select_from(Visit)) or 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--recent",
        action="store_true",
        help="also add ~12 weeks of synthetic visits ending today (ops/demo_recent.py)",
    )
    args = parser.parse_args()
    try:
        with session_scope() as session:  # commits on success
            added = load_demo(session, recent=args.recent)
    except RuntimeError as exc:
        print(exc)
        return 1
    extra = " plus the last 12 weeks" if args.recent else ""
    print(f"Loaded {added} synthetic visits (weeks of 2026-03-02 and April 2026{extra}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
