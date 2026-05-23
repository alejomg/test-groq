import os
import json
import wikipedia
import uuid
from fastapi import APIRouter, Request, Depends, HTTPException
from app.schemas.chat_request import ChatRequest
from app.schemas.chat_response import ChatResponse, SingleChatResponse, ChatResponseInfo
from app.schemas.chat import ChatDetailResponse
from app.schemas.list_request import ListRequest
from dotenv import load_dotenv
from loguru import logger
from app.db.session import get_db
from app.models.chat import Chat, ChatMessage
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

router = APIRouter()

load_dotenv()

model = os.environ.get("GROQ_MODEL")


@router.post("", response_model=ChatResponse)
async def chat(request: Request, data: ChatRequest, db: AsyncSession = Depends(get_db)):
	
    chat_uuid = data.uuid
    user_message = data.prompt
	
    if not chat_uuid:
        logger.info(f"starting new chat")
        chat = Chat.create_new()
        db.add(chat)
        await db.commit()
        await db.refresh(chat)
    else:
        logger.info(f"getting chat: {chat_uuid}")
        chat = await Chat.get_by_uuid(db, chat_uuid)
        
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
	
    chat_uuid = chat.uuid
	
    user_msg_obj = ChatMessage.create_user_message(chat.id, user_message)
    db.add(user_msg_obj)	
	
    # recovering the client from the 'state'
    client = request.app.state.groq_client
    
    try:

        # sending the request to groq
        chat_completion = await client.chat.completions.create(
            messages=[
                {"role": "user", "content": user_message}
            ],
            model=model,
        )
        
        # getting the response
        system_response_text = chat_completion.choices[0].message.content
        
        usage = chat_completion.usage.model_dump() if chat_completion.usage else None  # Passes Groq's exact token usage object smoothly
        
        assistant_message = ChatMessage.create_assistant_message(
            chat_id=chat.id, 
            text=system_response_text, 
            model_name=model, 
            usage_data=usage
        )
        db.add(assistant_message)
        
        await db.commit()        
        
        # building chat (mapping them to the SingleResponse shape)
        raw_outputs = [
            {"message": user_message, "type": "user"},
            {"message": system_response_text, "type": "system"}
        ]
    
        # Convert dictionaries to SingleChatResponse Pydantic model
        processed_responses = [SingleChatResponse(**item) for item in raw_outputs]
        
        # 3. Return the generic wrapper
        return ChatResponse(
            status="success",
            uuid=chat_uuid,
            chat=processed_responses,
            info=ChatResponseInfo(
                model=model,
                usage=usage
            )
        )
                    
    except Exception as e:
        # rollback to avoid orfan or partial messages (review)
        await db.rollback()
        logger.error(f"Error processing Groq interaction: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error in Groq: {str(e)}")

@router.get("", response_model=list[ChatResponse])
async def list_chats(
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """
    Recupera un listado paginado de todas las sesiones de chat almacenadas.
    Los chats se devuelven ordenados por la fecha de última actualización (los más recientes primero).
    """
    # Construimos la query ordenando por la fecha de actualización de forma descendente
    stmt = select(Chat).order_by(Chat.updated_date.desc()).limit(limit).offset(offset)
    
    # Ejecutamos la consulta de forma asíncrona
    result = await db.execute(stmt)
    chats = result.scalars().all()
    
    return chats
    
    
@router.get("/{chat_uuid}", response_model=ChatDetailResponse)
#@router.get("/{chat_uuid}")
async def get_chat(chat_uuid: uuid.UUID, db: AsyncSession = Depends(get_db)):
    
    logger.info(f"getting chat: {chat_uuid}")
    
    chat = await Chat.get_by_uuid(db, chat_uuid)
    
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
        
    return chat
    

# simple health check
@router.get("/health")
def health_check():
    return {
		"status": "online"
	}


generate_wikipedia_reading_list_tool = {
	"type": "function",
	"function": {
		"name": "generate_wikipedia_reading_list",
		"description": "search REAL wikipedia pages and return title + URL.",
		"parameters": {
			"type": "object",
			"properties": {
				"research_topic": {
					"type": "string",
					"description":  "The overall research topic."
				},
				"article_titles": {
					"type": "array",
					"items": {"type": "string"},
					"description":  "List of Wikipedia article titles."
				}
			},
			"required": ["research_topic", "article_titles"]
		}
	}
}


@router.post("/list")
async def list_groq(request: Request, data: ListRequest):

	# recovering the client from the 'state'
	client = request.app.state.groq_client

	topic = data.topic
	num_articles = data.num_articles

	prompt = f"""
	Generate exactly {num_articles} Wikipedia article titles about '{topic}'.

	Rules:
	- Must be real topics
	- No duplicates
	- Interesting but not too obvious

	When appropriate, call the tool generate_wikipedia_reading_list.
	"""

	response = await client.chat.completions.create(
		model=model,
		messages=[
			{"role": "user", "content": prompt}
		],
		tools=[generate_wikipedia_reading_list_tool],
		tool_choice="auto"
	)

	message = response.choices[0].message

	# Aquí está la diferencia importante con Claude, Si el modelo quiere usar la tool...
	if message.tool_calls:
		tool_call = message.tool_calls[0]
		args = json.loads(tool_call.function.arguments)

		articles = generate_wikipedia_reading_list(
			args["research_topic"],
			args["article_titles"]
		)

		return {
			"topic": args["research_topic"],
			"articles": articles
		}

	# fallback si no usa tool
	return {
		"topic": topic,
		"articles": [],
		"note": "Model did not call tool"
	}


def generate_wikipedia_reading_list(research_topic, article_titles):
	wikipedia_articles = []
	for t in article_titles:
		try:
			results = wikipedia.search(t)
			page = wikipedia.page(results[0])
			title = page.title
			url = page.url
			wikipedia_articles.append({"title": title, "url": url})
		except:
			continue
	# add_to_research_reading_file(wikipedia_articles, research_topic)

	return wikipedia_articles


def add_to_research_reading_file(articles, topic):
	with open("output/research_reading.md", "a", encoding="utf-8") as file:
		file.write(f"## {topic} \n")
		for article in articles:
			title = article["title"]
			url = article["url"]
			file.write(f"* [{title}]({url}) \n")
		file.write(f"\n\n")
