"""Dog onboarding schemas - create-or-get under an owner."""

from datetime import date

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
    """Response schema for dog lookup."""

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
