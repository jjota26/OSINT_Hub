from fastapi import APIRouter, Query, Request
from typing import Optional
from app.services.people_service import search_person_osint
from app.core.limiter import limiter
from app.core.config import settings

router = APIRouter(prefix="/api/person", tags=["Pesquisa de Pessoas e Empresas"])

@router.get("/search")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def search_person(
    request: Request,
    name: str = Query(..., description="Nome da pessoa a investigar"),
    company: Optional[str] = Query(None, description="Empresa ou organização onde trabalha"),
    role: Optional[str] = Query(None, description="Cargo ou função profissional"),
    country: Optional[str] = Query(None, description="País ou localização")
):
    """
    Pesquisa aprofundada de uma pessoa e empresa.
    Descobre perfis de LinkedIn, redes sociais, notícias/menções,
    extrai emails reais e gera previsões de emails corporativos.
    """
    return await search_person_osint(
        name=name,
        company=company,
        role=role,
        country=country
    )
