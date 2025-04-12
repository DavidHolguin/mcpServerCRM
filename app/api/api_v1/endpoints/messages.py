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
    ContextoConversacionalCreate,
    # Nuevos esquemas
    ChatbotActivacionCreate,
    ChatbotActivacionResponse,
    MensajeFrontendCreate,
    MensajeFrontendResponse
)
from ....core.mcp_handler import MCPHandler
from ....core.database import get_db
from ....core.llm_handler import LLMHandler
import uuid
from datetime import datetime

router = APIRouter()
mcp_handler = MCPHandler()
llm_handler = LLMHandler()

@router.post("/sanitize", response_model=MensajeSanitizadoResponse)
async def sanitize_message(
    message: MensajeCreate,
    db: Session = Depends(get_db)
):
    """
    Sanitiza un mensaje, lo procesa con el LLM y devuelve tanto el mensaje sanitizado como la respuesta del LLM.
    Todo en una sola llamada.
    """
    try:
        from ....models.chat import Conversacion, Mensaje, Chatbot
        
        # Verificar si existe una conversación activa
        conversacion = db.query(Conversacion).filter(
            Conversacion.lead_id == message.lead_id,
            Conversacion.chatbot_id == message.chatbot_id,
            Conversacion.estado == "activo"
        ).first()
        
        # Si no existe conversación, crearla
        if not conversacion:
            conversacion = Conversacion(
                lead_id=message.lead_id,
                chatbot_id=message.chatbot_id,
                canal_id=message.canal_id,
                estado="activo",
                chatbot_activo=True,
                ultimo_mensaje=datetime.now(),
                metadata={}
            )
            db.add(conversacion)
            db.commit()
            db.refresh(conversacion)
        
        # 1. Generar token anónimo para el lead si no existe
        token_anonimo = mcp_handler.create_pii_token(db, message.lead_id)
        
        # 2. Sanitizar el mensaje - IMPORTANTE: Este es el paso clave
        mensaje_sanitizado = mcp_handler.save_sanitized_message(
            db=db,
            mensaje_id=uuid.uuid4().int >> 64,  # ID temporal que se actualizará después
            token_anonimo=token_anonimo,
            contenido_original=message.contenido,
            metadata=message.metadata or {}
        )
        
        # 3. Guardar el mensaje con el contenido original en la tabla de mensajes
        mensaje_usuario = Mensaje(
            conversacion_id=conversacion.id,
            origen="usuario",
            remitente_id=message.lead_id,
            contenido=message.contenido,  # Contenido original
            tipo_contenido="texto",
            metadata=message.metadata or {},
            leido=False,
            created_at=datetime.now()
        )
        db.add(mensaje_usuario)
        db.commit()
        db.refresh(mensaje_usuario)
        
        # 4. Actualizar el ID del mensaje sanitizado con el ID real del mensaje
        from ....models.chat import MensajeSanitizado
        db.query(MensajeSanitizado).filter(
            MensajeSanitizado.id == mensaje_sanitizado.id
        ).update({
            "mensaje_id": mensaje_usuario.id
        })
        db.commit()
        
        # 5. Actualizar timestamp de último mensaje en la conversación
        conversacion.ultimo_mensaje = datetime.now()
        db.commit()
        
        # 6. Actualizar contexto conversacional con el CONTENIDO SANITIZADO
        mcp_handler.update_conversation_context(
            db=db,
            token_anonimo=token_anonimo,
            tipo_contexto="mensaje_usuario",
            contenido=mensaje_sanitizado.contenido_sanitizado,  # Usamos el contenido sanitizado
            relevancia=1.0  # Alta relevancia para mensajes recientes
        )
        
        # 7. Verificar si el chatbot está activo para esta conversación
        if not conversacion.chatbot_activo:
            # Si el chatbot no está activo, devolvemos solo el mensaje sanitizado sin respuesta LLM
            return MensajeSanitizadoResponse(
                id=mensaje_sanitizado.id,
                token_anonimo=mensaje_sanitizado.token_anonimo,
                contenido_sanitizado=mensaje_sanitizado.contenido_sanitizado,
                metadata_sanitizada=mensaje_sanitizado.metadata_sanitizada,
                created_at=mensaje_sanitizado.created_at
            )
        
        # 8. Procesar con el LLM si el chatbot está activo
        # IMPORTANTE: Pasamos el contenido sanitizado al LLM
        respuesta_llm = llm_handler.process_message(
            db=db,
            chatbot_id=message.chatbot_id,
            token_anonimo=token_anonimo,
            contenido_sanitizado=mensaje_sanitizado.contenido_sanitizado  # Usamos el contenido sanitizado
        )
        
        # 9. Guardar la respuesta del LLM como mensaje en la base de datos
        mensaje_respuesta = Mensaje(
            conversacion_id=conversacion.id,
            origen="chatbot",
            remitente_id=message.chatbot_id,
            contenido=respuesta_llm["respuesta"],
            tipo_contenido="texto",
            metadata=respuesta_llm.get("metadata", {}),
            leido=False,
            created_at=datetime.now()
        )
        db.add(mensaje_respuesta)
        db.commit()
        db.refresh(mensaje_respuesta)
        
        # 10. Actualizar timestamp de último mensaje en la conversación
        conversacion.ultimo_mensaje = datetime.now()
        db.commit()
        
        # 11. Devolver respuesta completa
        return MensajeSanitizadoResponse(
            id=mensaje_sanitizado.id,
            token_anonimo=mensaje_sanitizado.token_anonimo,
            contenido_sanitizado=mensaje_sanitizado.contenido_sanitizado,
            metadata_sanitizada=mensaje_sanitizado.metadata_sanitizada,
            created_at=mensaje_sanitizado.created_at,
            llm_respuesta=respuesta_llm["respuesta"],
            llm_mensaje_id=mensaje_respuesta.id,
            llm_metadata=respuesta_llm.get("metadata", {})
        )
        
    except Exception as e:
        db.rollback()
        import traceback
        error_detail = traceback.format_exc()
        raise HTTPException(status_code=500, detail=f"Error al procesar el mensaje: {str(e)}\n{error_detail}")

