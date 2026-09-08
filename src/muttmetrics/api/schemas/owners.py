"""Owner onboarding schemas - minimal create-or-get contract."""

from pydantic import BaseModel, ConfigDict, Field


class UpsertOwnerRequest(BaseModel):
    """Find an owner by name or create one."""

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
    """Response schema for owner lookup."""

    model_config = ConfigDict(from_attributes=True)

    owner_id: int
    name: str
    phone: str | None = None
    email: str | None = None
