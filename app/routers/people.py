from fastapi import APIRouter, Query, Request, HTTPException
from typing import Optional
from app.services.people_service import search_intelligence
from app.core.limiter import limiter
from app.core.config import settings

router = APIRouter(prefix="/api/person", tags=["Pesquisa de Pessoas e Empresas"])

@router.get("/search")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def search_person(
    request: Request,
    name: Optional[str] = Query(None, description="Nome da pessoa a investigar"),
    company: Optional[str] = Query(None, description="Empresa ou organização onde trabalha"),
    role: Optional[str] = Query(None, description="Cargo ou função profissional"),
    country: Optional[str] = Query(None, description="País ou localização")
):
    """
    Pesquisa flexível e precisa de inteligência corporativa.
    Permite busca por qualquer campo de forma individual (Nome, Empresa, Cargo ou País).
    Identifica com exatidão o domínio corporativo oficial, servidores MX e contactos reais em uso.
    """
    if not any([name and name.strip(), company and company.strip(), role and role.strip(), country and country.strip()]):
        raise HTTPException(
            status_code=400,
            detail="Por favor, preencha pelo menos um campo para pesquisar (Nome, Empresa, Cargo ou País)."
        )

    return await search_intelligence(
        name=name,
        company=company,
        role=role,
        country=country
    )
