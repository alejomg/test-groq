import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.v1.endpoints import items
from app.api.v1.endpoints import chat
from app.core.config import settings
from groq import AsyncGroq
from dotenv import load_dotenv

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup logic ---
    print(f"starting up {settings.PROJECT_NAME}...")
    # print("Connecting to DB...")
    # Example: await database.connect()
    
    # Guardamos el cliente en el 'state' para que sea accesible desde los routers
    app.state.groq_client = AsyncGroq(api_key=os.environ.get("GROQ_API_KEY"))
    
    yield  # Here the app runs and serves requests
    
    # --- Shutdown logic ---
    print(f"shutting down {settings.PROJECT_NAME}...")
    # print("Closing resources and cleanup...")
    # Ejemplo: await database.disconnect()
    await app.state.groq_client.close()

app = FastAPI(
    lifespan=lifespan,
    title=settings.PROJECT_NAME,
    debug=settings.DEBUG
)

#make routers visible
app.include_router(items.router, prefix="/api/v1/item", tags=["Item"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])


@app.get("/")
def root():
    return {"message": "API Online"}


@app.get("/config-check")
def check_config():
    return {"app_name": settings.PROJECT_NAME}
