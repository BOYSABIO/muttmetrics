"""#177: the suite refuses to run against a non-test database."""

import pytest
from tests.db_guard import require_test_database


def test_accepts_a_test_database() -> None:
    url = "postgresql+psycopg://u:p@127.0.0.1:5432/muttmetrics_test"
    assert require_test_database(url) == url


@pytest.mark.parametrize("name", ["muttmetrics", "salon", ""])
def test_refuses_anything_else(name: str) -> None:
    with pytest.raises(ValueError, match="must contain 'test'"):
        require_test_database(f"postgresql+psycopg://u:p@127.0.0.1:5432/{name}")
