"""Owner create-or-get, search, and Directory profile reads."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from muttmetrics.api.schemas.owners import (
    OwnerPetItem,
    OwnerProfile,
    OwnerSearchItem,
    PatchOwnerRequest,
)
from muttmetrics.api.services.patching import reject_null_for_required_columns
from muttmetrics.models import Owner, Pet, Visit
from muttmetrics.services.visit_eligibility import visit_counts_clause


class OwnerNameConflict(Exception):
    """Name already taken; route returns 409 with candidates (#187 / #191)."""

    def __init__(self, candidates: list[Owner]):
        self.candidates = candidates
        super().__init__("Owner name already exists")


def normalize_owner_name(name: str) -> str:
    """Collapse internal whitespace; strip ends. Keep original casing for storage."""
    return " ".join(name.split())


def normalize_phone(phone: str | None) -> str | None:
    """
    Digits only for comparison so '+49 170' and '+49170' match.

    Empty / None → None. We do not store this form; only compare with it.
    """
    if phone is None:
        return None
    digits = "".join(ch for ch in phone if ch.isdigit())
    return digits or None


def create_or_get_owner(
    session: Session,
    *,
    name: str,
    phone: str | None = None,
    email: str | None = None,
) -> tuple[Owner, bool]:
    """
    Return (owner, created).

    Match rules (#187):
    - No row with this normalized name → create (201).
    - Same name + phone digits match an existing row → reuse (200).
    - Same name + phone digits differ from all matches → create another (201).
    - Same name + no usable phone → raise OwnerNameConflict (409). Never silent-merge.
    """
    cleaned = normalize_owner_name(name)
    if not cleaned:
        raise ValueError("Owner name cannot be empty")

    matches = list(
        session.scalars(select(Owner).where(func.lower(Owner.name) == cleaned.lower())).all()
    )
    want_phone = normalize_phone(phone)

    if not matches:
        owner = Owner(name=cleaned, phone=phone, email=email)
        session.add(owner)
        session.flush()
        return owner, True

    if want_phone is not None:
        for existing in matches:
            if normalize_phone(existing.phone) == want_phone:
                return existing, False
        # Same display name, different phone → a different person.
        owner = Owner(name=cleaned, phone=phone, email=email)
        session.add(owner)
        session.flush()
        return owner, True

    raise OwnerNameConflict(matches)


def search_owners(
    session: Session,
    *,
    q: str | None = None,
    limit: int = 50,
) -> list[OwnerSearchItem]:
    """
    Directory / capture owner pick (#191).

    Empty / blank q → up to `limit` owners by name.
    Non-empty q → name ILIKE %q% (wildcards escaped, same as pet search).
    """
    pet_count_sq = (
        select(Pet.owner_id, func.count().label("pet_count")).group_by(Pet.owner_id).subquery()
    )

    stmt = (
        select(Owner, pet_count_sq.c.pet_count)
        .outerjoin(pet_count_sq, Owner.owner_id == pet_count_sq.c.owner_id)
        .order_by(Owner.name)
        .limit(limit)
    )
    cleaned = (q or "").strip()
    if cleaned:
        literal = cleaned.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        stmt = stmt.where(Owner.name.ilike(f"%{literal}%", escape="\\"))

    rows = session.execute(stmt).all()
    return [
        OwnerSearchItem(
            owner_id=owner.owner_id,
            name=owner.name,
            phone=owner.phone,
            pet_count=int(pet_count or 0),
        )
        for owner, pet_count in rows
    ]


def get_owner_profile(session: Session, *, owner_id: int) -> OwnerProfile:
    """
    Load one owner for Directory: contact fields + pet list.

    Raises LookupError if owner_id missing (route -> 404).
    """
    owner = session.scalar(
        select(Owner).options(selectinload(Owner.pets)).where(Owner.owner_id == owner_id)
    )
    if owner is None:
        raise LookupError(f"Owner {owner_id} not found")

    pets = sorted(owner.pets, key=lambda d: d.name.lower())
    # Live total across all pets — derived owner.visit_count can lag / be null.
    visit_count = session.scalar(
        select(func.count())
        .select_from(Visit)
        .where(Visit.owner_id == owner_id, visit_counts_clause())
    )
    profile = OwnerProfile.model_validate(owner)
    return profile.model_copy(
        update={
            "pets": [OwnerPetItem.model_validate(d) for d in pets],
            "visit_count": int(visit_count or 0),
        }
    )


def patch_owner(
    session: Session,
    *,
    owner_id: int,
    body: PatchOwnerRequest,
) -> OwnerProfile:
    """
    Apply a partial owner update. Only fields present in the JSON are touched.

    Raises LookupError if owner missing
    Raises ValueError if name is sent but blank.
    """
    owner = session.get(Owner, owner_id)
    if owner is None:
        raise LookupError(f"Owner {owner_id} not found")

    updates = body.model_dump(exclude_unset=True)
    reject_null_for_required_columns(Owner, updates)

    if "name" in updates:
        cleaned = normalize_owner_name(updates["name"] or "")
        if not cleaned:
            raise ValueError("owner name cannot be empty")
        updates["name"] = cleaned

    for key, value in updates.items():
        setattr(owner, key, value)

    session.flush()
    return get_owner_profile(session, owner_id=owner_id)
