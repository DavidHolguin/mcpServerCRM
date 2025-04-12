from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .core.config import settings
from .api.api_v1.api import router as api_router
from .core.mcp_handler import MCPHandler

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Servidor MCP para CRM con IA que procesa datos de manera segura",
    version="1.0.0"
)

# Configuración CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializar el manejador MCP
mcp_handler = MCPHandler()

# Incluir rutas de la API
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {"message": "CRM IA MCP Server is running"}