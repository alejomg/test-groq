from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

### Dialog Responses ###
class DialogBasicResponse(BaseResponse):
    id: int
    duuid: UUID


class DialogResponse(DialogBasicResponse):
    created_date: datetime
    updated_date: datetime


class DialogSimpleMessage(BaseResponse):
    text: str
    type: str


class DialogDetailResponse(DialogResponse):
    messages: list[DialogSimpleMessage] = Field(default_factory=list)


class DialogMetadata(BaseResponse):
    model: str
    # Optional and accepts Any structure (objects, dicts, or None)
    usage: Optional[Any] = Field(default=None, description="Provider-specific token usage")


class DialogProcessedResponse(DialogBasicResponse):
    dialog: list[DialogSimpleMessage]
    metadata: DialogMetadata
