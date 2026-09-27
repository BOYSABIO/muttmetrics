"""Find photo files on disk with no database row (#30).

Normal causes: a crash between writing the file and inserting the row, or a
.tmp file from an interrupted write. Files newer than --min-age-hours are
never touched, so an upload in flight is safe.

    python scripts/photo_sweep.py             # report only
    python scripts/photo_sweep.py --apply     # delete the orphans
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from sqlalchemy import select

from muttmetrics import storage
from muttmetrics.db.session import session_scope
from muttmetrics.models import Photo


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="actually delete orphans (default: report only)",
    )
    parser.add_argument(
        "--min-age-hours",
        type=float,
        default=1.0,
        help="ignore files younger than this (default: 1)",
    )
    return parser.parse_args()


def find_orphans(root: Path, known_keys: set[str], cutoff: float) -> list[Path]:
    """Files under root that no row references and that are older than cutoff."""
    orphans: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        key = path.relative_to(root).as_posix()
        if key in known_keys:
            continue
        if path.stat().st_mtime >= cutoff:
            continue  # too new - could be an upload in progress
        orphans.append(path)
    return orphans


def main() -> int:
    args = parse_args()
    root = storage.photo_root()

    if not root.exists():
        print(f"Photo root does not exist yet: {root}")
        return 0

    with session_scope() as session:
        known_keys = set(session.scalars(select(Photo.storage_key)))

    cutoff = time.time() - args.min_age_hours * 3600
    orphans = find_orphans(root, known_keys, cutoff)

    print(f"Photo root: {root}")
    print(f"Rows in database: {len(known_keys)}")

    if not orphans:
        print("No orphan files.")
        return 0

    total_bytes = sum(path.stat().st_size for path in orphans)
    print(f"Orphan files: {len(orphans)} ({total_bytes / 1024 / 1024:.1f} MB)")
    for path in orphans:
        print(f"  {path.relative_to(root).as_posix()}")

    if not args.apply:
        print("\nDry run - nothing deleted. Re-run with --apply to delete.")
        return 0

    deleted = 0
    for path in orphans:
        try:
            path.unlink()
            deleted += 1
        except OSError as exc:
            print(f"  ! could not delete {path}: {exc}")

    print(f"\nDeleted {deleted} orphan file(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
