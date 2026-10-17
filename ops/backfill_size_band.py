"""Set dog.size_band from weight_kg for rows that already have a weight (#171).

Dogs without weight are skipped — size_band stays NULL. The prior and profile
already compute size from weight on read; this only syncs the stored column
for dogs that were weighed before write-through existed.

    python ops/backfill_size_band.py             # report only (dry run)
    python ops/backfill_size_band.py --apply     # write size_band
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from muttmetrics.db.session import session_scope
from muttmetrics.models import Dog
from muttmetrics.priors.size import size_band_from_weight


@dataclass
class BackfillReport:
    total: int = 0
    no_weight: int = 0
    unchanged: int = 0
    # (dog_id, weight_kg, old band, new band) for every dog that needs a change
    changes: list[tuple[int, float, str | None, str | None]] = field(default_factory=list)


def backfill(session: Session, *, apply: bool) -> BackfillReport:
    """Compare every weighed dog's stored size_band with its weight.

    Dry run (apply=False) only reports. With apply=True the new bands are set
    on the session; the caller decides whether to commit (tests roll back).
    """
    report = BackfillReport()
    for dog in session.scalars(select(Dog).order_by(Dog.dog_id)):
        report.total += 1
        if dog.weight_kg is None:
            report.no_weight += 1
            continue
        new_band = size_band_from_weight(float(dog.weight_kg))
        if dog.size_band == new_band:
            report.unchanged += 1
            continue
        report.changes.append((dog.dog_id, float(dog.weight_kg), dog.size_band, new_band))
        if apply:
            dog.size_band = new_band
    if apply:
        session.flush()
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="write size_band (default: dry run, report only)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    with session_scope() as session:  # commits on success
        report = backfill(session, apply=args.apply)

    for dog_id, weight, old, new in report.changes:
        print(f"  dog_id={dog_id} weight_kg={weight} {old!r} → {new!r}")
    print(f"Dogs total:     {report.total}")
    print(f"No weight:      {report.no_weight} (skipped)")
    print(f"Already match:  {report.unchanged}")
    print(f"Would update:   {len(report.changes)}")
    if args.apply:
        print(f"\nUpdated {len(report.changes)} dog(s).")
    else:
        print("\nDry run - nothing written. Re-run with --apply to update.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
