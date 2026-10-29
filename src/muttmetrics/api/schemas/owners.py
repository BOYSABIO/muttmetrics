"""Owner onboarding + Directory profile schemas."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class UpsertOwnerRequest(BaseModel):
    """Create an owner, or reuse one when name+phone clearly match (#187)."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "Anna Schmidt",
                    "phone": "+49 170 0000000",
                }
            ]
        }
    )

    name: str = Field(..., min_length=1, description="Client display name")
    phone: str | None = None
    email: str | None = None


class OwnerResponse(BaseModel):
    """Minimal response for create-or-get (capture path)."""

    model_config = ConfigDict(from_attributes=True)

    owner_id: int
    name: str
    phone: str | None = None
    email: str | None = None


class OwnerSearchItem(BaseModel):
    """One hit from GET /owners?q= (#191) — pick an existing client in capture."""

    model_config = ConfigDict(from_attributes=True)

    owner_id: int
    name: str
    phone: str | None = None
    dog_count: int = 0


class OwnerConflictCandidate(BaseModel):
    """Existing owner the SPA can offer when POST /owners hits a name clash."""

    owner_id: int
    name: str
    phone: str | None = None


class OwnerNameConflictDetail(BaseModel):
    """HTTP 409 body: do not guess — pick a candidate or supply a phone (#187)."""

    code: str = "owner_name_conflict"
    message: str
    candidates: list[OwnerConflictCandidate]


class OwnerDogItem(BaseModel):
    """Dog stub on an owner profile."""

    model_config = ConfigDict(from_attributes=True)

    dog_id: int
    name: str


class OwnerProfile(BaseModel):
    """Full owner profile for Directory (#131). Hand-entered + read-only derived."""

    model_config = ConfigDict(from_attributes=True)

    owner_id: int
    name: str
    phone: str | None = None
    email: str | None = None
    locale: str
    address_area: str | None = None
    preferred_channel: str | None = None
    client_since: date | None = None
    notes: str | None = None

    # Derived (ADR-001) — display only; never accept on PATCH (#132)
    visit_count: int | None = Field(default=None, description="Derived — display only")
    avg_rebook_days: Decimal | None = Field(default=None, description="Derived — display only")
    neglect_rate: Decimal | None = Field(default=None, description="Derived — display only")
    cancellation_rate: Decimal | None = Field(default=None, description="Derived — display only")
    no_show_count: int | None = Field(default=None, description="Derived — display only")
    avg_tip_pct: Decimal | None = Field(default=None, description="Derived — display only")
    lifetime_value: Decimal | None = Field(default=None, description="Derived — display only")
    reliability_score: Decimal | None = Field(default=None, description="Derived — display only")

    dogs: list[OwnerDogItem] = Field(default_factory=list)


class PatchOwnerRequest(BaseModel):
    """Partial owner update - hand entered fields only."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    phone: str | None = None
    email: str | None = None
    locale: str | None = None
    address_area: str | None = None
    preferred_channel: str | None = None
    client_since: date | None = None
    notes: str | None = None
