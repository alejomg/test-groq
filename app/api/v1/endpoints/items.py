from fastapi import APIRouter, HTTPException
from app.schemas.item import Item
from loguru import logger

router = APIRouter()


@router.post("/", status_code=201)
async def create_item(item: Item):
    # Here Pydantic already validated item properties
    logger.debug(f"Payload: {item.model_dump()}")
    
    if item.price > 10000:
        logger.error(f"Price too high: {item.price}")
        raise HTTPException(status_code=400, detail="Price too high")
    
    logger.debug(f"Item created: {item.name}")
    
    return {"message": "Item created successfully", "data": item}
