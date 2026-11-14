from fastapi import HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Request

from app.models.dialog import Dialog, DialogSource, DMessageRole, DMessageType
from app.util.dialog_util import _start_new_dialog, get_turn_history_from_dialog, sending_turn_history, \
    process_tool_calls, add_assistant_message_to_dialog, add_user_message_to_dialog

# number of rounds of the dialog
ROUNDS = 3


async def start_synthetic_dialog(request: Request, db: AsyncSession):

    dialog_source = DialogSource.SYNTHETIC
    origin_role = DMessageRole.STUDENT
    pasive_role = DMessageRole.TEACHER

    # 1 iniciamos un dialog origen y pasivo nuevos
    dialog_origin = await _start_new_dialog(dialog_source, origin_role, db)
    dialog_pasive = await _start_new_dialog(dialog_source, pasive_role, db)

    try:

        # rounds
        for count in range(ROUNDS):

            await generic_turn(dialog_origin, dialog_pasive, origin_role, request, db)

            await generic_turn(dialog_pasive, dialog_origin, pasive_role, request, db)

        # # O4 actualizamos la historia origen
        # turn_history_origin = await get_turn_history_from_dialog(dialog_origin.duuid, db)
        #
        # # O5 sending the turn_history to groq, just the system message
        # completion_origin = await sending_turn_history(turn_history_origin, groq_client)
        #
        # # O6 if any tool call request, processing them and sending results back to the assistant (groq) for final
        # completion_origin, turn_history_origin = await process_tool_calls(completion_origin, turn_history_origin, groq_client, db)
        #
        # # O7 guardamos en DB el mensaje recibido del asistente (groq)
        # assistant_dmessage = await add_assistant_message_to_dialog(dialog_origin, completion_origin, DMessageRole.STUDENT, db)
        #
        # # O8 actualizamos la historia origin
        # turn_history_origin = await get_turn_history_from_dialog(dialog_origin.duuid, db)
        #
        # # O9 guardamos en DB el mensaje recibido del origin
        # origin_message = assistant_dmessage.text
        # pasive_dmessage = await add_user_message_to_dialog(
        #     dialog_pasive, origin_message, db, role=DMessageRole.STUDENT
        # )




        # # P4 actualizamos la historia origin
        # turn_history_pasive = await get_turn_history_from_dialog(dialog_pasive.duuid, db)
        #
        # # P5 sending the turn_history to groq
        # completion_pasive = await sending_turn_history(turn_history_pasive, groq_client)
        #
        # # P6 if any tool call request, processing them and sending results back to the assistant (groq) for final
        # completion_pasive, turn_history_pasive = await process_tool_calls(completion_pasive, turn_history_pasive, groq_client, db)
        #
        # # P7 guardamos en DB el mensaje recibido del asistente (groq)
        # assistant_dmessage = await add_assistant_message_to_dialog(dialog_pasive, completion_pasive, DMessageRole.TEACHER, db)
        #
        # # P8 actualizamos la historia pasivo
        # turn_history_pasive = await get_turn_history_from_dialog(dialog_pasive.duuid, db)
        #
        # # P9 guardamos en DB el mensaje recibido del pasivo
        # pasive_message = assistant_dmessage.text
        # origin_dmessage = await add_user_message_to_dialog(
        #     dialog_origin, pasive_message, db, role=DMessageRole.TEACHER
        # )




        # # O4 actualizamos la historia pasivo
        # turn_history_origin = await get_turn_history_from_dialog(dialog_origin.duuid, db)
        #
        # # O5 sending the turn_history to groq
        # completion_origin = await sending_turn_history(turn_history_origin, groq_client)
        #
        # # O6 if any tool call request, processing them and sending results back to the assistant (groq) for final
        # completion_origin, turn_history_origin = await process_tool_calls(completion_origin, turn_history_origin, groq_client, db)
        #
        # # O7 guardamos en DB el mensaje recibido del asistente (groq)
        # assistant_dmessage = await add_assistant_message_to_dialog(dialog_origin, completion_origin, DMessageRole.STUDENT, db)
        #
        # # O8 actualizamos la historia pasivo
        # turn_history_origin = await get_turn_history_from_dialog(dialog_origin.duuid, db)
        #
        # # O9 guardamos en DB el mensaje recibido del origin
        # origin_message = assistant_dmessage.text
        # pasive_dmessage = await add_user_message_to_dialog(
        #     dialog_pasive, origin_message, db, role=DMessageRole.STUDENT
        # )


        # print()

    except Exception as e:
        # rollback to avoid orfan or partial messages (review)
        await db.rollback()
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


async def generic_turn(dialog_initiator: Dialog, dialog_responder: Dialog, initiator_role: DMessageRole,
                       request: Request, db: AsyncSession):

    # Initiator vs. Responder
    groq_client = request.app.state.groq_client

    # O4 actualizamos la historia del Initiator
    turn_history_initiator = await get_turn_history_from_dialog(dialog_initiator.duuid, db)

    # O5 sending the turn_history to groq, just the system message
    completion_initiator = await sending_turn_history(turn_history_initiator, groq_client)

    # O6 if any tool call request, processing them and sending results back to the assistant (groq) for final
    completion_initiator, turn_history_initiator = await process_tool_calls(completion_initiator, turn_history_initiator,
                                                                      groq_client, db)

    # O7 guardamos en DB el mensaje recibido del asistente (groq)
    assistant_dmessage = await add_assistant_message_to_dialog(dialog_initiator, completion_initiator, initiator_role,
                                                               db)

    # O8 actualizamos la historia del Initiator
    turn_history_initiator = await get_turn_history_from_dialog(dialog_initiator.duuid, db)

    # O9 guardamos en DB el mensaje recibido del Initiator
    initiator_message = assistant_dmessage.text
    responder_dmessage = await add_user_message_to_dialog(
        dialog_responder, initiator_message, db, role=initiator_role
    )
