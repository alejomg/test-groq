from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=3, example="Dime un dato curioso sobre el espacio en una frase.")
