import enum
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import ForeignKey, String, Text, UUID, Enum, JSON, func, select
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, selectinload
from app.db.session import Base


class DMessageType(str, enum.Enum):
    SYSTEM = "SYSTEM"
    USER = "USER"
    ASSISTANT = "ASSISTANT"


class Dialog(Base):
    __tablename__ = "dialog"

    id: Mapped[int] = mapped_column(primary_key=True)
    duuid: Mapped[UUID] = mapped_column(UUID(as_uuid=True), unique=True, index=True, default=uuid.uuid4)
    
    # Fechas automáticas de auditoría gestionadas por el Servidor/ORM
    created_date: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_date: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    # Relación bidireccional inteligente (Uno a Muchos) con cascada de borrado
    messages: Mapped[List["DMessage"]] = relationship(
        "DMessage",
        back_populates="dialog",
        cascade="all, delete-orphan"
    )

    # --- MÉTODOS DE FACTORÍA Y NEGOCIO (Rich Data Model) ---
    @classmethod
    def create_new(cls) -> "Dialog":
        """Método de factoría para inicializar consistentemente un nuevo dialogo."""
        return cls(duuid=uuid.uuid4(), messages=[])
        
    @classmethod
    async def get_by_duuid(cls, db: AsyncSession, duuid: UUID) -> Optional["Dialog"]:
        """
        Busca y recupera un dialogo específico utilizando su UUID público.
        Devuelve la instancia del Dialog si existe, o None si no se encuentra.
        """
        stmt = select(cls).options(selectinload(Dialog.messages)).where(cls.duuid == duuid)
        result = await db.execute(stmt)
        return result.scalars().first()

    def to_dict_summary(self) -> Dict[str, Any]:
        """Exporta un resumen ligero del dialogo ideal para listados en la UI."""
        return {
            "id": self.id,
            "duuid": str(self.duuid),
            "created_date": self.created_date.isoformat() if self.created_date else None,
            "updated_date": self.updated_date.isoformat() if self.updated_date else None,
        }

    @hybrid_property
    def get_duration(self) -> float:
        """Calcula la duración activa de la sesión de dialogo en segundos."""
        if self.updated_date and self.created_date:
            return (self.updated_date - self.created_date).total_seconds()
        return 0.0

    async def get_messages(self, db: AsyncSession, descending: bool = False) -> List["DMessage"]:
        """
        Recupera todos los mensajes asociados a este dialog de forma asíncrona.
        Ordena por el ID numérico para garantizar un orden cronológico perfecto.
        """
        stmt = select(DMessage).where(DMessage.dialog_id == self.id)
        
        if descending:
            stmt = stmt.order_by(DMessage.id.desc())
        else:
            stmt = stmt.order_by(DMessage.id.asc())
            
        result = await db.execute(stmt)
        return list(result.scalars().all())


class DMessage(Base):
    __tablename__ = "dialog_message"

    id: Mapped[int] = mapped_column(primary_key=True)
    dialog_id: Mapped[int] = mapped_column(ForeignKey("dialog.id", ondelete="CASCADE"), index=True)
    
    text: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[DMessageType] = mapped_column(Enum(DMessageType), nullable=False)
    
    # Columnas específicas del LLM (Nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    usage: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    created_date: Mapped[datetime] = mapped_column(server_default=func.now())

    # Relación inversa hacia el padre
    dialog: Mapped["Dialog"] = relationship("Dialog", back_populates="messages")

    # --- MÉTODOS DE FACTORÍA Y EXTRACTORES (Rich Data Model) ---

    @classmethod
    def create_sytem_prompt(cls, dialog_id: int, text: str) -> "DMessage":
        """Factoría especializada para el system prompt."""
        return cls(
            dialog_id=dialog_id,
            text=text,
            type=DMessageType.SYSTEM,
            model=None,
            usage=None
        )

    @classmethod
    def create_user_message(cls, dialog_id: int, text: str) -> "DMessage":
        """Factoría especializada para mensajes enviados por el usuario."""
        return cls(
            dialog_id=dialog_id,
            text=text,
            type=DMessageType.USER,
            model=None,
            usage=None
        )

    @classmethod
    def create_assistant_message(cls, dialog_id: int, text: str, model_name: str, usage_data: Dict[str, Any]) -> "DMessage":
        """Factoría especializada para respuestas generadas por el asistente (LLM)."""
        return cls(
            dialog_id=dialog_id,
            text=text,
            type=DMessageType.ASSISTANT,
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
