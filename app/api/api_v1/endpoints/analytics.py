from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from ....core.mcp_handler import MCPHandler
from ....core.database import get_db
from ....schemas.message import EvaluacionCreate, EvaluacionResponse
from datetime import datetime

router = APIRouter()
mcp_handler = MCPHandler()

@router.post("/analyze-lead", response_model=Dict[str, Any])
async def analyze_lead(
    lead_id: int,
    db: Session = Depends(get_db)
):
    """
    Analiza un lead usando el sistema MCP para generar insights sin exponer datos personales
    """
    try:
        # Buscar el token anónimo existente o crear uno nuevo
        from ....models.chat import PIIToken
        pii_token = db.query(PIIToken).filter(
            PIIToken.lead_id == lead_id,
            PIIToken.is_active == True
        ).first()
        
        if not pii_token:
            token_anonimo = mcp_handler.create_pii_token(db, lead_id)
        else:
            token_anonimo = pii_token.token_anonimo
        
        # Obtener datos del lead de manera segura
        from ....models.chat import MensajeSanitizado, ContextoConversacional
        mensajes = db.query(MensajeSanitizado).filter(
            MensajeSanitizado.token_anonimo == token_anonimo
        ).all()
        
        contexto = db.query(ContextoConversacional).filter(
            ContextoConversacional.token_anonimo == token_anonimo
        ).order_by(ContextoConversacional.relevancia_score.desc()).all()
        
        # Preparar datos para análisis
        data_for_analysis = {
            "mensajes_sanitizados": [
                {
                    "contenido": msg.contenido_sanitizado,
                    "metadata": msg.metadata_sanitizada,
                    "timestamp": msg.created_at.isoformat()
                }
                for msg in mensajes
            ],
            "contexto_relevante": [
                {
                    "tipo": ctx.tipo_contexto,
                    "contenido": ctx.contenido_sanitizado,
                    "relevancia": ctx.relevancia_score
                }
                for ctx in contexto
            ]
        }
        
        # Procesar con el LLM
        llm_context = mcp_handler.prepare_data_for_llm(data_for_analysis)
        
        # Realizar evaluación
        evaluacion = EvaluacionCreate(
            lead_id=lead_id,
            conversacion_id=0,  # Se puede actualizar si es necesario
            mensaje_id=0,  # Se puede actualizar si es necesario
            llm_configuracion_id=1,  # Usar configuración por defecto
            prompt_utilizado="Análisis completo de lead",
            score_potencial=0.0,  # Se actualizará con el resultado del LLM
            score_satisfaccion=0.0,  # Se actualizará con el resultado del LLM
            interes_productos={},  # Se actualizará con el resultado del LLM
            palabras_clave=[]  # Se actualizará con el resultado del LLM
        )
        
        resultado_evaluacion = mcp_handler.evaluate_conversation(
            db=db,
            lead_id=evaluacion.lead_id,
            conversacion_id=evaluacion.conversacion_id,
            mensaje_id=evaluacion.mensaje_id,
            llm_config_id=evaluacion.llm_configuracion_id,
            contenido_sanitizado=str(llm_context),
            prompt_template=evaluacion.prompt_utilizado
        )
        
        return {
            "analysis_id": resultado_evaluacion.id,
            "timestamp": datetime.now().isoformat(),
            "lead_analysis": {
                "score_potencial": resultado_evaluacion.score_potencial,
                "score_satisfaccion": resultado_evaluacion.score_satisfaccion,
                "intereses": resultado_evaluacion.interes_productos,
                "palabras_clave": resultado_evaluacion.palabras_clave,
                "metadata": llm_context["metadata"]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/lead-metrics/{lead_id}", response_model=Dict[str, Any])
async def get_lead_metrics(
    lead_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtiene métricas históricas de un lead de manera segura
    """
    try:
        from ....models.chat import EvaluacionLLM
        evaluaciones = db.query(EvaluacionLLM).filter(
            EvaluacionLLM.lead_id == lead_id
        ).order_by(EvaluacionLLM.fecha_evaluacion.desc()).all()
        
        if not evaluaciones:
            return {
                "message": "No hay evaluaciones disponibles para este lead",
                "evaluaciones": []
            }
        
        return {
            "total_evaluaciones": len(evaluaciones),
            "ultima_evaluacion": evaluaciones[0].fecha_evaluacion.isoformat(),
            "promedio_score_potencial": sum(e.score_potencial for e in evaluaciones) / len(evaluaciones),
            "promedio_score_satisfaccion": sum(e.score_satisfaccion for e in evaluaciones) / len(evaluaciones),
            "historial": [
                {
                    "fecha": e.fecha_evaluacion.isoformat(),
                    "score_potencial": e.score_potencial,
                    "score_satisfaccion": e.score_satisfaccion,
                    "intereses": e.interes_productos,
                    "palabras_clave": e.palabras_clave
                }
                for e in evaluaciones
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))