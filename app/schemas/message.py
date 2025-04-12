from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime

class TokenBase(BaseModel):
    token_anonimo: str

class MensajeBase(BaseModel):
    contenido: str
    metadata: Optional[Dict[str, Any]] = None

class MensajeCreate(MensajeBase):
    lead_id: int
    chatbot_id: int
    canal_id: Optional[int] = None

class MensajeSanitizadoResponse(BaseModel):
    id: int
    token_anonimo: str
    contenido_sanitizado: str
    metadata_sanitizada: Dict[str, Any]
    created_at: datetime
    # Campos adicionales para la respuesta del LLM
    llm_respuesta: Optional[str] = None
    llm_mensaje_id: Optional[int] = None
    llm_metadata: Optional[Dict[str, Any]] = None

# Nuevos esquemas para activar chatbot y enviar mensajes
class ChatbotActivacionCreate(BaseModel):
    lead_id: int
    chatbot_id: int
    estado: bool = True
    metadata: Optional[Dict[str, Any]] = None

class ChatbotActivacionResponse(BaseModel):
    lead_id: int
    chatbot_id: int
    conversacion_id: int
    estado: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

class MensajeFrontendCreate(BaseModel):
    lead_id: int
    contenido: str
    canal_id: Optional[int] = None
    tipo_contenido: str = "texto"
    metadata: Optional[Dict[str, Any]] = None
    
class MensajeFrontendResponse(BaseModel):
    id: int
    conversacion_id: int
    contenido: str
    origen: str
    remitente_id: Optional[int] = None
    tipo_contenido: str
    created_at: datetime
    respuesta_chatbot: Optional[Dict[str, Any]] = None

class ChatbotContextoBase(BaseModel):
    tipo: str
    contenido: str
    orden: Optional[int] = None
    welcome_message: Optional[str] = None
    personality: Optional[str] = None
    general_context: Optional[str] = None
    communication_tone: Optional[str] = None
    main_purpose: Optional[str] = None
    key_points: Optional[Dict[str, Any]] = None
    special_instructions: Optional[str] = None
    prompt_template: Optional[str] = None
    qa_examples: Optional[List[Dict[str, str]]] = None

class ChatbotContextoCreate(ChatbotContextoBase):
    chatbot_id: int

class ChatbotContextoResponse(ChatbotContextoBase):
    id: int
    created_at: datetime
    updated_at: datetime

class QAPairBase(BaseModel):
    pregunta: str
    respuesta_ideal: str
    categoria: Optional[str] = None

class QAPairCreate(QAPairBase):
    chatbot_id: int
    agregado_por: int

class QAPairResponse(QAPairBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

class EvaluacionBase(BaseModel):
    score_potencial: float = Field(..., ge=0.0, le=1.0)
    score_satisfaccion: float = Field(..., ge=0.0, le=1.0)
    interes_productos: Dict[str, Any]
    comentario: Optional[str] = None
    palabras_clave: List[str]

class EvaluacionCreate(EvaluacionBase):
    lead_id: int
    conversacion_id: int
    mensaje_id: int
    llm_configuracion_id: int
    prompt_utilizado: str

class EvaluacionResponse(EvaluacionBase):
    id: int
    fecha_evaluacion: datetime
    created_at: datetime
    updated_at: datetime

class ContextoConversacionalBase(BaseModel):
    tipo_contexto: str
    contenido_sanitizado: str
    relevancia_score: float = Field(..., ge=0.0, le=1.0)

class ContextoConversacionalCreate(ContextoConversacionalBase):
    token_anonimo: str

class ContextoConversacionalResponse(ContextoConversacionalBase):
    id: int
    created_at: datetime
    updated_at: datetime