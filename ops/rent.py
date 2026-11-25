"""Show or set the monthly rent the dashboard measures take-home against (#229).

The amount is the salon's own figure, so it lives in the database only: set it
here on the box, never in the repo. A row means "from this month on"; a change
later adds a row, so earlier months keep the rent they had. Rent is due on the
1st. Dry run unless --apply.

    python ops/rent.py                                  # show what's set
    python ops/rent.py --set 2000 --from 2026-03        # dry run
    python ops/rent.py --set 2000 --from 2026-03 --apply

Setting the same month again replaces that month's amount. --set 0 from a
month means no rent from then on (the bar disappears).
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

# `python ops/rent.py` puts ops/ on sys.path; tests use the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from muttmetrics.db.session import session_scope  # noqa: E402
from muttmetrics.models import FixedCost  # noqa: E402


def parse_month(raw: str) -> date:
    """'2026-10' or '2026-10-01' → date(2026, 10, 1)."""
    parts = raw.strip().split("-")
    if len(parts) not in (2, 3):
        raise argparse.ArgumentTypeError("use YYYY-MM, e.g. 2026-03")
    try:
        year, month = int(parts[0]), int(parts[1])
        if len(parts) == 3 and int(parts[2]) != 1:
            raise argparse.ArgumentTypeError("rent starts on the 1st: use YYYY-MM")
        return date(year, month, 1)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("use YYYY-MM, e.g. 2026-03") from exc


def parse_amount(raw: str) -> Decimal:
    try:
        amount = Decimal(raw.replace(",", "."))
    except InvalidOperation as exc:
        raise argparse.ArgumentTypeError("the amount must be a number, e.g. 2000") from exc
    if amount < 0:
        raise argparse.ArgumentTypeError("the amount can't be negative")
    return amount


def rent_rows(session: Session) -> list[FixedCost]:
    return list(
        session.scalars(
            select(FixedCost).where(FixedCost.kind == "rent").order_by(FixedCost.valid_from)
        )
    )


def set_rent(session: Session, amount: Decimal, valid_from: date) -> str:
    """Add (or replace) the rent from ``valid_from``; returns what it did."""
    existing = session.scalar(
        select(FixedCost).where(FixedCost.kind == "rent", FixedCost.valid_from == valid_from)
    )
    if existing is None:
        session.add(FixedCost(kind="rent", monthly_amount=amount, valid_from=valid_from))
        return "added"
    existing.monthly_amount = amount
    return "replaced"


def show(rows: list[FixedCost]) -> None:
    if not rows:
        print("No rent set. The dashboard shows no rent bar.")
        return
    print("Rent (due on the 1st), from:")
    for row in rows:
        print(f"  {row.valid_from:%Y-%m}  {Decimal(row.monthly_amount):,.2f} / month")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--set", dest="amount", type=parse_amount, help="monthly rent, e.g. 2000")
    p.add_argument(
        "--from", dest="valid_from", type=parse_month, help="first month it applies, YYYY-MM"
    )
    p.add_argument("--apply", action="store_true", help="write it (default: dry run)")
    args = p.parse_args(argv)
    if (args.amount is None) != (args.valid_from is None):
        p.error("--set and --from go together")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    with session_scope() as session:
        show(rent_rows(session))
        if args.amount is None:
            return 0
        print(f"\nTo set: {args.amount:,.2f} / month from {args.valid_from:%Y-%m}")
        if not args.apply:
            print("Dry run - nothing changed. Re-run with --apply to save.")
            return 0
        what = set_rent(session, args.amount, args.valid_from)
        session.flush()
        print(f"Saved ({what}).\n")
        show(rent_rows(session))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
