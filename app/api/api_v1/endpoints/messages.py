from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from ....schemas.message import (
    MensajeCreate,
    MensajeSanitizadoResponse,
    ChatbotContextoCreate,
    ChatbotContextoResponse,
    QAPairCreate,
    QAPairResponse,
    EvaluacionCreate,
    EvaluacionResponse,
    ContextoConversacionalCreate
)
from ....core.mcp_handler import MCPHandler
from ....core.database import get_db
import uuid

router = APIRouter()
mcp_handler = MCPHandler()

@router.post("/sanitize", response_model=MensajeSanitizadoResponse)
async def sanitize_message(
    message: MensajeCreate,
    db: Session = Depends(get_db)
):
    """
    Sanitiza un mensaje y lo prepara para procesamiento por LLM
    """
    # Generar token anónimo para el lead si no existe
    token_anonimo = mcp_handler.create_pii_token(db, message.lead_id)
    
    # Sanitizar y guardar mensaje
    mensaje_sanitizado = mcp_handler.save_sanitized_message(
        db=db,
        mensaje_id=uuid.uuid4().int >> 64,  # Generar ID temporal
        token_anonimo=token_anonimo,
        contenido_original=message.contenido,
        metadata=message.metadata or {}
    )
    
    # Actualizar contexto conversacional
    mcp_handler.update_conversation_context(
        db=db,
        token_anonimo=token_anonimo,
        tipo_contexto="mensaje_usuario",
        contenido=mensaje_sanitizado.contenido_sanitizado,
        relevancia=1.0  # Alta relevancia para mensajes recientes
    )
    
    return mensaje_sanitizado

@router.post("/chatbot/context", response_model=ChatbotContextoResponse)
async def create_chatbot_context(
    context: ChatbotContextoCreate,
    db: Session = Depends(get_db)
):
    """
    Crea o actualiza el contexto de un chatbot
    """
    try:
        from ....models.chat import ChatbotContexto
        
        chatbot_context = ChatbotContexto(
            chatbot_id=context.chatbot_id,
            tipo=context.tipo,
            contenido=context.contenido,
            orden=context.orden,
            welcome_message=context.welcome_message,
            personality=context.personality,
            general_context=context.general_context,
            communication_tone=context.communication_tone,
            main_purpose=context.main_purpose,
            key_points=context.key_points,
            special_instructions=context.special_instructions,
            prompt_template=context.prompt_template,
            qa_examples=context.qa_examples
        )
        
        db.add(chatbot_context)
        db.commit()
        db.refresh(chatbot_context)
        return chatbot_context
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/qa-pairs", response_model=QAPairResponse)
async def create_qa_pair(
    qa_pair: QAPairCreate,
    db: Session = Depends(get_db)
):
    """
    Crea un nuevo par pregunta-respuesta para entrenamiento
    """
    try:
        from ....models.chat import QAPar
        
        new_qa = QAPar(
            chatbot_id=qa_pair.chatbot_id,
            pregunta=qa_pair.pregunta,
            respuesta_ideal=qa_pair.respuesta_ideal,
            categoria=qa_pair.categoria,
            agregado_por=qa_pair.agregado_por,
            is_active=True
        )
        
        db.add(new_qa)
        db.commit()
        db.refresh(new_qa)
        return new_qa
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/evaluate", response_model=EvaluacionResponse)
async def evaluate_message(
    evaluacion: EvaluacionCreate,
    db: Session = Depends(get_db)
):
    """
    Evalúa un mensaje usando el LLM configurado
    """
    try:
        # Obtener mensaje sanitizado
        from ....models.chat import MensajeSanitizado
        mensaje = db.query(MensajeSanitizado).filter(
            MensajeSanitizado.mensaje_id == evaluacion.mensaje_id
        ).first()
        
        if not mensaje:
            raise HTTPException(status_code=404, detail="Mensaje no encontrado")
        
        # Realizar evaluación
        eval_result = mcp_handler.evaluate_conversation(
            db=db,
            lead_id=evaluacion.lead_id,
            conversacion_id=evaluacion.conversacion_id,
            mensaje_id=evaluacion.mensaje_id,
            llm_config_id=evaluacion.llm_configuracion_id,
            contenido_sanitizado=mensaje.contenido_sanitizado,
            prompt_template=evaluacion.prompt_utilizado
        )
        
        return eval_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))