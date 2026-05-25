from pydantic import BaseModel, Field
from uuid import UUID


class DialogRequest(BaseModel):
    duuid: UUID | None = Field(None, description="Optional, unique identifier for the dialog")
    message: str = Field(..., min_length=3, description="Message sent by the user", example="Tell me one interesting fact about space in one sentence.")