@router.post("/activar-chatbot", response_model=ChatbotActivacionResponse)
async def activar_chatbot_lead(
    activacion: ChatbotActivacionCreate,
    db: Session = Depends(get_db)
):
    """
    Activa o desactiva un chatbot para un lead específico (pago).
    Si no existe una conversación con ese chatbot, crea una nueva.
    """
    try:
        # Verificar si el lead existe
        from ....models.chat import Lead, Chatbot, Conversacion
        
        lead = db.query(Lead).filter(Lead.id == activacion.lead_id).first()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead no encontrado")
        
        chatbot = db.query(Chatbot).filter(Chatbot.id == activacion.chatbot_id).first()
        if not chatbot:
            raise HTTPException(status_code=404, detail="Chatbot no encontrado")
        
        # Buscar si ya existe una conversación entre este lead y chatbot
        conversacion = db.query(Conversacion).filter(
            Conversacion.lead_id == activacion.lead_id,
            Conversacion.chatbot_id == activacion.chatbot_id
        ).first()
        
        if not conversacion:
            # Crear nueva conversación
            conversacion = Conversacion(
                lead_id=activacion.lead_id,
                chatbot_id=activacion.chatbot_id,
                estado="activo" if activacion.estado else "inactivo",
                chatbot_activo=activacion.estado,
                ultimo_mensaje=datetime.now(),
                metadata=activacion.metadata or {}
            )
            db.add(conversacion)
            db.commit()
            db.refresh(conversacion)
        else:
            # Actualizar conversación existente
            conversacion.chatbot_activo = activacion.estado
            conversacion.estado = "activo" if activacion.estado else "inactivo"
            conversacion.ultimo_mensaje = datetime.now()
            if activacion.metadata:
                conversacion.metadata = {**conversacion.metadata, **activacion.metadata} if conversacion.metadata else activacion.metadata
            db.commit()
            db.refresh(conversacion)
        
        # Preparar respuesta
        response = ChatbotActivacionResponse(
            lead_id=activacion.lead_id,
            chatbot_id=activacion.chatbot_id,
            conversacion_id=conversacion.id,
            estado=conversacion.chatbot_activo,
            created_at=conversacion.created_at,
            updated_at=datetime.now()
        )
        
        return response
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/send-message", response_model=MensajeFrontendResponse)
async def send_message_from_frontend(
    mensaje: MensajeFrontendCreate,
    db: Session = Depends(get_db)
):
    """
    Envía un mensaje desde el frontend (agente humano) a un lead específico.
    Automáticamente desactiva el chatbot para esta conversación.
    """
    try:
        # Verificar que el lead existe
        from ....models.chat import Lead, Conversacion, Mensaje, Chatbot
        
        lead = db.query(Lead).filter(Lead.id == mensaje.lead_id).first()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead no encontrado")
        
        # Buscar la conversación activa para este lead
        conversacion = db.query(Conversacion).filter(
            Conversacion.lead_id == mensaje.lead_id,
            Conversacion.estado == "activo"
        ).order_by(Conversacion.ultimo_mensaje.desc()).first()
        
        if not conversacion:
            raise HTTPException(status_code=404, detail="No hay conversaciones activas para este lead")
        
        # Desactivar el chatbot automáticamente cuando un agente humano envía un mensaje
        if conversacion.chatbot_activo:
            conversacion.chatbot_activo = False
            db.commit()
        
        # Guardar el mensaje enviado desde el frontend (agente humano)
        nuevo_mensaje = Mensaje(
            conversacion_id=conversacion.id,
            origen="agente",
            remitente_id=None,  # Este campo puede ser el ID del agente si está disponible
            contenido=mensaje.contenido,
            tipo_contenido=mensaje.tipo_contenido,
            metadata=mensaje.metadata or {},
            leido=False,
            created_at=datetime.now()
        )
        
        db.add(nuevo_mensaje)
        db.commit()
        db.refresh(nuevo_mensaje)
        
        # Actualizar último mensaje de la conversación
        conversacion.ultimo_mensaje = datetime.now()
        db.commit()
        
        # Preparar respuesta
        response = MensajeFrontendResponse(
            id=nuevo_mensaje.id,
            conversacion_id=conversacion.id,
            contenido=nuevo_mensaje.contenido,
            origen=nuevo_mensaje.origen,
            remitente_id=nuevo_mensaje.remitente_id,
            tipo_contenido=nuevo_mensaje.tipo_contenido,
            created_at=nuevo_mensaje.created_at,
            respuesta_chatbot=None  # No hay respuesta de chatbot ya que se desactivó
        )
        
        return response
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

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