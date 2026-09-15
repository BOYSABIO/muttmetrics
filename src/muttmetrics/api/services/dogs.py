"""Dog create-or-get helper (scoped to owner)."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from muttmetrics.api.schemas.dogs import DogSearchItem
from muttmetrics.models import Breed, Dog, Owner


def normalize_dog_name(name: str) -> str:
    """Collapse whitespace; keep casing for storage."""
    return " ".join(name.split())


def create_or_get_dog(
    session: Session,
    *,
    owner_id: int,
    name: str,
    breed_id: int | None = None,
) -> tuple[Dog, bool]:
    """
    Return (dog, created).

    Raises ValueError for blank name.
    Raises LookupError with a clear message if owner (or breed) missing -
    the route turns those into 404.
    """
    cleaned = normalize_dog_name(name)
    if not cleaned:
        raise ValueError("Dog name must not be empty")

    if session.get(Owner, owner_id) is None:
        raise LookupError(f"Owner {owner_id} not found")

    if breed_id is not None and session.get(Breed, breed_id) is None:
        raise LookupError(f"Breed {breed_id} not found")

    existing = session.scalar(
        select(Dog).where(
            Dog.owner_id == owner_id,
            func.lower(Dog.name) == cleaned.lower(),
        )
    )
    if existing is not None:
        return existing, False

    dog = Dog(owner_id=owner_id, name=cleaned, breed_id=breed_id)
    session.add(dog)
    session.flush()
    return dog, True


def search_dogs(
    session: Session,
    *,
    q: str | None = None,
    limit: int = 50,
) -> list[DogSearchItem]:
    """
    Directory list: dogs with owner display name.

    Empty / blank q -> up to `limit` dogs (browse).
    Non-empty q -> dog.name ILIKE %q% (case-insensitive).
    """
    stmt = select(Dog).options(joinedload(Dog.owner)).order_by(Dog.name).limit(limit)
    cleaned = (q or "").strip()
    if cleaned:
        stmt = stmt.where(Dog.name.ilike(f"%{cleaned}%"))

    dogs = session.scalars(stmt).unique().all()
    return [
        DogSearchItem(
            dog_id=dog.dog_id,
            name=dog.name,
            owner_id=dog.owner_id,
            owner_name=dog.owner.name,
            last_visit_date=dog.last_visit_date,
        )
        for dog in dogs
    ]
