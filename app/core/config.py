import os
from pydantic import BaseModel

class Settings(BaseModel):
    PROJECT_NAME: str = "OSINT Hub API"
    VERSION: str = "1.0.0"
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # SearXNG
    SEARXNG_URL: str = os.getenv("SEARXNG_URL", "http://localhost:8080")
    SEARXNG_PUBLIC_FALLBACK: str = os.getenv("SEARXNG_PUBLIC_FALLBACK", "https://searx.be")
    
    # Cache & Rate Limit
    REDIS_URL: str = os.getenv("REDIS_URL", "")
    CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "3600"))
    RATE_LIMIT_DEFAULT: str = os.getenv("RATE_LIMIT_DEFAULT", "60/minute")
    RATE_LIMIT_OSINT: str = os.getenv("RATE_LIMIT_OSINT", "15/minute")
    
    # Engines
    DEFAULT_TIMEOUT: float = float(os.getenv("DEFAULT_TIMEOUT", "15.0"))
    USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

settings = Settings()
