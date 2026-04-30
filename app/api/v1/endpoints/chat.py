import os
from fastapi import APIRouter, Request, HTTPException
from app.schemas.chat_request import ChatRequest
from dotenv import load_dotenv

router = APIRouter()

load_dotenv()


@router.post("/ask")
async def ask_groq(request: Request, data: ChatRequest):
	
	# recovering the client from the 'state'
    client = request.app.state.groq_client
    
    model = os.environ.get("GROQ_MODEL")
    
    try:
        # sending the request to groq
        chat_completion = await client.chat.completions.create(
            messages=[
                {"role": "user", "content": data.prompt}
            ],
            model=model,
        )
        
        # returning the response
        response = chat_completion.choices[0].message.content
        
        return {
            "status": "success",
            "response": response,
            "info": {
                "model": model,
                "usage": chat_completion.usage # Optional: to see token usage
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in Groq: {str(e)}")


# simple health check
@router.get("/health")
def health_check():
    return {
		"status": "online"
		}
