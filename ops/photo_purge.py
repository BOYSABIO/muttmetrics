"""Delete stored photos for a client, pet, visit or single photo (#30).

Files first, then rows - the reverse of the write order, so a row is never
left pointing at bytes that are gone. Dry run unless --apply is given.

    python ops/photo_purge.py --owner-id 42
    python ops/photo_purge.py --owner-id 42 --apply

The additive photo copies under <BACKUP_ROOT>/photos/ are removed too (same
relative key). Database dumps still age out on their own schedule; a second copy
on another device (#221) needs the printed keys removed by hand. See
docs/runbooks/backup.md §6 and docs/architecture/privacy.md.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import Select, select

from muttmetrics.config import get_settings
from muttmetrics.db.session import session_scope
from muttmetrics.media import storage
from muttmetrics.models import Pet, Photo


def parse_args() -> argparse.Namespace:
    """Exactly one selector, plus the safety flag."""
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--owner-id", type=int, help="every photo of every pet of this owner")
    group.add_argument("--pet-id", type=int, help="every photo of this pet")
    group.add_argument("--visit-id", type=int, help="every photo of this visit")
    group.add_argument("--photo-id", type=int, help="one photo")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="actually delete (default: report only)",
    )
    return parser.parse_args()


def build_query(args: argparse.Namespace) -> Select[tuple[Photo]]:
    """Photos matching the chosen selector."""
    stmt = select(Photo)
    if args.owner_id is not None:
        stmt = stmt.join(Pet, Pet.pet_id == Photo.pet_id).where(Pet.owner_id == args.owner_id)
    elif args.pet_id is not None:
        stmt = stmt.where(Photo.pet_id == args.pet_id)
    elif args.visit_id is not None:
        stmt = stmt.where(Photo.visit_id == args.visit_id)
    else:
        stmt = stmt.where(Photo.photo_id == args.photo_id)
    return stmt.order_by(Photo.photo_id)


def photos_for_owner(session, owner_id: int) -> list[Photo]:
    """Every photo row for every pet of this owner (used by client_erase #195)."""
    stmt = (
        select(Photo)
        .join(Pet, Pet.pet_id == Photo.pet_id)
        .where(Pet.owner_id == owner_id)
        .order_by(Photo.photo_id)
    )
    return list(session.scalars(stmt))


@dataclass
class PurgeResult:
    files_deleted: int = 0
    rows_deleted: int = 0
    backup_copies_deleted: int = 0
    # Keys whose rows are gone: the only record of where other copies live.
    deleted_keys: list[str] = field(default_factory=list)


def backup_copy_path(backup_root: Path, key: str) -> Path:
    """Where backup.py put this photo: <backup_root>/photos/<key>, never outside it."""
    base = (backup_root / "photos").resolve()
    candidate = (base / key).resolve()
    if base not in candidate.parents:
        raise ValueError(f"key escapes the backup photo folder: {key!r}")
    return candidate


def purge_photos(
    session, photos: list[Photo], *, apply: bool, backup_root: Path | None = None
) -> PurgeResult:
    """Delete photo files, their backup copies, then rows.

    Dry run (apply=False) deletes nothing. On a live-file error the row is
    left so the bytes stay findable — same rule as the CLI. ``backup_root``
    None skips the backup copies (tests, or a machine without backups).
    """
    result = PurgeResult()
    if not apply:
        return result
    for photo in photos:
        try:
            if storage.delete(photo.storage_key):
                result.files_deleted += 1
        except (OSError, ValueError) as exc:
            print(f"  ! could not delete file for photo_id={photo.photo_id}: {exc}")
            continue
        if backup_root is not None:
            try:
                copy = backup_copy_path(backup_root, photo.storage_key)
                if copy.is_file():
                    copy.unlink()
                    result.backup_copies_deleted += 1
            except (OSError, ValueError) as exc:
                print(f"  ! could not delete backup copy for photo_id={photo.photo_id}: {exc}")
        result.deleted_keys.append(photo.storage_key)
        session.delete(photo)
        result.rows_deleted += 1
    return result


def default_backup_root() -> Path:
    return get_settings().backup_root.expanduser().resolve()


def main() -> int:
    args = parse_args()

    with session_scope() as session:
        photos = list(session.scalars(build_query(args)))

        if not photos:
            print("No photos match that selector.")
            return 0

        print(f"{len(photos)} photo(s):")
        for photo in photos:
            print(
                f"  photo_id={photo.photo_id} pet_id={photo.pet_id} "
                f"visit_id={photo.visit_id} kind={photo.kind} "
                f"bytes={photo.byte_size} key={photo.storage_key}"
            )

        if not args.apply:
            print("\nDry run - nothing deleted. Re-run with --apply to delete.")
            return 0

        backup_root = default_backup_root()
        result = purge_photos(session, photos, apply=True, backup_root=backup_root)

        print(
            f"\nDeleted {result.files_deleted} file(s), {result.rows_deleted} row(s) and "
            f"{result.backup_copies_deleted} backup cop(ies) under {backup_root / 'photos'}."
        )
        print("Keys (remove the same ones from any other backup copy, e.g. #221):")
        for key in result.deleted_keys:
            print(f"  {key}")
        print("Database dumps still age out - see docs/architecture/privacy.md.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
