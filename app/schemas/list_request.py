from pydantic import BaseModel, Field

class ListRequest(BaseModel):
    topic: str = Field(..., min_length=3, example="Quantum computing")
    num_articles: int = Field(..., example=3)
