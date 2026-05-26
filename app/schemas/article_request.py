from pydantic import BaseModel, Field


class ArticleRequest(BaseModel):
    topic: str = Field(..., min_length=3, example="Quantum computing")
    num_articles: int = Field(..., example=2)
