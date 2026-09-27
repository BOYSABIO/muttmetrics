"""Delete stored photos for a client, dog, visit or single photo (#30).

Files first, then rows - the reverse of the write order, so a row is never
left pointing at bytes that are gone. Dry run unless --apply is given.

    python scripts/photo_purge.py --owner-id 42
    python scripts/photo_purge.py --owner-id 42 --apply

Backups still hold copies until the retention window in docs/privacy.md
passes. See docs/ops-photos.md for the full deletion procedure.
"""

from __future__ import annotations

import argparse
import sys

from sqlalchemy import Select, select

from muttmetrics import storage
from muttmetrics.db.session import session_scope
from muttmetrics.models import Dog, Photo


def parse_args() -> argparse.Namespace:
    """Exactly one selector, plus the safety flag."""
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--owner-id", type=int, help="every photo of every dog of this owner")
    group.add_argument("--dog-id", type=int, help="every photo of this dog")
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
        stmt = stmt.join(Dog, Dog.dog_id == Photo.dog_id).where(Dog.owner_id == args.owner_id)
    elif args.dog_id is not None:
        stmt = stmt.where(Photo.dog_id == args.dog_id)
    elif args.visit_id is not None:
        stmt = stmt.where(Photo.visit_id == args.visit_id)
    else:
        stmt = stmt.where(Photo.photo_id == args.photo_id)
    return stmt.order_by(Photo.photo_id)


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
                f"  photo_id={photo.photo_id} dog_id={photo.dog_id} "
                f"visit_id={photo.visit_id} kind={photo.kind} "
                f"bytes={photo.byte_size} key={photo.storage_key}"
            )

        if not args.apply:
            print("\nDry run - nothing deleted. Re-run with --apply to delete.")
            return 0

        files_deleted = 0
        rows_deleted = 0
        for photo in photos:
            try:
                if storage.delete(photo.storage_key):
                    files_deleted += 1
            except (OSError, ValueError) as exc:
                # Leave the row in place: while it exists the file is findable.
                print(f"  ! could not delete file for photo_id={photo.photo_id}: {exc}")
                continue
            session.delete(photo)
            rows_deleted += 1

        print(f"\nDeleted {files_deleted} file(s) and {rows_deleted} row(s).")
        print("Backups still contain copies - see docs/privacy.md.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
