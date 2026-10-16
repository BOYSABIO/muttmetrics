"""size_band_from_weight() boundaries (#171)."""

import pytest

from muttmetrics.priors.size import size_band_from_weight


@pytest.mark.parametrize(
    ("kg", "expected"),
    [
        (None, None),
        (0, None),
        (-1, None),
        (10, "s"),
        (10.1, "m"),
        (26, "m"),
        (26.1, "l"),
        (45, "l"),
        (45.1, "xl"),
        (1, "s"),
        (100, "xl"),
    ],
)
def test_size_band_boundaries(kg: float | None, expected: str | None) -> None:
    assert size_band_from_weight(kg) == expected
