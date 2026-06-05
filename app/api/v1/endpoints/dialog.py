import os
import json
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
from app.util.dialog_util import get_raw_message_from_dmessage, get_dialog_messages_from_raw_messages, get_list_of_raw_messages, get_history_turn_from_dialog, init_history_turn, get_system_prompt_message
from app.util.tool_util import tools, get_current_datetime, get_dialog_by_uuid
from groq import BadRequestError


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

        dialog_sytem_prompt = DMessage.create_sytem_prompt(
            dialog_id=dialog.id,
            text=get_system_prompt_message(),
        )
        db.add(dialog_sytem_prompt)
        await db.commit()
        
        await db.refresh(dialog, attribute_names=["messages"])
        
        logger.info(f"new dialog: {dialog.duuid}")
        
    else:
        logger.info(f"getting dialog: {duuid}")
        dialog = await Dialog.get_by_duuid(db, duuid)

        if not dialog:
            raise HTTPException(status_code=404, detail="Dialog not found")
            
        logger.info(f"found dialog: {duuid}")

    turn_history = get_history_turn_from_dialog(dialog)
    turn_history.append({"role": "user", "content": user_message})
    
    # recovering the Groq client from the 'state'
    groq_client = request.app.state.groq_client

    # sending the request to groq
    try:
        logger.info(f"sending request: {turn_history}")
        dialog_completion = await groq_client.chat.completions.create(
            messages=turn_history,
            model=model,
            tools=tools,
            tool_choice="auto"
        )
        logger.info(f"got response: {dialog_completion}")

        dialog_user_message = DMessage.create_user_message(
            dialog_id=dialog.id,
            text=user_message,
        )
        db.add(dialog_user_message)

        dialog_completion_message = dialog_completion.choices[0].message
        logger.info(f"****** {user_message}")
        logger.info(f"****** {dialog_completion_message}")
        
        tool_calls = dialog_completion_message.tool_calls
        if tool_calls:
            logger.info(f"Groq trying to use a tool -> tool_calls: {tool_calls}")
            
            # 1. Adding Groq tool use request to history
            turn_history.append(dialog_completion_message)
            
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_arguments = json.loads(tool_call.function.arguments)
                
                logger.info(f"using tool: {function_name}")
                logger.info(f"arguments: {function_arguments}")
                
                # 2. logic to choose function to use
                if function_name == "get_current_datetime":
                    tool_result = get_current_datetime()
                elif function_name == "get_dialog_by_uuid":
                    tool_result = await get_dialog_by_uuid(
                        db=db, 
                        duuid_str=function_arguments.get("duuid_str")
                    )
                else:
                    tool_result = json.dumps(
                        {"error": f"Tool {function_name} not implemented."}
                    )
                    
                logger.info(f"tool_result tool: {tool_result}")
                
                # 3. Adding tool result to history
                turn_history.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": tool_result,
                })
                    
                # 4. Send everything back to Groq to get final response
                dialog_completion = await groq_client.chat.completions.create(
                    model=model,
                    messages=turn_history
                )
        
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
