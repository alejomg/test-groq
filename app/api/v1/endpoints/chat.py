import os
import json
import wikipedia
import uuid
from fastapi import APIRouter, Request, HTTPException
from app.schemas.chat_request import ChatRequest
from app.schemas.chat_response import ChatResponse, SingleChatResponse, ChatResponseInfo
from app.schemas.list_request import ListRequest
from dotenv import load_dotenv

router = APIRouter()

load_dotenv()

model = os.environ.get("GROQ_MODEL")


@router.post("/ask", response_model=ChatResponse)
async def ask_groq(request: Request, data: ChatRequest):
	
	# recovering the client from the 'state'
    client = request.app.state.groq_client
    
    try:
        userMessage = data.prompt
		
        # sending the request to groq
        chat_completion = await client.chat.completions.create(
            messages=[
                {"role": "user", "content": userMessage}
            ],
            model=model,
        )
        
        # getting the response
        systemResponse = chat_completion.choices[0].message.content
        
        # building chat (mapping them to the SingleResponse shape)
        raw_outputs = [
            {"message": userMessage, "type": "user"},
            {"message": systemResponse, "type": "system"}
        ]
    
        # Convert dictionaries to SingleChatResponse Pydantic model
        processed_responses = [SingleChatResponse(**item) for item in raw_outputs]
        
        unique_id = data.uuid
        if not unique_id:
            # generating uuid
            unique_id = str(uuid.uuid4())
        
        # 3. Return the generic wrapper
        return ChatResponse(
            status="success",
            uuid=unique_id,
            chat=processed_responses,
            info=ChatResponseInfo(
                model=model,
                usage=chat_completion.usage.model_dump() if chat_completion.usage else None  # Optional: Passes Groq's exact token usage object smoothly
            )
        )
                    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in Groq: {str(e)}")


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
