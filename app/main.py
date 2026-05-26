import os
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.api.v1.endpoints import dialog
from app.api.v1.endpoints import wikipedia
from app.api.v1.endpoints import items
from app.core.config import settings
from groq import AsyncGroq
from dotenv import load_dotenv
from loguru import logger
from app.core.logger_config import setup_logging
from app.db.session import engine, Base
from sqlalchemy import text

load_dotenv()

# starting logs
setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup logic ---
    logger.info(f"Starting up {settings.PROJECT_NAME}...")
    
    # Crea las tablas automáticamente en tu SQLite local si no existen
    # (Nota: En producción con Postgres se suele usar Alembic, pero esto es perfecto para empezar)
    logger.info(f"Initializing {settings.DB_NAME} DB tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
        logger.info(f"Checking {settings.DB_NAME} DB connection...")
        await conn.execute(text("SELECT 1"))
    
    # saving the client to the 'state' for access from the routers.
    app.state.groq_client = AsyncGroq(api_key=os.environ.get("GROQ_API_KEY"))
    
    yield  # Here the app runs and serves requests
    
    # --- Shutdown logic ---
    logger.info(f"Shutting down {settings.PROJECT_NAME}...")
    # print("Closing resources and cleanup...")
    # Example: await database.disconnect()
    await app.state.groq_client.close()
    
    # Cierra el pool de conexiones de la base de datos de forma asíncrona
    await engine.dispose()
    logger.info(f"{settings.DB_NAME} DB connections closed.")

app = FastAPI(
    lifespan=lifespan,
    title=settings.PROJECT_NAME,
    debug=settings.DEBUG
)

# making routers visible
app.include_router(dialog.router, prefix="/api/v1/dialog", tags=["Dialog"])
app.include_router(wikipedia.router, prefix="/api/v1/wikipedia", tags=["Wikipedia"])
app.include_router(items.router, prefix="/api/v1/item", tags=["Item"])


@app.get("/")
def root():
    return {
        "app_name": settings.PROJECT_NAME,
        "status": "Online",
        "groq_model": settings.GROQ_MODEL
    }
