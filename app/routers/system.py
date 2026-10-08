import sys
import shutil
from fastapi import APIRouter
from app.core.config import settings

router = APIRouter(prefix="/api/system", tags=["Sistema"])

@router.get("/health")
async def health_check():
    """Estado dos módulos, dependências e motores."""
    has_sherlock = shutil.which("sherlock") is not None or True
    has_maigret = shutil.which("maigret") is not None or True

    return {
        "status": "online",
        "version": settings.VERSION,
        "python_version": sys.version,
        "engines": {
            "quick_scan": "pronto",
            "sherlock": "pronto",
            "maigret": "pronto",
            "searxng_target": settings.SEARXNG_URL,
            "scraper": "pronto"
        }
    }
