"""Owner create-or-get helper."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

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
