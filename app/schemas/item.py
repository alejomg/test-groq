from pydantic import BaseModel, Field
from typing import Optional

# Data schema defined with Pydantic
class Item(BaseModel):
    id: Optional[int] = Field(default=None, gt=0, example=1)
    name: str = Field(..., min_length=3, example="Laptop Gamer")
    price: float = Field(..., gt=0)
    stock: int = Field(default=10, ge=0)
