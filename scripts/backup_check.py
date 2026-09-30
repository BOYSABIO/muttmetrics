"""Is the backup still running? (#95)

A backup that stops does not raise an error - it goes quiet. This reads the
status file written by scripts/backup.py and says plainly how old the last
run is, exiting non-zero when it is too old (or missing entirely).

    python scripts/backup_check.py
    python scripts/backup_check.py --max-age-hours 24

Exit codes: 0 fresh, 1 stale or missing. The exit code is there so this can
later be wired into something that shouts on its own (see the icebox
monitoring issue) - today it is for a human running it.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from muttmetrics.config import get_settings

STATUS_FILE = "last-backup.json"
DUMP_PATTERN = "muttmetrics-*.dump"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--max-age-hours",
        type=float,
        default=36.0,
        help="how old the last backup may be before this fails (default: 36)",
    )
    parser.add_argument(
        "--dest",
        action="append",
        default=[],
        metavar="PATH",
        help="check this destination instead of BACKUP_ROOT (repeatable)",
    )
    return parser.parse_args()


def check_destination(dest: Path, max_age_hours: float) -> bool:
    """Report on one destination. Returns True if it looks healthy."""
    print(f"{dest}")

    status_path = dest / STATUS_FILE
    if not status_path.exists():
        print("  FAIL: no status file - has the backup ever run here?")
        return False

    try:
        status = json.loads(status_path.read_text(encoding="utf-8"))
        finished_at = datetime.fromisoformat(status["finished_at"])
    except (ValueError, KeyError) as exc:
        print(f"  FAIL: status file is unreadable ({exc})")
        return False

    age_hours = (datetime.now() - finished_at).total_seconds() / 3600
    dumps = sorted((dest / "db").glob(DUMP_PATTERN))

    print(f"  last run   : {finished_at:%Y-%m-%d %H:%M} ({age_hours:.1f} h ago)")
    print(f"  dump       : {status.get('dump_file')} ({status.get('dump_bytes', 0) / 1024:.0f} KB)")
    print(f"  photos     : {status.get('photos_present', 0)} copied so far")
    print(f"  dumps kept : {len(dumps)}")

    healthy = True

    if age_hours > max_age_hours:
        print(f"  FAIL: older than {max_age_hours:.0f} h - the backup has stopped running")
        healthy = False

    # The status file could be written while the dump itself failed to land,
    # so trust the directory, not only the report.
    newest = status.get("dump_file")
    if newest is not None and not (dest / "db" / newest).exists():
        print(f"  FAIL: status names {newest}, but that file is not in db/")
        healthy = False

    if not dumps:
        print("  FAIL: no dumps in db/ at all")
        healthy = False

    if healthy:
        print("  OK")

    return healthy


def main() -> int:
    args = parse_args()

    if args.dest:
        destinations = [Path(p).expanduser().resolve() for p in args.dest]
    else:
        destinations = [get_settings().backup_root.expanduser().resolve()]

    results = [check_destination(dest, args.max_age_hours) for dest in destinations]

    if all(results):
        return 0

    print("\nBackup is not healthy - see docs/runbooks/backup.md", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
