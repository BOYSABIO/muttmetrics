"""ops/client_export.py + ops/client_erase.py (#195)."""

from __future__ import annotations

import json
import os
import stat
from datetime import date
from pathlib import Path

import pytest
from ops.client_erase import erase_owner, erased_owner_name, erased_pet_name
from ops.client_export import export_owner
from sqlalchemy.orm import Session

from muttmetrics.media import storage
from muttmetrics.models import Owner, Pet, Photo, Visit


@pytest.fixture(autouse=True)
def photo_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("PHOTO_ROOT", str(tmp_path / "photos"))
    from muttmetrics.config import get_settings

    get_settings.cache_clear()
    root = tmp_path / "photos"
    root.mkdir()
    return root


def _owner_tree(
    db_session: Session,
    *,
    name: str,
    pet_name: str,
    with_photo: bool = False,
) -> tuple[Owner, Pet, Visit]:
    owner = Owner(
        name=name,
        phone="+49000",
        email=f"{name.replace(' ', '').lower()}@example.test",
        notes="private note",
        address_area="Nordend",
        preferred_channel="whatsapp",
        client_since=date(2024, 1, 1),
    )
    db_session.add(owner)
    db_session.flush()
    pet = Pet(
        owner_id=owner.owner_id,
        name=pet_name,
        species="dog",
        temperament_notes="nervous around men",
        vet_notes="allergy",
        fear_triggers=["vacuum"],
    )
    db_session.add(pet)
    db_session.flush()
    visit = Visit(
        pet_id=pet.pet_id,
        owner_id=owner.owner_id,
        visit_date=date(2026, 3, 2),
        actual_minutes=60,
        final_price=45,
        what_surprised_me="Owner mentioned neighbour Anna",
        pivot_reason="too matted",
    )
    db_session.add(visit)
    db_session.flush()
    if with_photo:
        key = storage.build_key()
        storage.write_bytes(key, b"fake-jpeg-bytes")
        photo = Photo(
            pet_id=pet.pet_id,
            visit_id=visit.visit_id,
            kind="intake",
            storage_key=key,
            content_type="image/jpeg",
            byte_size=len(b"fake-jpeg-bytes"),
            sha256="a" * 64,
        )
        db_session.add(photo)
        db_session.flush()
    return owner, pet, visit


def test_export_contains_only_that_owner(db_session: Session, tmp_path: Path) -> None:
    a, pet_a, visit_a = _owner_tree(db_session, name="Syn Export A", pet_name="Syn Dog A")
    b, _, _ = _owner_tree(db_session, name="Syn Export B", pet_name="Syn Dog B")

    dest = export_owner(db_session, a.owner_id, export_root=tmp_path / "exports")
    payload = json.loads((dest / "owner.json").read_text(encoding="utf-8"))

    assert payload["owner_id"] == a.owner_id
    assert payload["name"] == "Syn Export A"
    assert payload["pets"][0]["name"] == "Syn Dog A"
    assert payload["pets"][0]["visits"][0]["visit_id"] == visit_a.visit_id
    assert all(p["owner_id"] == a.owner_id for pet in payload["pets"] for p in pet["visits"])
    dumped = json.dumps(payload)
    assert "Syn Export B" not in dumped
    assert str(b.owner_id) not in dumped or payload["owner_id"] != b.owner_id
    assert b.name not in dumped


