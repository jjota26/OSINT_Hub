from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import os
from pathlib import Path

from app.core.ssl_patch import apply_ssl_fix
from app.core.config import settings
from app.core.limiter import limiter
from app.routers import username, web_search, scraper, system

# Corrige certificados SSL antes de qualquer requisição de rede
apply_ssl_fix()

@asynccontextmanager
async def lifespan(app: FastAPI):
    apply_ssl_fix()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Plataforma Integrada de OSINT (Pesquisa de Perfis, SearXNG e Web Scraping)",
    lifespan=lifespan
)

# Rate Limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers da API
app.include_router(username.router)
app.include_router(web_search.router)
app.include_router(scraper.router)
app.include_router(system.router)

# Frontend Estático
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_index():
        return FileResponse(FRONTEND_DIR / "index.html")
