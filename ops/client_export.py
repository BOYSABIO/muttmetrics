"""Art. 15 access export for one owner (#195).

Read-only. Writes a folder under gitignored data/exports/ with JSON of the
owner, pets, visits (incl. add-on ids) and copies of live photo files.

    python ops/client_export.py --owner-id 42

Run export *before* erase if the client asked for a copy of their data.
Never commit the export folder.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from muttmetrics.db.session import session_scope
from muttmetrics.media import storage
from muttmetrics.models import Owner, Pet, Visit

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPORT_ROOT = REPO_ROOT / "data" / "exports"


def _jsonable(value: Any) -> Any:
    """Turn SQLAlchemy/Python values into JSON-safe ones."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    return str(value)


def owner_payload(owner: Owner) -> dict[str, Any]:
    """Serializable snapshot of one owner subtree (no other owners)."""
    pets_out: list[dict[str, Any]] = []
    for pet in owner.pets:
        visits_out: list[dict[str, Any]] = []
        for visit in pet.visits:
            visits_out.append(
                {
                    "visit_id": visit.visit_id,
                    "pet_id": visit.pet_id,
                    "owner_id": visit.owner_id,
                    "visit_date": _jsonable(visit.visit_date),
                    "created_at": _jsonable(visit.created_at),
                    "booked_service_id": visit.booked_service_id,
                    "actual_service_id": visit.actual_service_id,
                    "actual_minutes": visit.actual_minutes,
                    "quoted_price": _jsonable(visit.quoted_price),
                    "final_price": _jsonable(visit.final_price),
                    "tip": _jsonable(visit.tip),
                    "condition_score": visit.condition_score,
                    "pivoted": visit.pivoted,
                    "pivot_reason": visit.pivot_reason,
                    "shaved_down": visit.shaved_down,
                    "what_surprised_me": visit.what_surprised_me,
                    "behaviour_this_visit": visit.behaviour_this_visit,
                    "status": visit.status,
                    "predicted_min_p50": visit.predicted_min_p50,
                    "predicted_min_p90": visit.predicted_min_p90,
                    "days_since_last": visit.days_since_last,
                    "add_on_ids": [link.add_on_id for link in visit.visit_add_ons],
                }
            )
        photos_out = [
            {
                "photo_id": photo.photo_id,
                "kind": photo.kind,
                "visit_id": photo.visit_id,
                "byte_size": photo.byte_size,
                "storage_key": photo.storage_key,
            }
            for photo in pet.photos
        ]
        pets_out.append(
            {
                "pet_id": pet.pet_id,
                "name": pet.name,
                "species": pet.species,
                "breed_id": pet.breed_id,
                "breed_secondary_id": pet.breed_secondary_id,
                "sex": pet.sex,
                "date_of_birth": _jsonable(pet.date_of_birth),
                "weight_kg": _jsonable(pet.weight_kg),
                "coat_type": pet.coat_type,
                "temperament_notes": pet.temperament_notes,
                "mobility_notes": pet.mobility_notes,
                "vet_notes": pet.vet_notes,
                "fear_triggers": pet.fear_triggers,
                "visits": visits_out,
                "photos": photos_out,
            }
        )
    return {
        "owner_id": owner.owner_id,
        "name": owner.name,
        "phone": owner.phone,
        "email": owner.email,
        "locale": owner.locale,
        "address_area": owner.address_area,
        "preferred_channel": owner.preferred_channel,
        "client_since": _jsonable(owner.client_since),
        "notes": owner.notes,
        "pets": pets_out,
    }


def load_owner_tree(session: Session, owner_id: int) -> Owner | None:
    """Owner with pets, visits (+ add-ons), and photos eagerly loaded."""
    stmt = (
        select(Owner)
        .where(Owner.owner_id == owner_id)
        .options(
            selectinload(Owner.pets).selectinload(Pet.visits).selectinload(Visit.visit_add_ons),
            selectinload(Owner.pets).selectinload(Pet.photos),
        )
    )
    return session.scalars(stmt).first()


def export_owner(
    session: Session,
    owner_id: int,
    *,
    export_root: Path = DEFAULT_EXPORT_ROOT,
) -> Path:
    """Write one export folder. Raises LookupError if the owner is missing."""
    owner = load_owner_tree(session, owner_id)
    if owner is None:
        raise LookupError(f"No owner with owner_id={owner_id}")

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = export_root / f"owner-{owner_id}-{stamp}"
    dest.mkdir(parents=True, exist_ok=False)
    photos_dir = dest / "photos"
    photos_dir.mkdir()
    # Client data: owner-only whatever the caller's umask (no effect on Windows,
    # where the folder's ACL decides).
    dest.chmod(0o700)
    photos_dir.chmod(0o700)

    payload = owner_payload(owner)
    (dest / "owner.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (dest / "owner.json").chmod(0o600)

    missing: list[str] = []
    copied = 0
    for pet in owner.pets:
        for photo in pet.photos:
            src_name = f"photo-{photo.photo_id}-{photo.kind}.jpg"
            target = photos_dir / src_name
            try:
                src = storage.key_to_path(photo.storage_key)
                if not src.is_file():
                    missing.append(photo.storage_key)
                    continue
                shutil.copy2(src, target)
                target.chmod(0o600)  # copy2 also copies the source's mode
                copied += 1
            except (OSError, ValueError, FileNotFoundError):
                missing.append(photo.storage_key)

    manifest = {
        "owner_id": owner_id,
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "photos_copied": copied,
        "photos_missing": missing,
    }
    (dest / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    (dest / "manifest.json").chmod(0o600)
    return dest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner-id", type=int, required=True)
    parser.add_argument(
        "--export-root",
        type=Path,
        default=DEFAULT_EXPORT_ROOT,
        help="parent directory for export folders (default: data/exports)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        with session_scope() as session:
            dest = export_owner(session, args.owner_id, export_root=args.export_root)
    except LookupError as exc:
        print(exc)
        return 1
    print(f"Export written to {dest}")
    print("This folder is gitignored — do not commit it. See docs/runbooks/client-requests.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
