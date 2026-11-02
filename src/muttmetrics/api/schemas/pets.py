"""Pet onboarding + Directory profile schemas."""

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from muttmetrics.api.schemas.add_ons import AddOnSummary
from muttmetrics.species import DEFAULT_SPECIES

SpeciesLiteral = Literal["dog", "cat"]


class UpsertPetRequest(BaseModel):
    """Find a pet by owner + name + species, or create one."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "owner_id": 1,
                    "name": "Bella",
                    "species": "dog",
                    "breed_id": 1,
                }
            ]
        }
    )

    owner_id: int = Field(..., description="Existing owner primary key")
    name: str = Field(..., min_length=1, description="Pet call name")
    species: SpeciesLiteral = Field(
        default=DEFAULT_SPECIES,  # type: ignore[assignment]
        description="dog or cat (ADR-004); default dog",
    )
    breed_id: int | None = Field(
        default=None, description="Optional breed.breed_id from seed catalog"
    )


class PetResponse(BaseModel):
    """Minimal response for create-or-get (capture path)."""

    model_config = ConfigDict(from_attributes=True)

    pet_id: int
    owner_id: int
    name: str
    species: SpeciesLiteral
    breed_id: int | None = None


class PetSearchItem(BaseModel):
    """One row in the directory list (pet + owner label)"""

    model_config = ConfigDict(from_attributes=True)

    pet_id: int
    name: str
    species: SpeciesLiteral
    owner_id: int
    owner_name: str
    last_visit_date: date | None = None


class OwnerSummary(BaseModel):
    """Owner stub nested on a pet profile (not the full owner page)."""

    model_config = ConfigDict(from_attributes=True)

    owner_id: int
    name: str
    phone: str | None = None
    email: str | None = None


class VisitSummary(BaseModel):
    """Recent visit row for a pet profile (facts only — not analytics)."""

    model_config = ConfigDict(from_attributes=True)

    visit_id: int
    visit_date: date
    actual_minutes: int
    condition_score: int | None = None
    status: str | None = None
    add_ons: list[AddOnSummary] = Field(default_factory=list)


class PetProfile(BaseModel):
    """Full pet profile for Directory (#131). Hand-entered + read-only derived."""

    model_config = ConfigDict(from_attributes=True)

    pet_id: int
    owner_id: int
    name: str
    species: SpeciesLiteral
    breed_id: int | None = None
    breed_secondary_id: int | None = None
    sex: str | None = None
    date_of_birth: date | None = None
    weight_kg: Decimal | None = None

    coat_type: str | None = None
    hair_or_fur: str | None = None
    coat_density: str | None = None
    undercoat: bool | None = None
    sheds: bool | None = None

    handling_score: int | None = None
    fear_triggers: list[str] | None = None
    muzzle_required: bool | None = None
    two_person_job: bool | None = None
    temperament_notes: str | None = None

    skin_conditions: list[str] | None = None
    senior_flag: bool | None = None
    mobility_notes: str | None = None
    vet_notes: str | None = None

    # Derived (ADR-001) — display only; never accept on PATCH (#132)
    size_band: str | None = Field(default=None, description="Derived — display only")
    visit_count: int | None = Field(default=None, description="Derived — display only")
    avg_duration_min: Decimal | None = Field(default=None, description="Derived — display only")
    duration_stddev_min: Decimal | None = Field(default=None, description="Derived — display only")
    typical_interval_days: Decimal | None = Field(
        default=None, description="Derived — display only"
    )
    last_visit_date: date | None = Field(default=None, description="Derived — display only")
    next_due_date: date | None = Field(default=None, description="Derived — display only")

    avatar_photo_id: int | None = Field(
        default=None,
        description="Newest profile photo, else newest intake; for Directory avatar",
    )

    owner: OwnerSummary
    recent_visits: list[VisitSummary] = Field(default_factory=list)


class PatchPetRequest(BaseModel):
    """Partial pet update - hand entered fields only."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    species: SpeciesLiteral | None = None
    breed_id: int | None = None
    breed_secondary_id: int | None = None
    sex: str | None = None
    date_of_birth: date | None = None
    # > 0, and a ceiling that catches grams typed into a kg field (7500 -> 422).
    weight_kg: Decimal | None = Field(default=None, gt=0, le=150)

    coat_type: str | None = None
    hair_or_fur: str | None = None
    coat_density: str | None = None
    undercoat: bool | None = None
    sheds: bool | None = None

    handling_score: int | None = Field(default=None, ge=1, le=5)
    fear_triggers: list[str] | None = None
    muzzle_required: bool | None = None
    two_person_job: bool | None = None
    temperament_notes: str | None = None

    skin_conditions: list[str] | None = None
    senior_flag: bool | None = None
    mobility_notes: str | None = None
    vet_notes: str | None = None
