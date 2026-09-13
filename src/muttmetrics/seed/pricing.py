"""Optional price overrides loaded from a gitignored local file.

Service prices are the salon's commercial data. They are never committed.
Put real values in `data/private/pricing.json` (gitignored):

    {"full_groom": 75, "de_mat": 100}

Missing file, missing key, or a bad value simply leaves `price_base` NULL,
which is a valid state - nothing downstream requires a catalog price.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

LOGGER = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[3]
PRICING_PATH = _REPO_ROOT / "data" / "private" / "pricing.json"


def load_price_overrides(path: Path | None = None) -> dict[str, float]:
    """Return {service_slug: price}. Empty dict when no local file is present."""
    path = path or PRICING_PATH
    if not path.exists():
        LOGGER.info("No %s - seeding services with NULL price_base.", path)
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        LOGGER.warning("Could not read %s - seeding with NULL price_base.", path)
        return {}
    if not isinstance(raw, dict):
        LOGGER.warning("%s is not a JSON object - ignoring.", path)
        return {}
    out: dict[str, float] = {}
    for slug, value in raw.items():
        key = str(slug)
        if key.startswith("_"):
            continue
        if isinstance(value, int | float) and not isinstance(value, bool):
            out[key] = float(value)
        else:
            LOGGER.warning("Ignoring non-numeric price for %r in %s.", slug, path)
    return out


def apply_price_overrides(rows: list[dict], overrides: dict[str, float]) -> list[dict]:
    """Return seed rows with `price_base` filled in where an override exists."""
    if not overrides:
        return rows
    merged = []
    for row in rows:
        row = dict(row)
        if row.get("slug") in overrides:
            row["price_base"] = overrides[row["slug"]]
        merged.append(row)
    return merged
