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

from sqladmin import Admin
from app.admin import admin_auth, DialogAdmin, DMessageAdmin

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

# Montaje del panel de administración SQLAdmin
admin = Admin(
    app=app,
    engine=engine,
    authentication_backend=admin_auth,
    title=f"{settings.PROJECT_NAME} - Backoffice",
)

_ADMIN_TRANSLATIONS = {
    "Actions": "Acciones",
    "Apply Filter": "Aplicar filtro",
    "Cancel": "Cancelar",
    "Clear filter": "Quitar filtro",
    "Close": "Cerrar",
    "Column": "Columna",
    "Delete": "Eliminar",
    "Delete selected items": "Eliminar elementos seleccionados",
    "Done": "Hecho",
    "Edit": "Editar",
    "Edit %(name)s": "Editar %(name)s",
    "Enter username": "Introduce el nombre de usuario",
    "Export": "Exportar",
    "Filters": "Filtros",
    "Go Back": "Volver",
    "Import": "Importar",
    "Import CSV": "Importar CSV",
    "Language": "Idioma",
    "Login": "Iniciar sesión",
    "Login to %(title)s": "Iniciar sesión en %(title)s",
    "Logout": "Cerrar sesión",
    "New %(name)s": "Nuevo %(name)s",
    "next": "siguiente",
    "No file selected": "Ningún archivo seleccionado",
    "Password": "Contraseña",
    "Please confirm": "Confirma la acción",
    "prev": "anterior",
    "Refresh list": "Actualizar lista",
    "Save": "Guardar",
    "Save and add another": "Guardar y añadir otro",
    "Save and continue editing": "Guardar y seguir editando",
    "Save as new": "Guardar como nuevo",
    "Search": "Buscar",
    "Select all": "Seleccionar todo",
    "Select item": "Seleccionar elemento",
    "Show": "Mostrar",
    "Showing %(start)s to %(end)s of %(count)s items": "Mostrando %(start)s a %(end)s de %(count)s elementos",
    "Skip invalid rows and continue import": "Omitir filas no válidas y continuar la importación",
    "Username": "Nombre de usuario",
    "Value": "Valor",
    "View": "Ver",
    "Yes": "Sí",
    "You are not authorized to view these records.": "No tienes autorización para ver estos registros.",
}


def _translate_admin_text(message: str) -> str:
    return _ADMIN_TRANSLATIONS.get(message, message)


def _translate_admin_plural(singular: str, plural: str, count: int) -> str:
    return _translate_admin_text(singular if count == 1 else plural)


admin.templates.env.install_gettext_callables(
    _translate_admin_text,
    _translate_admin_plural,
    newstyle=True,
)
admin.add_view(DialogAdmin)
admin.add_view(DMessageAdmin)


@app.get("/")
def root():
    return {
        "app_name": settings.PROJECT_NAME,
        "status": "Online",
        "groq_model": settings.GROQ_MODEL
    }
