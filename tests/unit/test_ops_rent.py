"""ops/rent.py: argument parsing (no database needed)."""

from __future__ import annotations

import argparse
from datetime import date
from decimal import Decimal

import pytest
from ops.rent import parse_amount, parse_args, parse_month


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2026-10", date(2026, 10, 1)),
        ("2026-10-01", date(2026, 10, 1)),
        (" 2027-1 ", date(2027, 1, 1)),
    ],
)
def test_parse_month(raw: str, expected: date) -> None:
    assert parse_month(raw) == expected


@pytest.mark.parametrize("raw", ["2026-10-15", "2026", "2026-13", "october"])
def test_parse_month_rejects(raw: str) -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        parse_month(raw)


def test_parse_amount() -> None:
    assert parse_amount("2000") == Decimal("2000")
    assert parse_amount("1999,50") == Decimal("1999.50")
    with pytest.raises(argparse.ArgumentTypeError):
        parse_amount("-5")
    with pytest.raises(argparse.ArgumentTypeError):
        parse_amount("lots")


def test_set_and_from_go_together() -> None:
    with pytest.raises(SystemExit):
        parse_args(["--set", "2000"])
    args = parse_args(["--set", "2000", "--from", "2026-10"])
    assert (args.amount, args.valid_from, args.apply) == (Decimal("2000"), date(2026, 10, 1), False)
