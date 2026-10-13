"""Guard against CP437 double-encoded UTF-8 in tracked SQL/Markdown (#154).

Background (why this exists)
---------------------------
UTF-8 bytes for punctuation like em dash (—) or arrow (→) were once
*misread* as code page 437 (old DOS), then saved again as UTF-8. The file
is still "valid UTF-8", but of the *wrong* characters: an em dash becomes
the visible junk ``ΓÇö``. That happened during the scripts→ops move (#125);
comments were poisoned, queries were not — yet.

M5 will run the same SQL recipes with money symbols (euro) and breed
names. A PowerShell pipe (Get-Content into docker) can also re-encode
non-ASCII on the way into psql. Repair the files, document an
encoding-safe runner (docker compose cp + psql -f), and keep this
guard so the signature cannot return unnoticed.

A guard that has never failed proves nothing (#89). So we also feed the
detector a fabricated mojibake string and assert it fires.
"""

from __future__ import annotations

from pathlib import Path

import pytest


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").is_file():
            return parent
    raise RuntimeError("could not locate repo root (pyproject.toml)")


REPO = _repo_root()

# Visible leftovers of UTF-8 → CP437 → UTF-8 round-trips.
# ΓÇ  covers —, –, “, ”, •, …
# Γå  covers → and similar arrows
MOJIBAKE_SIGNATURES = ("ΓÇ", "Γå")

# Tracked text we care about for maintainer SQL / runbooks.
SCAN_SUFFIXES = {".sql", ".md"}

# Directories that hold durable docs/scripts (not node_modules, not venv).
SCAN_ROOTS = (
    REPO / "ops",
    REPO / "docs",
)


def iter_tracked_text_files() -> list[Path]:
    files: list[Path] = []
    for root in SCAN_ROOTS:
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in SCAN_SUFFIXES:
                continue
            # Personal / local escape hatches are gitignored; skip if present.
            if path.name.endswith(".local.sql"):
                continue
            files.append(path)
    return sorted(files)


def mojibake_hits(text: str) -> list[str]:
    """Return which signatures appear in text (empty ⇒ clean)."""
    return [sig for sig in MOJIBAKE_SIGNATURES if sig in text]


def test_detector_flags_known_mojibake() -> None:
    """The detector must be able to fail, or it proves nothing."""
    poisoned = "-- Week = MonΓÇôSun on visit_date\n-- error ΓåÆ under-predicted\n"
    assert mojibake_hits(poisoned) == ["ΓÇ", "Γå"]


def test_detector_allows_clean_utf8_punctuation() -> None:
    """Real dashes/arrows after repair must not trip the guard."""
    clean = "-- Week = Mon–Sun\n-- error → under-predicted\n-- breed — Doodles\n"
    assert mojibake_hits(clean) == []


def test_scan_roots_exist() -> None:
    """A guard that scans nothing passes for the wrong reason."""
    files = iter_tracked_text_files()
    assert files, f"no .sql/.md files under {SCAN_ROOTS} — guard is not running"


@pytest.mark.parametrize(
    "path",
    iter_tracked_text_files(),
    ids=lambda p: str(p.relative_to(REPO)).replace("\\", "/"),
)
def test_no_cp437_mojibake_in_tracked_text(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    hits = mojibake_hits(text)
    if not hits:
        return
    rel = path.relative_to(REPO).as_posix()
    pytest.fail(
        f"{rel} contains CP437 double-encoding signature(s): {hits}\n\n"
        "UTF-8 punctuation was misread as code page 437 and saved again.\n"
        "Repair by reversing the round-trip (non-ASCII run → encode cp437 →\n"
        "decode utf-8), or restore from git before the scripts→ops move.\n"
        "See #154 and docs/runbooks/db-peek.md (encoding-safe SQL runs).\n",
        pytrace=False,
    )
