from typing import Dict, Any, List, Optional
import openai
from .config import settings

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