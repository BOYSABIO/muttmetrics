"""Photo response schemas - metadata only; bytes come from GET /photos/{id}."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class PhotoResponse(BaseModel):
    """What the SPA needs to show and fetch a photo."""

    model_config = ConfigDict(from_attributes=True)

    photo_id: int
    dog_id: int
    visit_id: int | None = None
    kind: Literal["intake", "after", "profile"]
    content_type: str
    byte_size: int
    created_at: datetime
