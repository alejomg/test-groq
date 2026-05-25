import os
from uuid import UUID
from fastapi import APIRouter, Request, Depends, HTTPException
from dotenv import load_dotenv
from loguru import logger
from app.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.dialog import Dialog, DMessage
from app.schemas.dialog_request import DialogRequest
from app.schemas.dialog_response import DialogResponse, DialogDetailResponse, DialogProcessedResponse, DialogSimpleMessage, \
    DialogMetadata
from app.util.dialog_util import get_raw_message_from_dmessage, get_dialog_messages_from_raw_messages, get_list_of_raw_messages

router = APIRouter()

load_dotenv()

model = os.environ.get("GROQ_MODEL")


@router.post("", response_model=DialogProcessedResponse)
async def request_dialog(request: Request, dialog_request: DialogRequest, db: AsyncSession = Depends(get_db)):
    duuid = dialog_request.duuid
    user_message = dialog_request.message

    if not duuid:
        logger.info(f"starting new dialog")
        dialog = Dialog.create_new()
        db.add(dialog)
        await db.commit()
        await db.refresh(dialog)
    else:
        logger.info(f"getting dialog: {duuid}")
        dialog = await Dialog.get_by_duuid(db, duuid)

        if not dialog:
            raise HTTPException(status_code=404, detail="Dialog not found")

    # recovering the Groq client from the 'state'
    groq_client = request.app.state.groq_client

    # sending the request to groq
    try:
        dialog_completion = await groq_client.chat.completions.create(
            messages=[
                {"role": "user", "content": user_message}
            ],
            model=model,
        )

        dialog_user_message = DMessage.create_user_message(
            dialog_id=dialog.id,
            text=user_message,
        )
        db.add(dialog_user_message)

        # getting the response
        assistant_message = dialog_completion.choices[0].message.content

        # Passes Groq's exact token usage object smoothly
        usage = dialog_completion.usage.model_dump() if dialog_completion.usage else None

        dialog_assistant_message = DMessage.create_assistant_message(
            dialog_id=dialog.id,
            text=assistant_message,
            model_name=model,
            usage_data=usage,
        )
        db.add(dialog_assistant_message)

        await db.commit()

        raw_messages = [
            get_raw_message_from_dmessage(dialog_user_message),
            get_raw_message_from_dmessage(dialog_assistant_message)
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

    except Exception as e:
        # rollback to avoid orfan or partial messages (review)
        await db.rollback()
        logger.error(f"Error processing Groq interaction: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error in Groq: {str(e)}")


@router.get("", response_model=list[DialogResponse])
async def list_dialogs(
        limit: int = 20,
        offset: int = 0,
        db: AsyncSession = Depends(get_db)
):
    """
    Recupera un listado paginado de todas las sesiones de dialogo almacenadas.
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
    Recupera un dialogo por su uuid.
    """
    dialog = await Dialog.get_by_duuid(db, duuid)

    if not dialog:
        raise HTTPException(status_code=404, detail="Dialog not found")

    dialog_messages = get_dialog_messages_from_raw_messages(get_list_of_raw_messages(dialog))

    return DialogDetailResponse(
        id=dialog.id,
        duuid=dialog.duuid,
        created_date=dialog.created_date,
        updated_date=dialog.updated_date,
        messages=dialog_messages
    )
