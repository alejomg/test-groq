import json
from uuid import UUID
from fastapi import APIRouter, Request, Depends, HTTPException
from dotenv import load_dotenv
from loguru import logger

from app.core.config import settings
from app.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.dialog import Dialog, DMessage
from app.schemas.dialog_request import DialogRequest
from app.schemas.dialog_response import DialogResponse, DialogDetailResponse, DialogProcessedResponse, DialogMetadata
from app.util.dialog_util import (get_raw_message_from_dmessage, get_dialog_messages_from_raw_messages,
                                  get_list_of_raw_messages, get_history_turn_from_dialog, acquire_dialog,
                                  add_user_message_to_dialog, process_tool_calls, add_assistant_message_to_dialog,
                                  sending_user_message)
from groq import BadRequestError


router = APIRouter()

load_dotenv()

model = settings.GROQ_MODEL


@router.post("", response_model=DialogProcessedResponse)
async def request_dialog(request: Request, dialog_request: DialogRequest, db: AsyncSession = Depends(get_db)):

    duuid = dialog_request.duuid
    user_message = dialog_request.message

    # 1 adquirimos un dialog nuevo o existente
    dialog = await acquire_dialog(duuid, db)

    # 2 guardamos en DB el mensaje recibido del usuario
    user_dmessage = await add_user_message_to_dialog(dialog, user_message, db)

    # 3 sacamos la historia del dialog, si es nueva solo tiene el mensaje de sistema y el de usuario
    # si es existente, tiene un historial de mensajes, y el último siempre es del usuario
    turn_history = await get_history_turn_from_dialog(dialog.duuid, db)

    # recovering the Groq client from the 'state'
    groq_client = request.app.state.groq_client

    try:
        # 4 sending the user message to groq along with the turn_history
        dialog_completion = await sending_user_message(turn_history, groq_client)

        # 5 if any tool call request, processing them and sending results back to the assistant (groq) for final
        dialog_completion, turn_history = await process_tool_calls(dialog_completion, turn_history, groq_client, db)

        # 6 guardamos en DB el mensaje recibido del asistente (groq)
        assistant_dmessage = await add_assistant_message_to_dialog(dialog, dialog_completion, db)
        
        # Passes Groq's exact token usage object smoothly
        usage = dialog_completion.usage.model_dump() if dialog_completion.usage else None

        raw_messages = [
            get_raw_message_from_dmessage(user_dmessage),
            get_raw_message_from_dmessage(assistant_dmessage)
        ]

        dialog_messages = get_dialog_messages_from_raw_messages(raw_messages)

        dialog_metadata = DialogMetadata(
                model=model,
                usage=usage
        )

        return DialogProcessedResponse(
            id=dialog.id,
            duuid=dialog.duuid,
            dialog=dialog_messages,
            metadata=dialog_metadata
        )

    except BadRequestError as bre:
        await db.rollback()
        
        # 1. Intentamos extraer el cuerpo completo del error en formato diccionario
        error_response = getattr(bre, "response", None)
        error_json = {}
        if error_response:
            try:
                error_json = error_response.json()
            except Exception:
                error_json = {"raw_body": error_response.text}

        # 2. Logeamos con Loguru usando formato JSON bonito para la consola
        logger.error("❌ ERROR 400 EN LA API DE GROQ (Tool Calling Failed)")
        logger.error(f"Estructura completa del error: {json.dumps(error_json, indent=2, ensure_ascii=False)}")
        
        # 3. Extraemos específicamente el 'failed_generation' si existe para verlo directo
        failed_gen = error_json.get("error", {}).get("failed_generation", "No disponible")
        logger.error(f"⚠️ Lo que el LLM intentó generar mal: {failed_gen}")

        raise HTTPException(
            status_code=400, 
            detail={
                "message": "Groq rechazó el formato de la herramienta",
                "details": error_json.get("error", {})
            }
        )
        
    except Exception as e:
        # rollback to avoid orfan or partial messages (review)
        await db.rollback()
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


@router.get("", response_model=list[DialogResponse])
async def list_dialogs(
        limit: int = 20,
        offset: int = 0,
        db: AsyncSession = Depends(get_db)
):
    """
    Recupera un listado paginado de todas las sesiones de dialog almacenadas.
    Los dialogos se devuelven ordenados por la fecha de última actualización (los más recientes primero).
    """
    # Construimos la query ordenando por la fecha de actualización de forma descendente
    stmt = select(Dialog).order_by(Dialog.updated_date.desc()).limit(limit).offset(offset)

    # Ejecutamos la consulta de forma asíncrona
    result = await db.execute(stmt)
    dialogs = result.scalars().all()

    return dialogs


@router.get("/{duuid}", response_model=DialogDetailResponse)
async def get_dialog(duuid: UUID, db: AsyncSession = Depends(get_db)):
    """
    Recupera un dialog por su uuid.
    """
    dialog = await Dialog.get_by_duuid(db, duuid)

    if not dialog:
        raise HTTPException(status_code=404, detail="Dialog not found")

    dialog_messages = get_dialog_messages_from_raw_messages(get_list_of_raw_messages(dialog))

    return DialogDetailResponse(
        id=dialog.id,
        duuid=dialog.duuid,
        model=dialog.model,
        created_date=dialog.created_date,
        updated_date=dialog.updated_date,
        messages=dialog_messages
    )
