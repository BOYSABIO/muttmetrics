"""Refuse to run the test suite against anything but a test database (#177).

Tests roll back, but one committing test or a stray seed run would write into
whatever DATABASE_URL points at, and locally that used to be the salon's real
database. The cheapest protection is a naming rule: the database name must
contain "test".
"""

from __future__ import annotations

from sqlalchemy.engine import make_url

DEFAULT_TEST_DATABASE_URL = (
    "postgresql+psycopg://muttmetrics:muttmetrics@127.0.0.1:5432/muttmetrics_test"
)


def require_test_database(url: str) -> str:
    """Return ``url`` unchanged, or raise ValueError if it isn't a test database."""
    name = make_url(url).database or ""
    if "test" not in name.lower():
        raise ValueError(
            f"Refusing to run tests against database {name!r}: its name must contain "
            "'test'. Set TEST_DATABASE_URL (default: muttmetrics_test)."
        )
    return url
