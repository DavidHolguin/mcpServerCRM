from pydantic_settings import BaseSettings
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    PROJECT_NAME: str = "CRM IA MCP Server"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # Configuración de Supabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    SUPABASE_JWT_SECRET: str = os.getenv("SUPABASE_JWT_SECRET", "")
    
    # URL de la base de datos PostgreSQL
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/crm_ia_db"
    )
    
    # Configuración MCP
    MCP_SERVER_ID: str = "crm-ia-mcp"
    MCP_VERSION: str = "1.0.0"
    
    # Configuración LLM
    DEFAULT_LLM_PROVIDER: str = os.getenv("DEFAULT_LLM_PROVIDER", "openai")
    DEFAULT_LLM_MODEL: str = os.getenv("DEFAULT_LLM_MODEL", "gpt-4")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    
    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()