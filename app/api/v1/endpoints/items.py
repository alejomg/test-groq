from fastapi import APIRouter, HTTPException
from app.schemas.item import Item

router = APIRouter()


@router.post("/", status_code=201)
async def create_item(item: Item):
    # Here Pydantic already validated item properties
    if item.price > 10000:
        raise HTTPException(status_code=400, detail="Price too high")
    
    return {"message": "Item created successfully", "data": item}
