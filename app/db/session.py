import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

# En Render buscará la URL de Postgres. En local usará SQLite.
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "sqlite+aiosqlite:///./local_chats.db"
)

# Configuración especial solo si la URL es de SQLite
connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}

# 1. Crear el motor asíncrono
engine = create_async_engine(
    DATABASE_URL, 
    connect_args=connect_args, 
    echo=False
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
