"""Art. 17 erasure for one owner — anonymise, do not hard-delete (#195).

Photos go first (reuse photo_purge: live file, its copy under <BACKUP_ROOT>/photos/,
then the row), then owner/pet/visit free-text is scrubbed in place so visit facts
remain for bookkeeping and M7. Dry run unless --apply. The photo keys are printed,
because after --apply they are the only record of copies on another device (#221).

    python ops/client_erase.py --owner-id 42
    python ops/client_erase.py --owner-id 42 --apply

Idempotent: a second apply on an already-erased owner is a safe no-op.
See docs/architecture/privacy.md and docs/runbooks/client-requests.md.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

# `python ops/client_erase.py` puts ops/ on sys.path; tests use the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ops.photo_purge import default_backup_root, photos_for_owner, purge_photos  # noqa: E402

from muttmetrics.db.session import session_scope  # noqa: E402
from muttmetrics.models import Owner, Pet, Visit  # noqa: E402

# Stable placeholders — also the idempotency signal.
OWNER_NAME_FMT = "Erased client #{owner_id}"
PET_NAME_FMT = "Erased pet #{pet_id}"


def erased_owner_name(owner_id: int) -> str:
    return OWNER_NAME_FMT.format(owner_id=owner_id)


def erased_pet_name(pet_id: int) -> str:
    return PET_NAME_FMT.format(pet_id=pet_id)


@dataclass
class EraseReport:
    owner_id: int
    owner_found: bool = False
    already_erased: bool = False
    photo_count: int = 0
    photo_keys: list[str] = field(default_factory=list)
    photos_files_deleted: int = 0
    photos_rows_deleted: int = 0
    backup_copies_deleted: int = 0
    owner_fields_cleared: list[str] = field(default_factory=list)
    pets_renamed: list[int] = field(default_factory=list)
    visits_scrubbed: list[int] = field(default_factory=list)


def _owner_needs_scrub(owner: Owner) -> bool:
    if owner.name != erased_owner_name(owner.owner_id):
        return True
    return any(
        value not in (None, "")
        for value in (
            owner.phone,
            owner.email,
            owner.notes,
            owner.address_area,
            owner.preferred_channel,
            owner.client_since,
        )
    )


def _pet_needs_scrub(pet: Pet) -> bool:
    if pet.name != erased_pet_name(pet.pet_id):
        return True
    return any(
        value not in (None, "", [])
        for value in (
            pet.temperament_notes,
            pet.mobility_notes,
            pet.vet_notes,
            pet.fear_triggers,
        )
    )


def _visit_needs_scrub(visit: Visit) -> bool:
    return bool(visit.what_surprised_me) or bool(visit.pivot_reason)


def load_owner_for_erase(session: Session, owner_id: int) -> Owner | None:
    stmt = (
        select(Owner)
        .where(Owner.owner_id == owner_id)
        .options(
            selectinload(Owner.pets).selectinload(Pet.visits),
        )
    )
    return session.scalars(stmt).first()


def erase_owner(
    session: Session, owner_id: int, *, apply: bool, backup_root: Path | None = None
) -> EraseReport:
    """Anonymise one owner. Photos (and their backup copies) purged when apply=True.

    Raises LookupError if the owner id does not exist.
    """
    report = EraseReport(owner_id=owner_id)
    owner = load_owner_for_erase(session, owner_id)
    if owner is None:
        raise LookupError(f"No owner with owner_id={owner_id}")
    report.owner_found = True

    photos = photos_for_owner(session, owner_id)
    report.photo_count = len(photos)
    report.photo_keys = [p.storage_key for p in photos]

    pets_need = [p for p in owner.pets if _pet_needs_scrub(p)]
    visits_need = [v for p in owner.pets for v in p.visits if _visit_needs_scrub(v)]
    owner_need = _owner_needs_scrub(owner)

    if not owner_need and not pets_need and not visits_need and report.photo_count == 0:
        report.already_erased = True
        return report

    if not apply:
        if owner_need:
            report.owner_fields_cleared = [
                "name",
                "phone",
                "email",
                "notes",
                "address_area",
                "preferred_channel",
                "client_since",
            ]
        report.pets_renamed = [p.pet_id for p in pets_need]
        report.visits_scrubbed = [v.visit_id for v in visits_need]
        return report

    # 1) Photos first — files then rows (RESTRICT FKs + no orphan bytes).
    purged = purge_photos(session, photos, apply=True, backup_root=backup_root)
    report.photos_files_deleted = purged.files_deleted
    report.photos_rows_deleted = purged.rows_deleted
    report.backup_copies_deleted = purged.backup_copies_deleted
    session.flush()

    # 2) Scrub free text on visits, then pets, then owner (same transaction).
    for pet in owner.pets:
        for visit in pet.visits:
            if _visit_needs_scrub(visit):
                visit.what_surprised_me = None
                visit.pivot_reason = None
                report.visits_scrubbed.append(visit.visit_id)
        if _pet_needs_scrub(pet):
            pet.name = erased_pet_name(pet.pet_id)
            pet.temperament_notes = None
            pet.mobility_notes = None
            pet.vet_notes = None
            pet.fear_triggers = None
            report.pets_renamed.append(pet.pet_id)

    if owner_need:
        owner.name = erased_owner_name(owner.owner_id)
        owner.phone = None
        owner.email = None
        owner.notes = None
        owner.address_area = None
        owner.preferred_channel = None
        owner.client_since = None
        report.owner_fields_cleared = [
            "name",
            "phone",
            "email",
            "notes",
            "address_area",
            "preferred_channel",
            "client_since",
        ]

    session.flush()
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner-id", type=int, required=True)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="perform the erase (default: dry run)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        with session_scope() as session:
            backup_root = default_backup_root()
            report = erase_owner(session, args.owner_id, apply=args.apply, backup_root=backup_root)
    except LookupError as exc:
        print(exc)
        return 1

    print(f"owner_id={report.owner_id}")
    if report.already_erased:
        print("Already erased — nothing to do.")
        return 0

    print(f"photos matching: {report.photo_count}")
    for key in report.photo_keys:
        print(f"  {key}")
    if report.owner_fields_cleared:
        print(f"owner fields to clear: {', '.join(report.owner_fields_cleared)}")
    if report.pets_renamed:
        print(f"pets to anonymise: {report.pets_renamed}")
    if report.visits_scrubbed:
        print(f"visits free-text to clear: {report.visits_scrubbed}")

    if not args.apply:
        print("\nDry run - nothing changed. Re-run with --apply to erase.")
        return 0

    print(
        f"\nApplied: photos files={report.photos_files_deleted} "
        f"rows={report.photos_rows_deleted} "
        f"backup copies={report.backup_copies_deleted} (under {backup_root / 'photos'}); "
        f"pets={len(report.pets_renamed)}; visits={len(report.visits_scrubbed)}."
    )
    print("Live PII cleared. DB dumps still age out — see privacy.md.")
    if report.photo_keys:
        print("Remove the keys listed above from any other backup copy too (#221).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
