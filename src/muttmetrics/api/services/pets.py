"""Pet create-or-get, search, and Directory profile reads."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from muttmetrics.api.schemas.pets import (
    OwnerSummary,
    PatchPetRequest,
    PetProfile,
    PetSearchItem,
)
from muttmetrics.api.services.patching import reject_null_for_required_columns
from muttmetrics.api.services.visits import visit_to_summary
from muttmetrics.models import Breed, Owner, Pet, Photo, Visit, VisitAddOn
from muttmetrics.priors.size import size_band_from_weight
from muttmetrics.services.visit_eligibility import visit_counts_clause
from muttmetrics.species import ALLOWED_SPECIES, DEFAULT_SPECIES


def normalize_pet_name(name: str) -> str:
    """Collapse whitespace; keep casing for storage."""
    return " ".join(name.split())


def ensure_breed_matches_species(
    session: Session,
    breed_id: int | None,
    species: str,
) -> None:
    """Raise LookupError if missing, ValueError if species mismatch."""
    if breed_id is None:
        return
    breed = session.get(Breed, breed_id)
    if breed is None:
        raise LookupError(f"Breed {breed_id} not found")
    if breed.species != species:
        raise ValueError(f"Breed {breed_id} is species {breed.species!r}, pet is {species!r}")


def create_or_get_pet(
    session: Session,
    *,
    owner_id: int,
    name: str,
    species: str = DEFAULT_SPECIES,
    breed_id: int | None = None,
) -> tuple[Pet, bool]:
    """
    Return (pet, created). Match is owner + name + species.

    Raises ValueError for blank name or breed/species mismatch.
    Raises LookupError with a clear message if owner (or breed) missing -
    the route turns those into 404.
    """
    cleaned = normalize_pet_name(name)
    if not cleaned:
        raise ValueError("Pet name must not be empty")
    if species not in ALLOWED_SPECIES:
        raise ValueError(f"species must be one of {ALLOWED_SPECIES}")

    if session.get(Owner, owner_id) is None:
        raise LookupError(f"Owner {owner_id} not found")

    ensure_breed_matches_species(session, breed_id, species)

    existing = session.scalar(
        select(Pet).where(
            Pet.owner_id == owner_id,
            func.lower(Pet.name) == cleaned.lower(),
            Pet.species == species,
        )
    )
    if existing is not None:
        return existing, False

    pet = Pet(owner_id=owner_id, name=cleaned, species=species, breed_id=breed_id)
    session.add(pet)
    session.flush()
    return pet, True


def search_pets(
    session: Session,
    *,
    q: str | None = None,
    limit: int = 50,
) -> list[PetSearchItem]:
    """
    Directory list: pets with owner display name.

    Empty / blank q -> up to `limit` pets (browse).
    Non-empty q -> pet.name ILIKE %q% (case-insensitive).
    last_visit_date is live from visit rows (eligible statuses only), not the
    stored pet.last_visit_date column (#171)
    """
    last_visit_sq = (
        select(
            Visit.pet_id.label("pet_id"),
            func.max(Visit.visit_date).label("last_visit_date"),
        )
        .where(visit_counts_clause())
        .group_by(Visit.pet_id)
        .subquery()
    )

    stmt = (
        select(Pet, last_visit_sq.c.last_visit_date)
        .options(joinedload(Pet.owner))
        .outerjoin(last_visit_sq, Pet.pet_id == last_visit_sq.c.pet_id)
        .order_by(Pet.name)
        .limit(limit)
    )
    cleaned = (q or "").strip()
    if cleaned:
        # Escape LIKE wildcards so "%" or "_" in a search match literally (#180).
        literal = cleaned.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        stmt = stmt.where(Pet.name.ilike(f"%{literal}%", escape="\\"))

    rows = session.execute(stmt).unique().all()
    return [
        PetSearchItem(
            pet_id=pet.pet_id,
            name=pet.name,
            species=pet.species,  # type: ignore[arg-type]
            owner_id=pet.owner_id,
            owner_name=pet.owner.name,
            last_visit_date=last_visit_date,
        )
        for pet, last_visit_date in rows
    ]


def get_pet_profile(
    session: Session,
    *,
    pet_id: int,
    recent_limit: int = 10,
) -> PetProfile:
    """
    Load one pet for Directory: hand-entered fields, owner stub, recent visits.

    Raises LookupError if pet_id missing (route -> 404).
    """
    pet = session.scalar(select(Pet).options(joinedload(Pet.owner)).where(Pet.pet_id == pet_id))
    if pet is None:
        raise LookupError(f"Pet {pet_id} not found")

    limit = max(0, min(recent_limit, 50))
    visits = session.scalars(
        select(Visit)
        .options(selectinload(Visit.visit_add_ons).selectinload(VisitAddOn.add_on))
        .where(Visit.pet_id == pet_id)
        .order_by(Visit.visit_date.desc(), Visit.visit_id.desc())
        .limit(limit)
    ).all()

    # Live count from visit rows — derived pet.visit_count can lag / be null
    # when recompute hasn't run (Directory should still show the truth).
    visit_count = session.scalar(
        select(func.count()).select_from(Visit).where(Visit.pet_id == pet_id, visit_counts_clause())
    )
    last_visit_date = session.scalar(
        select(func.max(Visit.visit_date)).where(
            Visit.pet_id == pet_id,
            visit_counts_clause(),
        )
    )

    avatar_photo_id = session.scalar(
        select(Photo.photo_id)
        .where(Photo.pet_id == pet_id, Photo.kind == "profile")
        .order_by(Photo.photo_id.desc())
        .limit(1)
    )
    if avatar_photo_id is None:
        avatar_photo_id = session.scalar(
            select(Photo.photo_id)
            .where(Photo.pet_id == pet_id, Photo.kind == "intake")
            .order_by(Photo.photo_id.desc())
            .limit(1)
        )

    profile = PetProfile.model_validate(pet)
    return profile.model_copy(
        update={
            "owner": OwnerSummary.model_validate(pet.owner),
            "recent_visits": [visit_to_summary(v) for v in visits],
            "avatar_photo_id": avatar_photo_id,
            "visit_count": int(visit_count or 0),
            "last_visit_date": last_visit_date,
            "size_band": size_band_from_weight(pet.weight_kg, pet.species) or pet.size_band,
        }
    )


def patch_pet(
    session: Session,
    *,
    pet_id: int,
    body: PatchPetRequest,
) -> PetProfile:
    """
    Apply a partial pet update. Only fields present in the JSON are touched.

    Raises LookupError if pet or breed id missing
    Raises ValueError if name is sent but blank, or breed/species mismatch.
    """
    pet = session.get(Pet, pet_id)

    if pet is None:
        raise LookupError(f"Pet {pet_id} not found")

    updates = body.model_dump(exclude_unset=True)
    reject_null_for_required_columns(Pet, updates)

    if "name" in updates:
        cleaned = normalize_pet_name(updates["name"] or "")
        if not cleaned:
            raise ValueError("Pet name must not be empty")
        updates["name"] = cleaned

    if "species" in updates and updates["species"] not in ALLOWED_SPECIES:
        raise ValueError(f"species must be one of {ALLOWED_SPECIES}")

    new_species = updates.get("species", pet.species)
    for breed_key in ("breed_id", "breed_secondary_id"):
        breed_id = updates[breed_key] if breed_key in updates else getattr(pet, breed_key)
        ensure_breed_matches_species(session, breed_id, new_species)

    for key, value in updates.items():
        setattr(pet, key, value)

    # Write-through: size_band is derived from weight, never from the client.
    if "weight_kg" in updates or "species" in updates:
        w = pet.weight_kg
        pet.size_band = size_band_from_weight(
            float(w) if w is not None else None,
            pet.species,
        )

    session.flush()
    return get_pet_profile(session, pet_id=pet_id)
