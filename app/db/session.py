import os
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

# Ruta absoluta al archivo SQLite (basada en la ubicación de este archivo)
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / f"{settings.DB_NAME}.db"

# En Render buscará la URL de Postgres. En local usará SQLite.
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite+aiosqlite:///{DB_PATH}")

# Render entrega la URL con esquema "postgres://" que SQLAlchemy 2.0 no acepta.
# Se convierte a "postgresql+asyncpg://" para compatibilidad con el motor async.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Configuración especial solo si la URL es de SQLite
connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}

# 1. Crear el motor asíncrono
engine = create_async_engine(
    DATABASE_URL, 
    connect_args=connect_args, 
    echo=settings.SHOW_SQL
)

# 2. Creador de sesiones asíncronas
AsyncSessionLocal = async_sessionmaker(
    bind=engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)


# 3. Clase Base para que hereden tus modelos
class Base(DeclarativeBase):
    pass


# Dependencia (yield) para inyectar la sesión en tus endpoints de FastAPI
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
