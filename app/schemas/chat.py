from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, UUID4


class ChatMessageType(str, Enum):
    USER = "USER"
    ASSISTANT = "ASSISTANT"


# --- ESQUEMAS PARA METADATOS DE CONSUMO (USAGE) ---

class LLMUsageMetadata(BaseModel):
    """
    Estructura validada para el campo JSON de consumo de tokens y tiempos.
    Usa Field(default=...) para asegurar valores consistentes si faltan campos.
    """
    completion_tokens: int = Field(0, description="Tokens generados por el asistente")
    prompt_tokens: int = Field(0, description="Tokens del prompt del usuario")
    total_tokens: int = Field(0, description="Suma total de tokens consumidos")
    completion_time: Optional[float] = Field(None, description="Tiempo de generación")
    prompt_time: Optional[float] = Field(None, description="Tiempo de procesamiento del prompt")
    queue_time: Optional[float] = Field(None, description="Tiempo de espera en la cola de Groq")
    total_time: Optional[float] = Field(None, description="Tiempo total de la operación")

    class Config:
        # Permite que si el proveedor añade campos nuevos en el JSON, no rompa la validación
        extra = "allow"


# --- ESQUEMAS PARA CHAT_MESSAGE ---

class ChatMessageCreate(BaseModel):
    """Esquema de entrada: Lo que envía el cliente al mandar un nuevo mensaje."""
    message: str = Field(..., min_length=1, description="Contenido del mensaje enviado por el usuario")


class ChatMessageResponse(BaseModel):
    """Esquema de salida: Lo que la API devuelve al cliente sobre un mensaje."""
    id: int = Field(..., description="ID interno del mensaje (útil para ordenación en UI)")
    message: str
    type: ChatMessageType
    model: Optional[str] = None
    usage: Optional[LLMUsageMetadata] = None
    created_date: datetime

    class Config:
        # Configuración para SQLAlchemy 2.0 (antiguo orm_mode=True)
        # Permite a Pydantic leer atributos directamente de tus objetos de la base de datos
        from_attributes = True


# --- ESQUEMAS PARA CHAT (SESIÓN) ---

class ChatCreate(BaseModel):
    """Esquema de entrada: Habitualmente vacío ya que el chat genera su UUID solo."""
    pass


class ChatResponse(BaseModel):
    """Esquema de salida: Datos globales de la sesión de chat."""
    uuid: UUID4 = Field(..., description="Identificador público y seguro de la sesión")
    created_date: datetime
    updated_date: datetime

    class Config:
        from_attributes = True


class ChatDetailResponse(ChatResponse):
    """Esquema de salida extendido: Devuelve el chat junto con todo su historial de mensajes."""
    messages: List[ChatMessageResponse] = []

    class Config:
        from_attributes = True
