"""Back up the capture database and photos (#95).

Two things, two mechanisms:
  - database: a fresh pg_dump custom-format archive each run (small, compressed)
  - photos:   an ADDITIVE file copy - new files only, never deletes

Additive matters: a mirror would propagate an accidental deletion into the
backup, which is the opposite of the job. Honouring a GDPR deletion request
therefore needs the backup copy removed too - see docs/architecture/privacy.md.

    python ops/backup.py
    python ops/backup.py --extra-dest D:/muttmetrics-backup
    python ops/backup.py --skip-photos

Today all destinations are usually on the same disk as the live data. That
protects against mistakes, not against losing the drive. The second entry
arrives with the shop box (#93).
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy.engine import make_url

from muttmetrics.config import get_settings
from muttmetrics.media import storage

REPO_ROOT = Path(__file__).resolve().parents[1]
_log_path: Path | None = None

KEEP_DAILY_DAYS = 14
KEEP_WEEKLY_WEEKS = 8
DUMP_PATTERN = "muttmetrics-*.dump"
DUMP_STAMP_FORMAT = "%Y%m%d-%H%M%S"


def log(message: str) -> None:
    """Print, and append to the log file in the primary destination."""
    print(message)
    if _log_path is not None:
        with _log_path.open("a", encoding="utf-8") as handle:
            handle.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} {message}\n")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--extra-dest",
        action="append",
        default=[],
        metavar="PATH",
        help="additional destination directory (repeatable)",
    )
    parser.add_argument("--skip-photos", action="store_true", help="database only")
    parser.add_argument("--no-prune", action="store_true", help="keep every old dump")
    return parser.parse_args()


def dump_database() -> bytes:
    """Run pg_dump inside the db container and return the archive bytes.

    -Fc is the custom format: compressed, and pg_restore can pull single tables
    out of it. -T on docker exec disables the TTY, so stdout stays clean binary -
    this is also why the bytes come back through a  pipe instead of a shell
    redirect, which on PowerShell would mangle them into UTF-16.
    """
    url = make_url(get_settings().database_url)
    proc = subprocess.run(
        [
            "docker",
            "compose",
            "exec",
            "-T",
            "db",
            "pg_dump",
            "-U",
            str(url.username),
            str(url.database),
            "-Fc",
        ],
        capture_output=True,
        check=True,
        cwd=REPO_ROOT,
    )
    return proc.stdout


def verify_dump(data: bytes) -> int:
    """Read the archive's table of contents; returns the number of entries.

    Cheap proof that the file is a complete, readable archive rather than a
    truncated one. Raises CalledProcessError if pg_restore cannot read it.
    """
    proc = subprocess.run(
        ["docker", "compose", "exec", "-T", "db", "pg_restore", "--list"],
        input=data,
        capture_output=True,
        check=True,
        cwd=REPO_ROOT,
    )
    return len([line for line in proc.stdout.splitlines() if line and not line.startswith(b";")])


def copy_new_photos(photo_root: Path, dest: Path) -> tuple[int, int]:
    """Copy photo files that are not already in dest. Returns (copied, skipped)."""
    copied = 0
    skipped = 0

    for src in photo_root.rglob("*"):
        if not src.is_file() or src.suffix == ".tmp":
            continue

        target = dest / src.relative_to(photo_root)
        if target.exists() and target.stat().st_size == src.stat().st_size:
            skipped += 1
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)  # copy2 keeps the modification time
        copied += 1

    return copied, skipped


def dump_timestamp(path: Path) -> datetime | None:
    """When this dump was taken, from its filename. None if it isn't ours."""
    try:
        return datetime.strptime(path.stem.removeprefix("muttmetrics-"), DUMP_STAMP_FORMAT)
    except ValueError:
        return None


def prune_dumps(db_dir: Path, now: datetime) -> list[Path]:
    """Keep every dump from the last 14 days, plus Sundays for 8 weeks.

    Anything this function cannot positively identify as one of its own dumps
    is left alone - when deleting, the safe default is to keep.
    """
    daily_cutoff = now - timedelta(days=KEEP_DAILY_DAYS)
    weekly_cutoff = now - timedelta(weeks=KEEP_WEEKLY_WEEKS)
    removed: list[Path] = []

    for path in sorted(db_dir.glob(DUMP_PATTERN)):
        when = dump_timestamp(path)
        if when is None:
            continue  # unrecognized name - never ours to delete
        if when >= daily_cutoff:
            continue  # daily tier
        if when.weekday() == 6 and when >= weekly_cutoff:
            continue  # Sunday tier
        path.unlink()
        removed.append(path)

    return removed


def write_status(dest: Path, payload: dict) -> None:
    """Machine-readable record of the last run, for the staleness check."""
    (dest / "last-backup.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> int:
    """Main entry point."""
    args = parse_args()
    settings = get_settings()

    destinations = [settings.backup_root.expanduser().resolve()]
    destinations += [Path(p).expanduser().resolve() for p in args.extra_dest]

    global _log_path
    destinations[0].mkdir(parents=True, exist_ok=True)
    _log_path = destinations[0] / "backup.log"

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    log(f"[{stamp}] dumping database...")
    try:
        dump = dump_database()
    except FileNotFoundError:
        log("ERROR: docker not found on PATH")
        return 1
    except subprocess.CalledProcessError as exc:
        log(f"ERROR: pg_dump failed: {exc.stderr.decode(errors='replace')}")
        return 1

    try:
        entries = verify_dump(dump)
    except subprocess.CalledProcessError as exc:
        log(f"ERROR: dump is not readable: {exc.stderr.decode(errors='replace')}")
        return 1

    log(f"  dump OK: {len(dump) / 1024:.0f} KB, {entries} archive entries")

    photo_root = storage.photo_root()

    for dest in destinations:
        db_dir = dest / "db"
        db_dir.mkdir(parents=True, exist_ok=True)

        dump_path = db_dir / f"muttmetrics-{stamp}.dump"
        dump_path.write_bytes(dump)
        log(f"  wrote {dump_path}")

        copied = 0
        skipped = 0
        if not args.skip_photos and photo_root.exists():
            copied, skipped = copy_new_photos(photo_root, dest / "photos")
            log(f"  photos: {copied} new, {skipped} already there")

        pruned: list[Path] = []
        if not args.no_prune:
            pruned = prune_dumps(db_dir, datetime.now())
            if pruned:
                log(f"  pruned {len(pruned)} old dump(s)")

        write_status(
            dest,
            {
                "finished_at": datetime.now().isoformat(timespec="seconds"),
                "dump_file": dump_path.name,
                "dump_bytes": len(dump),
                "archive_entries": entries,
                "photos_copied": copied,
                "photos_present": copied + skipped,
                "dumps_pruned": len(pruned),
            },
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
