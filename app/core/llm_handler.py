from typing import Dict, Any, List, Optional
import openai
from .config import settings
from sqlalchemy.orm import Session

class LLMHandler:
    def __init__(self):
        self.provider = settings.DEFAULT_LLM_PROVIDER
        self.model = settings.DEFAULT_LLM_MODEL
        openai.api_key = settings.LLM_API_KEY

    async def process_prompt(
        self,
        prompt_template: str,
        context: Dict[str, Any],
        system_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Procesa un prompt con el LLM configurado, asegurando que no se envíen datos personales
        """
        try:
            messages = []
            
            # Añadir contexto del sistema si existe
            if system_context:
                messages.append({
                    "role": "system",
                    "content": system_context
                })
            
            # Añadir el contexto procesado
            context_str = str(context)
            messages.append({
                "role": "user",
                "content": f"{prompt_template}\n\nContexto:\n{context_str}"
            })
            
            # Realizar la llamada al LLM
            response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=2000
            )
            
            # Procesar la respuesta
            content = response.choices[0].message.content
            
            # Intentar estructurar la respuesta
            try:
                import json
                structured_content = json.loads(content)
            except:
                structured_content = {
                    "raw_response": content,
                    "score_potencial": 0.0,
                    "score_satisfaccion": 0.0,
                    "palabras_clave": [],
                    "interes_productos": {}
                }
            
            return {
                "success": True,
                "content": structured_content,
                "metadata": {
                    "model": self.model,
                    "provider": self.provider,
                    "tokens_used": response.usage.total_tokens
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "content": {
                    "score_potencial": 0.0,
                    "score_satisfaccion": 0.0,
                    "palabras_clave": [],
                    "interes_productos": {}
                }
            }

    async def evaluate_conversation(
        self,
        conversation_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evalúa una conversación completa para determinar el potencial del lead
        """
        system_context = """Eres un analista experto en evaluación de leads. 
        Tu tarea es analizar la conversación proporcionada y evaluar:
        1. El potencial del lead (0.0 a 1.0)
        2. El nivel de satisfacción actual (0.0 a 1.0)
        3. Interés en productos específicos
        4. Palabras clave relevantes
        
        IMPORTANTE: No uses ni reveles información personal en tu análisis.
        Céntrate en patrones de comportamiento e intereses."""
        
        evaluation_prompt = """Analiza el siguiente contexto conversacional y proporciona:
        {
            "score_potencial": float,
            "score_satisfaccion": float,
            "interes_productos": {
                "producto_name": float  // nivel de interés de 0 a 1
            },
            "palabras_clave": ["keyword1", "keyword2"],
            "analisis": "Breve análisis sin datos personales"
        }"""
        
        return await self.process_prompt(
            prompt_template=evaluation_prompt,
            context=conversation_context,
            system_context=system_context
        )

    def process_message(
        self,
        db: Session,
        chatbot_id: int,
        token_anonimo: str,
        contenido_sanitizado: str
    ) -> Dict[str, Any]:
        """
        Procesa un mensaje de un usuario y genera una respuesta utilizando el chatbot configurado
        
        Args:
            db: Sesión de base de datos
            chatbot_id: ID del chatbot que procesará el mensaje
            token_anonimo: Token anónimo del lead
            contenido_sanitizado: Contenido del mensaje sanitizado
            
        Returns:
            Dict con la respuesta del chatbot
        """
        try:
            from ..models.chat import Chatbot, ChatbotContexto, ContextoConversacional
            
            # Obtener configuración del chatbot
            chatbot = db.query(Chatbot).filter(Chatbot.id == chatbot_id).first()
            if not chatbot:
                return {
                    "success": False,
                    "error": "Chatbot no encontrado",
                    "respuesta": "Lo siento, no puedo procesar tu mensaje en este momento."
                }
                
            # Obtener contexto del chatbot
            chatbot_context = db.query(ChatbotContexto).filter(
                ChatbotContexto.chatbot_id == chatbot_id
            ).order_by(ChatbotContexto.orden).all()
            
            # Construir sistema de contexto
            system_context = f"""Eres un asistente virtual para {chatbot.nombre}. 
            
            PERSONALIDAD: {chatbot.personalidad or 'Amigable y profesional'}
            
            TONO: {chatbot.tono or 'Formal pero cercano'}
            
            INSTRUCCIONES: {chatbot.instrucciones or 'Responde de manera útil y concisa'}
            
            CONTEXTO: {chatbot.contexto or 'Eres un asistente virtual de atención al cliente'}
            
            IMPORTANTE: Nunca reveles que eres una IA. Responde como si fueras un agente humano representando a la empresa.
            """
            
            # Añadir contexto adicional de ChatbotContexto si está disponible
            for ctx in chatbot_context:
                if ctx.general_context:
                    system_context += f"\n\n{ctx.general_context}"
                if ctx.special_instructions:
                    system_context += f"\n\nINSTRUCCIONES ESPECIALES: {ctx.special_instructions}"
            
            # Obtener historial de conversación reciente
            conversation_history = db.query(ContextoConversacional).filter(
                ContextoConversacional.token_anonimo == token_anonimo
            ).order_by(ContextoConversacional.created_at.desc()).limit(10).all()
            
            # Construir mensajes para el LLM
            messages = [
                {"role": "system", "content": system_context}
            ]
            
            # Añadir historia conversacional
            for msg in reversed(conversation_history):
                role = "user" if msg.tipo_contexto == "mensaje_usuario" else "assistant"
                messages.append({
                    "role": role,
                    "content": msg.contenido_sanitizado
                })
                
            # Añadir mensaje actual
            messages.append({
                "role": "user", 
                "content": contenido_sanitizado
            })
            
            # Realizar llamada a la API
            response = openai.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            respuesta_contenido = response.choices[0].message.content
            
            # Registrar respuesta en contexto conversacional
            from ..models.chat import ContextoConversacional
            nuevo_contexto = ContextoConversacional(
                token_anonimo=token_anonimo,
                tipo_contexto="respuesta_chatbot",
                contenido_sanitizado=respuesta_contenido,
                relevancia_score=1.0
            )
            db.add(nuevo_contexto)
            db.commit()
            
            return {
                "success": True,
                "respuesta": respuesta_contenido,
                "metadata": {
                    "model": self.model,
                    "provider": self.provider,
                    "tokens_used": response.usage.total_tokens
                }
            }
        
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc(),
                "respuesta": "Lo siento, ha ocurrido un error al procesar tu mensaje. Por favor, inténtalo de nuevo más tarde."
            }