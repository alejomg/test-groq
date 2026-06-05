import json
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.dialog import Dialog
from loguru import logger


def get_current_datetime():
    logger.info("using tool -> get_current_datetime")
    return datetime.now().strftime("%m-%d-%Y %H:%M:%S")


get_current_datetime_tool = {
        "type": "function",
        "function": {
            "name": "get_current_datetime",
            "description": "Returns the current date and time. Use this tool ONLY when the user explicitly asks for the current date, time, or day.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            },
        },
    }


async def get_dialog_by_uuid(db: AsyncSession, duuid_str: str) -> str:
    logger.info(f"using tool -> get_dialog_by_uuid: {duuid_str}")
    try:
        duuid = UUID(duuid_str)
        
        dialog = await Dialog.get_by_duuid(db, duuid)
        
        if not dialog:
            return json.dumps({"error": f"Dialog not found with UUID: {duuid_str}"})
        
        logger.info(f"dialog: {json.dumps(dialog.to_dict_summary())}")
        return json.dumps(dialog.to_dict_summary())
        
    except ValueError:
        return json.dumps({"error": f"UUID '{duuid_str}' format not valid."})
    except Exception as e:
        return json.dumps({"error": f"Unexpected error searching for dialog: {str(e)}"})


get_dialog_by_uuid_tool = {
    "type": "function",
    "function": {
        "name": "get_dialog_by_uuid",
        "description": "Retrieves the metadata of a specific dialog. Use this tool ONLY when the user has explicitly provided a valid UUID string in their message. If the user asks about a dialog but has not provided the UUID, DO NOT use this tool; instead, ask the user to provide the identifier.",
        "parameters": {
            "type": "object",
            "properties": {
                "duuid_str": {
                    "type": "string",
                    "description": "The public UUID string provided by the user (e.g., '123e4567-e89b-12d3-a456-426614174000'). Never invent or use placeholder text here."
                }
            },
            "required": ["duuid_str"],
        }
    }
}


tools = [get_current_datetime_tool, get_dialog_by_uuid_tool]
