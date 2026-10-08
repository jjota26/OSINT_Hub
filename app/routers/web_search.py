from fastapi import APIRouter, Query, Request
from app.services.searxng_service import execute_web_search
from app.core.limiter import limiter
from app.core.config import settings

router = APIRouter(prefix="/api/search", tags=["Busca Web"])

@router.get("/web")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def web_search(
    request: Request,
    q: str = Query(..., description="Termo de pesquisa, nome ou email"),
    categories: str = Query("general", description="general, news, social_media, etc.")
):
    """Pesquisa web via SearXNG ou motor de busca meta-fallback."""
    return await execute_web_search(query=q, categories=categories)
