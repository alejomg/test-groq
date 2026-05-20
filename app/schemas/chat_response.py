from pydantic import BaseModel, Field
from uuid import UUID
from typing import List, Dict, Any, Optional
    
# 1. Individual response structure
class SingleChatResponse(BaseModel):
    message: str
    type: str

# 2. Metadata info (Generic to handle Groq, OpenAI, Anthropic, etc.)
class ChatResponseInfo(BaseModel):
    model: str
    # Optional and accepts Any structure (objects, dicts, or None)
    usage: Optional[Any] = Field(default=None, description="Provider-specific token usage")

# 3. The master envelope response
class ChatResponse(BaseModel):
    status: str = "success"
    uuid: UUID
    chat: List[SingleChatResponse]
    info: ChatResponseInfo
