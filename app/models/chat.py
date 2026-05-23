import enum
import uuid as py_uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import BigInteger, ForeignKey, String, Text, UUID, Enum, JSON, func, select
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from app.db.session import Base


class ChatMessageType(str, enum.Enum):
    USER = "USER"
    ASSISTANT = "ASSISTANT"


class Chat(Base):
    __tablename__ = "chat"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[py_uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, index=True, default=py_uuid.uuid4)
    
    # Fechas automáticas de auditoría gestionadas por el Servidor/ORM
    created_date: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_date: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    # Relación bidireccional inteligente (Uno a Muchos) con cascada de borrado
    messages: Mapped[List["ChatMessage"]] = relationship(
        "ChatMessage", 
        back_populates="chat", 
        cascade="all, delete-orphan"
    )

    # --- MÉTODOS DE FACTORÍA Y NEGOCIO (Rich Data Model) ---

    @classmethod
    def create_new(cls) -> "Chat":
        """Método de factoría para inicializar consistentemente un nuevo chat."""
        return cls(uuid=py_uuid.uuid4())
        
    @classmethod
    async def get_by_uuid(cls, db: AsyncSession, chat_uuid: py_uuid.UUID) -> Optional["Chat"]:
        """
        Busca y recupera un chat específico utilizando su UUID público.
        Devuelve la instancia del Chat si existe, o None si no se encuentra.
        """
        stmt = select(cls).where(cls.uuid == chat_uuid)
        result = await db.execute(stmt)
        return result.scalars().first()

    def to_dict_summary(self) -> Dict[str, Any]:
        """Exporta un resumen ligero del chat ideal para listados en la UI."""
        return {
            "id": self.id,
            "uuid": str(self.uuid),
            "created_date": self.created_date.isoformat() if self.created_date else None,
            "updated_date": self.updated_date.isoformat() if self.updated_date else None,
        }

    @hybrid_property
    def get_duration(self) -> float:
        """Calcula la duración activa de la sesión de chat en segundos."""
        if self.updated_date and self.created_date:
            return (self.updated_date - self.created_date).total_seconds()
        return 0.0

    async def get_messages(self, db: AsyncSession, descending: bool = False) -> List["ChatMessage"]:
        """
        Recupera todos los mensajes asociados a este chat de forma asíncrona.
        Ordena por el ID numérico para garantizar un orden cronológico perfecto.
        """
        stmt = select(ChatMessage).where(ChatMessage.chat_id == self.id)
        
        if descending:
            stmt = stmt.order_by(ChatMessage.id.desc())
        else:
            stmt = stmt.order_by(ChatMessage.id.asc())
            
        result = await db.execute(stmt)
        return list(result.scalars().all())


class ChatMessage(Base):
    __tablename__ = "chat_message"

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("chat.id", ondelete="CASCADE"), index=True)
    
    message: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[ChatMessageType] = mapped_column(Enum(ChatMessageType), nullable=False)
    
    # Columnas específicas del LLM (Nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    usage: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    created_date: Mapped[datetime] = mapped_column(server_default=func.now())

    # Relación inversa hacia el padre
    chat: Mapped["Chat"] = relationship("Chat", back_populates="messages")

    # --- MÉTODOS DE FACTORÍA Y EXTRACTORES (Rich Data Model) ---

    @classmethod
    def create_user_message(cls, chat_id: int, text: str) -> "ChatMessage":
        """Factoría especializada para mensajes enviados por el usuario."""
        return cls(
            chat_id=chat_id,
            message=text,
            type=ChatMessageType.USER,
            model=None,
            usage=None
        )

    @classmethod
    def create_assistant_message(cls, chat_id: int, text: str, model_name: str, usage_data: Dict[str, Any]) -> "ChatMessage":
        """Factoría especializada para respuestas generadas por el asistente (LLM)."""
        return cls(
            chat_id=chat_id,
            message=text,
            type=ChatMessageType.ASSISTANT,
            model=model_name,
            usage=usage_data
        )

    def get_total_tokens(self) -> int:
        """Extrae de forma segura el total de tokens consumidos desde el JSON de uso."""
        if self.usage and isinstance(self.usage, dict):
            return self.usage.get("total_tokens", 0)
        return 0

    def get_execution_time(self) -> float:
        """Extrae de forma segura el tiempo total de ejecución (Groq) desde el JSON."""
        if self.usage and isinstance(self.usage, dict):
            return self.usage.get("total_time", 0.0)
        return 0.0
