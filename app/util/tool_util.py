import json
from uuid import UUID
from datetime import datetime

from groq.types.chat import ChatCompletionMessageToolCall
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.dialog import Dialog
from loguru import logger


def get_current_datetime():
    logger.info("[*** Tools ***] using tool -> get_current_datetime")
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
    logger.info(f"[*** Tools ***] using tool -> get_dialog_by_uuid: {duuid_str}")
    try:
        duuid = UUID(duuid_str)

        dialog = await Dialog.get_by_duuid(db, duuid)

        if not dialog:
            return json.dumps({"error": f"Dialog not found with UUID: {duuid_str}"})

        logger.info(f"[*** Tools ***] dialog: {json.dumps(dialog.to_dict_summary())}")
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


# 2. logic to choose function to use
# tool_calls: list[ChatCompletionMessageToolCall]
async def get_tool_result(tool_call: ChatCompletionMessageToolCall, db: AsyncSession):
    function_name = tool_call.function.name
    logger.info(f"[*** Tools ***] using tool: {function_name}")

    if function_name == "get_current_datetime":
        tool_result = get_current_datetime()
    elif function_name == "get_dialog_by_uuid":
        try:
            function_arguments = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
        except Exception as ex:
            logger.warning(f"[*** Tools ***] Failed to parse function arguments for {function_name}: {ex}")
            function_arguments = {}

        logger.info(f"[*** Tools ***] arguments for the tool: {function_arguments}")

        tool_result = await get_dialog_by_uuid(
            db=db,
            duuid_str=function_arguments.get("duuid_str")
        )
    else:
        tool_result = {"error": f"Tool {function_name} not implemented."}

    # Garantizar que tool_result sea SIEMPRE un string (requisito estricto de la API de Groq/OpenAI)
    if not isinstance(tool_result, str):
        tool_result = json.dumps(tool_result, ensure_ascii=False)

    logger.info(f"[*** Tools ***] tool result --> {tool_result}")

    return tool_result, function_name


# 2. add all tool calls and their results to turn history
async def add_tool_results_to_turn_history(turn_history: list[dict[str, str]],
                                           tool_calls: list[ChatCompletionMessageToolCall], db: AsyncSession):

    logger.info("[*** Tools ***] start adding tool calls and results to history")

    for tool_call in tool_calls:
        tool_result, tool_name = await get_tool_result(tool_call, db)

        # adding tool result to history
        turn_history.append({
            "tool_call_id": tool_call.id,
            "role": "tool",
            "name": tool_name,
            "content": tool_result,
        })

        logger.info(f"[*** Tools ***] added result: {tool_result} for tool: {tool_name}")

    logger.info("[*** Tools ***] end adding tool calls and results to history.")

    return turn_history
