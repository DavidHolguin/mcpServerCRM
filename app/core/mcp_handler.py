from typing import Dict, Any, List, Optional
import hashlib
import json
from datetime import datetime
from sqlalchemy.orm import Session
from ..models.chat import (
    MensajeSanitizado,
    ContextoConversacional,
    PIIToken,
    ChatbotContexto,
    QAPar,
    EvaluacionLLM
)
from .llm_handler import LLMHandler

class MCPHandler:
    def __init__(self):
        self.sensitive_fields = {
            'email', 'first_name', 'last_name', 'phone', 'viewer_ip',
            'viewer_profile_id', 'profile_id', 'user_id', 'nombre',
            'apellido', 'telefono', 'direccion', 'ciudad', 'pais'
        }
        self.llm_handler = LLMHandler()

    def create_pii_token(self, db: Session, lead_id: int) -> str:
        """Crea un token anónimo para un lead"""
        token = hashlib.sha256(f"{lead_id}-{datetime.utcnow().timestamp()}".encode()).hexdigest()
        pii_token = PIIToken(
            lead_id=lead_id,
            token_anonimo=token,
            expires_at=datetime.utcnow()
        )
        db.add(pii_token)
        db.commit()
        return token

    def anonymize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Anonimiza datos sensibles reemplazándolos con hashes"""
        anonymized = {}
        for key, value in data.items():
            if key in self.sensitive_fields and value:
                anonymized[key] = hashlib.sha256(str(value).encode()).hexdigest()[:16]
            elif isinstance(value, dict):
                anonymized[key] = self.anonymize_data(value)
            elif isinstance(value, list):
                anonymized[key] = [
                    self.anonymize_data(item) if isinstance(item, dict) else item 
                    for item in value
                ]
            else:
                anonymized[key] = value
        return anonymized

    def extract_profile_analytics(self, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extrae datos analíticos relevantes sin información personal"""
        analytics = {
            "timestamp": datetime.now().isoformat(),
            "academic_info": {
                "university_id": profile_data.get("university_id"),
                "faculty_id": profile_data.get("faculty_id"),
                "program_id": profile_data.get("program_id"),
                "graduation_year": profile_data.get("graduation_date", "")[:4] if profile_data.get("graduation_date") else None
            },
            "skills": [
                {"name": skill["name"], "category": skill["category"], "proficiency": skill["proficiency"]}
                for skill in profile_data.get("skills", [])
            ],
            "experience_count": len(profile_data.get("work_experience", [])),
            "certification_count": len(profile_data.get("certifications", [])),
            "publication_count": len(profile_data.get("publications", [])),
            "awards_count": len(profile_data.get("awards", []))
        }
        return analytics

    def prepare_data_for_llm(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepara los datos para ser procesados por el LLM"""
        # Primero anonimizamos los datos
        anonymized_data = self.anonymize_data(data)
        
        # Extraemos métricas y análisis relevantes
        analytics = self.extract_profile_analytics(data)
        
        # Preparamos el contexto para el LLM
        llm_context = {
            "analytics": analytics,
            "anonymized_data": anonymized_data,
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "data_version": "1.0",
                "context_type": "crm_profile_analysis"
            }
        }
        
        return llm_context

    def prepare_chatbot_context(
        self, 
        db: Session, 
        chatbot_id: int,
        conversation_token: str
    ) -> Dict[str, Any]:
        """Prepara el contexto del chatbot incluyendo QA pairs relevantes"""
        context = db.query(ChatbotContexto).filter(
            ChatbotContexto.chatbot_id == chatbot_id
        ).order_by(ChatbotContexto.orden).all()

        qa_pairs = db.query(QAPar).filter(
            QAPar.chatbot_id == chatbot_id,
            QAPar.is_active == True
        ).all()

        conversation_context = db.query(ContextoConversacional).filter(
            ContextoConversacional.token_anonimo == conversation_token
        ).order_by(
            ContextoConversacional.relevancia_score.desc()
        ).limit(5).all()

        return {
            "base_context": [
                {
                    "tipo": ctx.tipo,
                    "contenido": ctx.contenido,
                    "instrucciones": ctx.special_instructions,
                    "tono": ctx.communication_tone,
                    "personalidad": ctx.personality
                }
                for ctx in context
            ],
            "qa_examples": [
                {
                    "pregunta": qa.pregunta,
                    "respuesta": qa.respuesta_ideal
                }
                for qa in qa_pairs
            ],
            "conversation_history": [
                {
                    "tipo": ctx.tipo_contexto,
                    "contenido": ctx.contenido_sanitizado,
                    "relevancia": ctx.relevancia_score
                }
                for ctx in conversation_context
            ]
        }

    def save_sanitized_message(
        self,
        db: Session,
        mensaje_id: int,
        token_anonimo: str,
        contenido_original: str,
        metadata: Dict[str, Any]
    ) -> MensajeSanitizado:
        """Guarda una versión sanitizada del mensaje"""
        sanitized_content = self.anonymize_data({"content": contenido_original})["content"]
        sanitized_metadata = self.anonymize_data(metadata)

        mensaje_sanitizado = MensajeSanitizado(
            mensaje_id=mensaje_id,
            token_anonimo=token_anonimo,
            contenido_sanitizado=sanitized_content,
            metadata_sanitizada=sanitized_metadata
        )
        db.add(mensaje_sanitizado)
        db.commit()
        return mensaje_sanitizado

    async def evaluate_conversation(
        self,
        db: Session,
        lead_id: int,
        conversacion_id: int,
        mensaje_id: int,
        llm_config_id: int,
        contenido_sanitizado: str,
        prompt_template: str
    ) -> EvaluacionLLM:
        """Evalúa una conversación usando el LLM configurado"""
        # Preparar el contexto para el LLM
        context = {
            "contenido_sanitizado": contenido_sanitizado,
            "metadata": {
                "conversation_id": conversacion_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        # Obtener evaluación del LLM
        llm_response = await self.llm_handler.evaluate_conversation(context)
        
        # Crear la evaluación
        evaluacion = EvaluacionLLM(
            lead_id=lead_id,
            conversacion_id=conversacion_id,
            mensaje_id=mensaje_id,
            score_potencial=llm_response["content"]["score_potencial"],
            score_satisfaccion=llm_response["content"]["score_satisfaccion"],
            interes_productos=llm_response["content"]["interes_productos"],
            palabras_clave=llm_response["content"]["palabras_clave"],
            llm_configuracion_id=llm_config_id,
            prompt_utilizado=prompt_template
        )
        
        db.add(evaluacion)
        db.commit()
        return evaluacion

    def update_conversation_context(
        self,
        db: Session,
        token_anonimo: str,
        tipo_contexto: str,
        contenido: str,
        relevancia: float
    ) -> ContextoConversacional:
        """Actualiza el contexto de la conversación"""
        contexto = ContextoConversacional(
            token_anonimo=token_anonimo,
            tipo_contexto=tipo_contexto,
            contenido_sanitizado=contenido,
            relevancia_score=relevancia
        )
        db.add(contexto)
        db.commit()
        return contexto

    def validate_tokens(self, tokens: List[str]) -> bool:
        """Valida que los tokens no contengan información personal"""
        # Implementar validación de tokens aquí
        return True