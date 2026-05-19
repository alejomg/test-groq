from pydantic import BaseModel, Field
from uuid import UUID

class ChatRequest(BaseModel):
    uuid: UUID | None = Field(None, description="Optional unique identifier for the chat")
    prompt: str = Field(..., min_length=3, example="Tell me one interesting fact about space in one sentence.")
