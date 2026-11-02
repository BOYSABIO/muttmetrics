"""size_band_from_weight() boundaries (#171 / #190)."""

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
def test_size_band_dog_boundaries(kg: float | None, expected: str | None) -> None:
    assert size_band_from_weight(kg) == expected
    assert size_band_from_weight(kg, "dog") == expected


@pytest.mark.parametrize(
    ("kg", "expected"),
    [
        (None, None),
        (0, None),
        (4.0, "s"),
        (4.1, "m"),
        (5.5, "m"),
        (5.6, "l"),
        (7.5, "l"),
        (7.6, "xl"),
        (12.0, "xl"),
    ],
)
def test_size_band_cat_boundaries_provisional(kg: float | None, expected: str | None) -> None:
    """Cat kg cutoffs are labelled provisional in ADR-004."""
    assert size_band_from_weight(kg, "cat") == expected


def test_unknown_species_has_no_scale() -> None:
    """A 5 kg cat is m; the same kg on an unscaled species is not a dog band."""
    assert size_band_from_weight(5.0, "cat") == "m"
    assert size_band_from_weight(5.0, "rabbit") is None
