import json
import asyncio
from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse
from app.services.quick_checker import stream_quick_check
from app.services.sherlock_service import stream_sherlock
from app.services.maigret_service import stream_maigret
from app.core.limiter import limiter
from app.core.config import settings

router = APIRouter(prefix="/api/username", tags=["Username OSINT"])

@router.get("/quick/{username}")
@limiter.limit(settings.RATE_LIMIT_OSINT)
async def check_quick(request: Request, username: str):
    """Verificação ultrarrápida (2-4s) nas principais redes sociais."""
    results = []
    async for item in stream_quick_check(username):
        if item.get("found"):
            results.append(item)
    return {
        "username": username,
        "engine": "QuickChecker",
        "total_found": len(results),
        "results": results
    }

@router.get("/stream/{username}")
@limiter.limit(settings.RATE_LIMIT_OSINT)
async def stream_search(
    request: Request,
    username: str,
    engine: str = Query("all", description="quick, sherlock, maigret, ou all")
):
    """Endpoint de Server-Sent Events (SSE) para enviar resultados em tempo real sem timeout."""
    async def event_generator():
        yield f"data: {json.dumps({'type': 'init', 'username': username, 'engine': engine})}\n\n"

        # 1. Se engine for 'quick' ou 'all', executa primeiro a verificação rápida (instantânea)
        if engine in ("quick", "all"):
            yield f"data: {json.dumps({'type': 'stage', 'message': 'A verificar redes prioritárias...'})}\n\n"
            async for item in stream_quick_check(username):
                if item.get("found"):
                    yield f"data: {json.dumps({'type': 'found', 'site': item['site'], 'category': item['category'], 'url': item['url'], 'engine': 'QuickScan'})}\n\n"

        # 2. Se for 'sherlock' ou 'all'
        if engine in ("sherlock", "all"):
            yield f"data: {json.dumps({'type': 'stage', 'message': 'A iniciar varredura profunda Sherlock (400+ plataformas)...'})}\n\n"
            async for item in stream_sherlock(username):
                yield f"data: {json.dumps(item)}\n\n"

        # 3. Se for 'maigret'
        elif engine == "maigret":
            yield f"data: {json.dumps({'type': 'stage', 'message': 'A iniciar varredura Maigret...'})}\n\n"
            async for item in stream_maigret(username):
                yield f"data: {json.dumps(item)}\n\n"

        yield f"data: {json.dumps({'type': 'completed', 'username': username})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
