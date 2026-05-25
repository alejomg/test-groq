import chainlit as cl
from client import send_api_request
from loguru import logger


@cl.on_chat_start
async def start():
    """Se ejecuta cuando el usuario abre o recarga la pestaña del chat."""
    # Inicializamos el uuid del chat en la sesión de Chainlit como None
    cl.user_session.set("duuid", None)

    # Mensaje de bienvenida inicial
    await cl.Message(content="Hey! I’m here and ready to chat. What would you like to talk about today? "
                             "Expect short replies with a little bit of personality along the way.").send()


@cl.on_message
async def main(message: cl.Message):
    """Se ejecuta cada vez que el usuario envía un mensaje en la UI."""
    # 1. Recuperar el UUID del dialogo actual (si existe)
    duuid = cl.user_session.get("duuid")

    # 2. Crear el mensaje que contendrá la respuesta y enviarlo vacío para mostrar animación de carga
    msg_espera = cl.Message(content="")
    await msg_espera.send()

    try:
        # 3. Llamar a tu FastAPI pasando el prompt del usuario
        backend_response = await send_api_request(
            message=message.content,
            duuid=duuid
        )

        # 4. Parsear la respuesta basándonos en tu Pydantic ChatResponse
        # Estructura esperada: { "status": "success", "uuid": "...", "chat": [...] }
        nuevo_uuid = backend_response.get("duuid")

        # Extraemos el texto del último elemento del historial devuelto por el backend
        historial = backend_response.get("dialog", [])
        if historial:
            # Tu backend devuelve una lista de SingleChatResponse. El último es el del sistema.
            ultimo_mensaje = historial[-1]
            texto_respuesta = ultimo_mensaje.get("text", "")
        else:
            texto_respuesta = "El backend no devolvió ningún mensaje."

        # 5. Si era un chat nuevo, guardamos el UUID generado por el backend en la sesión
        if nuevo_uuid and not duuid:
            cl.user_session.set("duuid", nuevo_uuid)
            logger.info(f"Sesión de Chainlit vinculada al UUID del backend: {nuevo_uuid}")

        # 6. Actualizar el mensaje en la pantalla con el texto final de Groq
        msg_espera.content = texto_respuesta
        await msg_espera.update()

    except Exception as e:
        # En caso de error, actualizamos el mensaje informando al usuario
        msg_espera.content = f"❌ Error al procesar la solicitud: {str(e)}"
        await msg_espera.update()