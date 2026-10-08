"""Owner create-or-get and Directory profile reads."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from muttmetrics.api.schemas.owners import OwnerDogItem, OwnerProfile, PatchOwnerRequest
from muttmetrics.models import Owner


def normalize_owner_name(name: str) -> str:
    """Collapse internal whitespace; strip ends. Keep original casing for storage."""
    return " ".join(name.split())


def create_or_get_owner(
    session: Session,
    *,
    name: str,
    phone: str | None = None,
    email: str | None = None,
) -> tuple[Owner, bool]:
    """
    Return (owner, created).

    Lookup is case-insensitive on normalized name. New rows store the normalized
    display name; phone/email are set only when creating (not overwritten on get).
    """
    cleaned = normalize_owner_name(name)
    if not cleaned:
        raise ValueError("Owner name cannot be empty")

    existing = session.scalar(select(Owner).where(func.lower(Owner.name) == cleaned.lower()))
    if existing is not None:
        return existing, False

    owner = Owner(name=cleaned, phone=phone, email=email)
    session.add(owner)
    session.flush()
    return owner, True


def get_owner_profile(session: Session, *, owner_id: int) -> OwnerProfile:
    """
    Load one owner for Directory: contact fields + dog list.

    Raises LookupError if owner_id missing (route -> 404).
    """
    owner = session.scalar(
        select(Owner).options(selectinload(Owner.dogs)).where(Owner.owner_id == owner_id)
    )
    if owner is None:
        raise LookupError(f"Owner {owner_id} not found")

    dogs = sorted(owner.dogs, key=lambda d: d.name.lower())
    profile = OwnerProfile.model_validate(owner)
    return profile.model_copy(update={"dogs": [OwnerDogItem.model_validate(d) for d in dogs]})


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

    if "name" in updates:
        cleaned = normalize_owner_name(updates["name"] or "")
        if not cleaned:
            raise ValueError("owner name cannot be empty")
        updates["name"] = cleaned

    for key, value in updates.items():
        setattr(owner, key, value)

    session.flush()
    return get_owner_profile(session, owner_id=owner_id)
