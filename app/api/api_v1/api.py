from fastapi import APIRouter
from .endpoints import tokens, messages, analytics

router = APIRouter()

# Incluir los routers de los diferentes endpoints
router.include_router(tokens.router, prefix="/tokens", tags=["tokens"])
router.include_router(messages.router, prefix="/messages", tags=["messages"])
router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])

@router.get("/health-check")
async def health_check():
    return {"status": "ok"}