def test_export_copies_photos(db_session: Session, tmp_path: Path, photo_root: Path) -> None:
    owner, _, _ = _owner_tree(
        db_session, name="Syn Photo Export", pet_name="Syn Photo Dog", with_photo=True
    )
    dest = export_owner(db_session, owner.owner_id, export_root=tmp_path / "exports")
    files = list((dest / "photos").glob("photo-*.jpg"))
    assert len(files) == 1
    assert files[0].read_bytes() == b"fake-jpeg-bytes"
    manifest = json.loads((dest / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["photos_copied"] == 1
    assert manifest["photos_missing"] == []


def test_erase_scrubs_pii_keeps_visits_and_spares_others(
    db_session: Session, photo_root: Path
) -> None:
    a, pet_a, visit_a = _owner_tree(
        db_session, name="Syn Erase A", pet_name="Syn Erase Dog", with_photo=True
    )
    b, pet_b, visit_b = _owner_tree(db_session, name="Syn Erase B", pet_name="Syn Keep Dog")

    report = erase_owner(db_session, a.owner_id, apply=True)
    db_session.refresh(a)
    db_session.refresh(pet_a)
    db_session.refresh(visit_a)
    db_session.refresh(b)
    db_session.refresh(pet_b)
    db_session.refresh(visit_b)

    assert report.photos_rows_deleted == 1
    assert a.name == erased_owner_name(a.owner_id)
    assert a.phone is None and a.email is None and a.notes is None
    assert a.address_area is None and a.preferred_channel is None
    assert a.client_since is None
    assert pet_a.name == erased_pet_name(pet_a.pet_id)
    assert pet_a.temperament_notes is None and pet_a.vet_notes is None
    assert pet_a.fear_triggers is None
    assert visit_a.what_surprised_me is None and visit_a.pivot_reason is None
    assert visit_a.actual_minutes == 60
    assert visit_a.final_price == 45
    assert visit_a.visit_date == date(2026, 3, 2)

    assert b.name == "Syn Erase B"
    assert b.phone == "+49000"
    assert pet_b.name == "Syn Keep Dog"
    assert visit_b.what_surprised_me is not None

    files = [p for p in photo_root.rglob("*") if p.is_file()]
    assert files == []


def test_erase_dry_run_writes_nothing(db_session: Session) -> None:
    owner, pet, visit = _owner_tree(db_session, name="Syn Dry Erase", pet_name="Syn Dry Dog")
    erase_owner(db_session, owner.owner_id, apply=False)
    db_session.refresh(owner)
    db_session.refresh(pet)
    db_session.refresh(visit)
    assert owner.name == "Syn Dry Erase"
    assert owner.phone == "+49000"
    assert pet.temperament_notes == "nervous around men"
    assert visit.what_surprised_me is not None


def test_erase_is_idempotent(db_session: Session) -> None:
    owner, _, _ = _owner_tree(db_session, name="Syn Idem", pet_name="Syn Idem Dog")
    erase_owner(db_session, owner.owner_id, apply=True)
    again = erase_owner(db_session, owner.owner_id, apply=True)
    assert again.already_erased is True
    assert again.photo_count == 0
    assert again.owner_fields_cleared == []
    assert again.pets_renamed == []
    assert again.visits_scrubbed == []


def test_erase_missing_owner(db_session: Session) -> None:
    with pytest.raises(LookupError, match="No owner"):
        erase_owner(db_session, 9_999_999, apply=False)


# --- 0.6.7: backup copies and owner-only files --------------------------------

posix_only = pytest.mark.skipif(os.name != "posix", reason="file modes are POSIX-only")


def _backup_copy(backup_root: Path, key: str) -> Path:
    """What ops/backup.py leaves behind: the same relative key under photos/."""
    copy = backup_root / "photos" / key
    copy.parent.mkdir(parents=True, exist_ok=True)
    copy.write_bytes(b"fake-jpeg-bytes")
    return copy


def test_erase_also_removes_the_backup_copies(db_session: Session, tmp_path: Path) -> None:
    a, pet_a, _ = _owner_tree(db_session, name="Syn Bk A", pet_name="Syn Bk Dog", with_photo=True)
    b, pet_b, _ = _owner_tree(db_session, name="Syn Bk B", pet_name="Syn Bk Keep", with_photo=True)
    backup_root = tmp_path / "backups"
    key_a = pet_a.photos[0].storage_key
    key_b = pet_b.photos[0].storage_key
    copy_a = _backup_copy(backup_root, key_a)
    copy_b = _backup_copy(backup_root, key_b)

    dry = erase_owner(db_session, a.owner_id, apply=False, backup_root=backup_root)
    assert dry.photo_keys == [key_a]  # listed before anything is deleted
    assert copy_a.exists()

    report = erase_owner(db_session, a.owner_id, apply=True, backup_root=backup_root)
    assert report.photo_keys == [key_a]
    assert report.backup_copies_deleted == 1
    assert not copy_a.exists()
    assert copy_b.exists()  # another client's copy is untouched


def test_erase_without_a_backup_copy_still_succeeds(db_session: Session, tmp_path: Path) -> None:
    owner, _, _ = _owner_tree(
        db_session, name="Syn No Bk", pet_name="Syn No Bk Dog", with_photo=True
    )
    report = erase_owner(db_session, owner.owner_id, apply=True, backup_root=tmp_path / "none")
    assert report.photos_rows_deleted == 1
    assert report.backup_copies_deleted == 0


def test_backup_copy_path_refuses_to_leave_the_folder(tmp_path: Path) -> None:
    from ops.photo_purge import backup_copy_path

    assert (
        backup_copy_path(tmp_path, "2026/11/abc.jpg")
        == (tmp_path / "photos" / "2026" / "11" / "abc.jpg").resolve()
    )
    with pytest.raises(ValueError, match="escapes"):
        backup_copy_path(tmp_path, "../dumps/x.dump")


@posix_only
def test_export_is_owner_only(db_session: Session, tmp_path: Path, photo_root: Path) -> None:
    owner, pet, _ = _owner_tree(
        db_session, name="Syn Mode", pet_name="Syn Mode Dog", with_photo=True
    )
    # A photo written world-readable, as the API did before UMask=0077
    storage.key_to_path(pet.photos[0].storage_key).chmod(0o644)

    dest = export_owner(db_session, owner.owner_id, export_root=tmp_path / "exports")

    assert stat.S_IMODE(dest.stat().st_mode) == 0o700
    assert stat.S_IMODE((dest / "photos").stat().st_mode) == 0o700
    for f in dest.rglob("*"):
        if f.is_file():
            assert stat.S_IMODE(f.stat().st_mode) == 0o600, f.name
