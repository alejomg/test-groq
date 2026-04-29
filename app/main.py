from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.v1.endpoints import items
from app.core.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup logic ---
    print(f"starting up {settings.PROJECT_NAME}...")
    # print("Connecting to DB...")
    # Example: await database.connect()
    
    yield  # Here the app runs and serves requests
    
    # --- Shutdown logic ---
    print(f"shutting down {settings.PROJECT_NAME}...")
    # print("Closing resources and cleanup...")
    # Ejemplo: await database.disconnect()

app = FastAPI(
    lifespan=lifespan,
    title=settings.PROJECT_NAME,
    debug=settings.DEBUG
)

#make routers visible
app.include_router(items.router, prefix="/api/v1/item", tags=["Item"])


@app.get("/")
def root():
    return {"message": "API Online"}


@app.get("/config-check")
def check_config():
    return {"app_name": settings.PROJECT_NAME}
