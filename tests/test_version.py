"""Package marker for tests."""

from muttmetrics import __version__


def test_version_is_semver_shaped() -> None:
    parts = __version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)
