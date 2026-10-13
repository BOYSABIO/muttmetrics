"""Price overlay loader — no Postgres required."""

import json
from pathlib import Path

from muttmetrics.seed.pricing import apply_price_overrides, load_price_overrides


def test_missing_file_returns_empty(tmp_path: Path) -> None:
    assert load_price_overrides(tmp_path / "missing.json") == {}


def test_loads_numeric_slugs_and_skips_comment_keys(tmp_path: Path) -> None:
    path = tmp_path / "pricing.json"
    path.write_text(
        json.dumps({"_comment": "ignore me", "full_groom": 75, "nails": 5}),
        encoding="utf-8",
    )
    assert load_price_overrides(path) == {"full_groom": 75.0, "nails": 5.0}


def test_invalid_json_returns_empty(tmp_path: Path) -> None:
    path = tmp_path / "pricing.json"
    path.write_text("{not json", encoding="utf-8")
    assert load_price_overrides(path) == {}


def test_apply_overrides_fills_matching_slugs_only() -> None:
    rows = [
        {"slug": "full_groom", "price_base": None},
        {"slug": "nails", "price_base": None},
    ]
    merged = apply_price_overrides(rows, {"full_groom": 75.0})
    assert merged[0]["price_base"] == 75.0
    assert merged[1]["price_base"] is None
    assert rows[0]["price_base"] is None
