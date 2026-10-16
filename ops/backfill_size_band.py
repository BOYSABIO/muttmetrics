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

from sqlalchemy import select

from muttmetrics.db.session import session_scope
from muttmetrics.models import Dog
from muttmetrics.priors.size import size_band_from_weight


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

    with session_scope() as session:
        dogs = session.scalars(select(Dog).order_by(Dog.dog_id)).all()

        would_set = 0
        unchanged = 0
        no_weight = 0

        for dog in dogs:
            if dog.weight_kg is None:
                no_weight += 1
                continue

            new_band = size_band_from_weight(float(dog.weight_kg))
            if dog.size_band == new_band:
                unchanged += 1
                continue

            would_set += 1
            print(
                f"  dog_id={dog.dog_id} weight_kg={dog.weight_kg} {dog.size_band!r} → {new_band!r}"
            )
            if args.apply:
                dog.size_band = new_band

        print(f"Dogs total:     {len(dogs)}")
        print(f"No weight:      {no_weight} (skipped)")
        print(f"Already match:  {unchanged}")
        print(f"Would update:   {would_set}")

        if not args.apply:
            print("\nDry run - nothing written. Re-run with --apply to update.")
        else:
            session.flush()
            print(f"\nUpdated {would_set} dog(s).")

    return 0


if __name__ == "__main__":
    sys.exit(main())
