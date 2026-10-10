"""Dog onboarding + Directory profile schemas."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class UpsertDogRequest(BaseModel):
    """Find a dog by owner + name, or create one."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "owner_id": 1,
                    "name": "Bella",
                    "breed_id": 1,
                }
            ]
        }
    )

    owner_id: int = Field(..., description="Existing owner primary key")
    name: str = Field(..., min_length=1, description="Dog call name")
    breed_id: int | None = Field(
        default=None, description="Optional breed.breed_id from seed catalog"
    )


class DogResponse(BaseModel):
    """Minimal response for create-or-get (capture path)."""

    model_config = ConfigDict(from_attributes=True)

    dog_id: int
    owner_id: int
    name: str
    breed_id: int | None = None


class DogSearchItem(BaseModel):
    """One row in the directory list (dog + owner label)"""

    model_config = ConfigDict(from_attributes=True)

    dog_id: int
    name: str
    owner_id: int
    owner_name: str
    last_visit_date: date | None = None


class OwnerSummary(BaseModel):
    """Owner stub nested on a dog profile (not the full owner page)."""

    model_config = ConfigDict(from_attributes=True)

    owner_id: int
    name: str
    phone: str | None = None
    email: str | None = None


class VisitSummary(BaseModel):
    """Recent visit row for a dog profile (facts only — not analytics)."""

    model_config = ConfigDict(from_attributes=True)

    visit_id: int
    visit_date: date
    actual_minutes: int
    condition_score: int | None = None
    status: str | None = None


class DogProfile(BaseModel):
    """Full dog profile for Directory (#131). Hand-entered + read-only derived."""

    model_config = ConfigDict(from_attributes=True)

    dog_id: int
    owner_id: int
    name: str
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


class PatchDogRequest(BaseModel):
    """Partial dog update - hand entered fields only."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = None
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

    handling_score: int | None = Field(default=None, ge=1, le=5)
    fear_triggers: list[str] | None = None
    muzzle_required: bool | None = None
    two_person_job: bool | None = None
    temperament_notes: str | None = None

    skin_conditions: list[str] | None = None
    senior_flag: bool | None = None
    mobility_notes: str | None = None
    vet_notes: str | None = None
