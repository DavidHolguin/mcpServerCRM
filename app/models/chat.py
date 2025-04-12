from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, JSON, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class MensajeSanitizado(Base):
    __tablename__ = "mensajes_sanitizados"
    
    id = Column(Integer, primary_key=True)
    mensaje_id = Column(Integer, ForeignKey("mensajes.id"))
    token_anonimo = Column(String)
    contenido_sanitizado = Column(String)
    metadata_sanitizada = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

class ContextoConversacional(Base):
    __tablename__ = "contexto_conversacional"
    
    id = Column(Integer, primary_key=True)
    token_anonimo = Column(String)
    tipo_contexto = Column(String)
    contenido_sanitizado = Column(String)
    relevancia_score = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PIIToken(Base):
    __tablename__ = "pii_tokens"
    
    id = Column(Integer, primary_key=True)
    lead_id = Column(Integer, ForeignKey("leads.id"))
    token_anonimo = Column(String, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    is_active = Column(Boolean, default=True)

class ChatbotContexto(Base):
    __tablename__ = "chatbot_contextos"
    
    id = Column(Integer, primary_key=True)
    chatbot_id = Column(Integer, ForeignKey("chatbots.id"))
    tipo = Column(String)
    contenido = Column(String)
    orden = Column(Integer)
    welcome_message = Column(String)
    personality = Column(String)
    general_context = Column(String)
    communication_tone = Column(String)
    main_purpose = Column(String)
    key_points = Column(JSON)
    special_instructions = Column(String)
    prompt_template = Column(String)
    qa_examples = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class QAPar(Base):
    __tablename__ = "qa_pares"
    
    id = Column(Integer, primary_key=True)
    chatbot_id = Column(Integer, ForeignKey("chatbots.id"))
    pregunta = Column(String)
    respuesta_ideal = Column(String)
    categoria = Column(String)
    agregado_por = Column(Integer)
    origen_id = Column(Integer)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class EvaluacionLLM(Base):
    __tablename__ = "evaluaciones_llm"
    
    id = Column(Integer, primary_key=True)
    lead_id = Column(Integer, ForeignKey("leads.id"))
    conversacion_id = Column(Integer, ForeignKey("conversaciones.id"))
    mensaje_id = Column(Integer, ForeignKey("mensajes.id"))
    fecha_evaluacion = Column(DateTime, default=datetime.utcnow)
    score_potencial = Column(Float)
    score_satisfaccion = Column(Float)
    interes_productos = Column(JSON)
    comentario = Column(String)
    palabras_clave = Column(JSON)
    llm_configuracion_id = Column(Integer, ForeignKey("llm_configuraciones.id"))
    prompt_utilizado = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)