# Servidor MCP para CRM con IA

Este servidor implementa el Protocolo de Contexto de Modelo (MCP) para proporcionar una capa segura de procesamiento de datos entre el CRM y los modelos de lenguaje (LLM).

## Características Principales

### 1. Seguridad de Datos
- Anonimización automática de datos personales
- Sistema de tokens para mantener la trazabilidad sin exponer información sensible
- Validación de datos antes del procesamiento con LLMs

### 2. Integración con Chatbots
- Manejo de contexto conversacional
- Sistema de Q&A con retroalimentación
- Evaluación continua de calidad de respuestas

### 3. Análisis de Leads
- Evaluación automática de potencial
- Seguimiento de interacciones
- Métricas de engagement
- Todo sin exponer datos personales

## Configuración

1. Crear archivo `.env` con las siguientes variables:
```env
SECRET_KEY="your-secure-secret-key"
DATABASE_URL="your-supabase-postgres-url"
SUPABASE_URL="your-supabase-url"
SUPABASE_KEY="your-supabase-key"
SUPABASE_JWT_SECRET="your-jwt-secret"
DEFAULT_LLM_PROVIDER="openai"
DEFAULT_LLM_MODEL="gpt-4"
LLM_API_KEY="your-openai-api-key"
```

2. Instalar dependencias:
```bash
pip install -r requirements.txt
```

3. Iniciar el servidor:
```bash
uvicorn app.main:app --reload
```

## Endpoints

### Tokens y Autenticación
- POST `/api/v1/tokens/generate`: Genera tokens de acceso

### Mensajes
- POST `/api/v1/messages/sanitize`: Sanitiza mensajes para procesamiento
- POST `/api/v1/chatbot/context`: Gestiona contexto del chatbot
- POST `/api/v1/qa-pairs`: Crea pares de pregunta-respuesta
- POST `/api/v1/evaluate`: Evalúa mensajes con LLM

### Análisis
- POST `/api/v1/analyze-lead`: Analiza leads de forma segura
- GET `/api/v1/lead-metrics/{lead_id}`: Obtiene métricas históricas

## Arquitectura de Seguridad

1. **Capa de Anonimización**
   - Sanitización de datos personales
   - Generación de tokens anónimos
   - Validación de contenido

2. **Capa de Contexto**
   - Manejo de contexto conversacional
   - Sistema de Q&A
   - Historial sanitizado

3. **Capa de Análisis**
   - Evaluación de leads
   - Métricas y seguimiento
   - Reportes agregados

## Integración con Base de Datos

El servidor utiliza Supabase como backend, con las siguientes tablas principales:

- `mensajes_sanitizados`: Almacena versiones sanitizadas de mensajes
- `contexto_conversacional`: Mantiene el contexto de conversaciones
- `pii_tokens`: Gestiona tokens anónimos
- `chatbot_contextos`: Configuración de chatbots
- `qa_pares`: Pares pregunta-respuesta para entrenamiento
- `evaluaciones_llm`: Resultados de evaluaciones

## Mejoras Continuas

El sistema incluye:
- Evaluación automática de calidad de respuestas
- Retroalimentación para mejora continua
- Métricas de rendimiento del LLM