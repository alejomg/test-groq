from fastapi import APIRouter, Request, HTTPException
from app.schemas.chat_request import ChatRequest

router = APIRouter()

@router.post("/ask")
async def ask_groq(request: Request, data: ChatRequest):
	
	# Recuperamos el cliente desde el estado de la app
    client = request.app.state.groq_client
    
    try:
        # Realizar la petición a Groq
        chat_completion = await client.chat.completions.create(
            messages=[
                {"role": "user", "content": data.prompt}
            ],
            model=data.model,
        )
        
        # Devolver la respuesta
        return {
            "status": "success",
            "response": chat_completion.choices[0].message.content,
            "info": {
                "model": data.model,
                "usage": chat_completion.usage # Opcional: ver cuántos tokens usaste
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en Groq: {str(e)}")

# Endpoint de salud simple
@router.get("/health")
def health_check():
    return {"status": "online"}
