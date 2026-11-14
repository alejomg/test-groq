from typing import Any

from fastapi import HTTPException
from groq import AsyncGroq
from groq.types.chat import ChatCompletion

from app.core.config import settings
from app.models.dialog import DMessage, Dialog
from app.schemas.dialog_response import DialogSimpleMessage
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from loguru import logger
from app.util.tool_util import add_tool_results_to_turn_history, tools

model = settings.GROQ_MODEL


def get_raw_message_from_dmessage(dialog_message: DMessage) -> dict[str, Any]:
    return {
        "text": dialog_message.text,
        "type": dialog_message.type,
        "role": dialog_message.role,
    }


def get_list_of_raw_messages(dialog: Dialog) -> list[dict[str, Any]]:
    """
    Converts a list of DMessage from a Dialog to a list of dictionaries
    :param dialog:
    :return:
    """
    if not dialog or not dialog.messages:
        return []

    return [
        get_raw_message_from_dmessage(message)
        for message in dialog.messages
    ]


def get_dialog_messages_from_raw_messages(raw_messages: list[dict[str, Any]]) -> list[DialogSimpleMessage]:
    """
    Converts a list of dictionaries to a list of DialogSingleMessage Pydantic model
    :param raw_messages:
    :return:
    """
    return [DialogSimpleMessage(**raw_message) for raw_message in raw_messages]


def get_turn_from_dmessage(dialog_message: DMessage) -> dict[str, str]:
    return {
        "role": dialog_message.type.lower(),
        "content": dialog_message.text
    }


async def get_history_turn_from_dialog(duuid: UUID, db: AsyncSession) -> list[dict[str, str]]:
    """
    Returns the history turn of a dialog
    :param db:
    :param duuid:
    :return:
    """
    dialog = await Dialog.get_by_duuid(db, duuid)

    if not dialog or not dialog.messages:
        return []

    return [
        get_turn_from_dmessage(message)
        for message in dialog.messages
    ]


async def acquire_dialog(duuid: UUID, db: AsyncSession) -> Dialog:
    if not duuid:
        return await _start_new_dialog(db)
    else:
        return await _get_existing_dialog(duuid, db)


async def _start_new_dialog(db: AsyncSession) -> Dialog:
    logger.info(f"[*** Dialog ***] starting new dialog with system initial message")
    dialog = Dialog.create_new(model_name=model)
    db.add(dialog)
    await db.commit()

    system_initial_message = DMessage.create_system_initial_message(dialog_id=dialog.id)

    db.add(system_initial_message)
    await db.commit()
    await db.refresh(dialog, attribute_names=["messages"])

    logger.info(f"[*** Dialog ***] new dialog: {dialog.duuid} with system initial message: {system_initial_message.id}")

    return dialog


async def _get_existing_dialog(duuid: UUID, db: AsyncSession) -> Dialog:
    logger.info(f"[*** Dialog ***] getting dialog: {duuid}")
    dialog = await Dialog.get_by_duuid(db, duuid)

    if not dialog:
        logger.info(f"[*** Dialog ***] dialog: {duuid} NOT found")
        raise HTTPException(status_code=404, detail="Dialog not found")

    logger.info(f"[*** Dialog ***] found dialog: {duuid}")

    return dialog


async def add_user_message_to_dialog(dialog: Dialog, user_message: str, db: AsyncSession) -> DMessage:

    logger.info(f"[*** Dialog ***] adding new user message to dialog: {dialog.duuid}")

    user_dmessage = DMessage.create_user_message(
        dialog_id=dialog.id,
        text=user_message,
    )

    db.add(user_dmessage)
    await db.commit()
    await db.refresh(dialog, attribute_names=["messages"])

    logger.info(f"[*** Dialog ***] added new user message id: {user_dmessage.id} - {user_message} "
                f" to dialog: {dialog.duuid}")

    return user_dmessage


async def add_assistant_message_to_dialog(dialog: Dialog, dialog_completion: ChatCompletion,
                                          db: AsyncSession) -> DMessage:

    logger.info(f"[*** Dialog ***] adding new assistant message to dialog: {dialog.duuid}")

    assistant_message = dialog_completion.choices[0].message.content

    usage = dialog_completion.usage.model_dump() if dialog_completion.usage else None

    assistant_dmessage = DMessage.create_assistant_message(
        dialog_id=dialog.id,
        text=assistant_message,
        usage_data=usage,
    )

    db.add(assistant_dmessage)
    await db.commit()
    await db.refresh(dialog, attribute_names=["messages"])

    logger.info(f"[*** Dialog ***] added new assistant message id: {assistant_dmessage.id} - {assistant_message} "
                f" to dialog: {dialog.duuid}")

    return assistant_dmessage


async def process_tool_calls(dialog_completion: ChatCompletion, turn_history: list[dict[str, str]],
                             groq_client: AsyncGroq, db: AsyncSession) -> tuple[ChatCompletion, list[dict[str, str]] | Any]:

    dialog_completion_message = dialog_completion.choices[0].message
    tool_calls = dialog_completion_message.tool_calls

    logger.info(f"[*** Dialog ***] looking for tool calls")

    if tool_calls:
        logger.info(f"[*** Dialog ***] trying to use tools -> : {tool_calls}")

        # 1. Agregar solicitud de tool call del asistente al historial en formato dict homogéneo
        turn_history.append(dialog_completion_message.model_dump(exclude_none=True))
        # Nota: Como alternativa, se puede construir el diccionario manualmente si en algún momento se requiere control total y exacto de cada campo que viaja a la API.

        # 2. add all tool calls and their results to turn history
        turn_history = await add_tool_results_to_turn_history(turn_history, tool_calls, db)

        # 3. sending everything back to Groq to get final response
        logger.info(f"[*** Dialog ***] sending everything back to Groq to get final response: {turn_history}")
        dialog_completion = await groq_client.chat.completions.create(
            model=model,
            messages=turn_history
        )

        dialog_completion_message = dialog_completion.choices[0].message
        logger.info(f"[*** Dialog ***] final response from groq: {dialog_completion_message}")

    return dialog_completion, turn_history


# sending the user message to groq
async def sending_user_message(turn_history: list[dict[str, str]], groq_client: AsyncGroq) \
        -> ChatCompletion:

    logger.info(f"[*** Dialog ***] sending the history and the user new message to groq: {turn_history}")
    dialog_completion = await groq_client.chat.completions.create(
        messages=turn_history,
        model=model,
        tools=tools,
        tool_choice="auto"
    )

    dialog_completion_message = dialog_completion.choices[0].message
    logger.info(f"[*** Dialog ***] response from groq: {dialog_completion_message}")

    return dialog_completion
