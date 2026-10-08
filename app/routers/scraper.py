from fastapi import APIRouter, Query, Request, HTTPException
from app.services.scraper_service import scrape_target_url
from app.core.limiter import limiter
from app.core.config import settings

router = APIRouter(prefix="/api/scraper", tags=["Scraper & Extração"])

@router.get("/extract")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def extract_contacts(
    request: Request,
    url: str = Query(..., description="URL da página a analisar")
):
    """Extrai emails, telefones e redes sociais de um website específico."""
    try:
        return await scrape_target_url(url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao extrair dados da página: {str(e)}")
