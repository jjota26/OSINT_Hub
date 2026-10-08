import time
import json
import logging
from typing import Any, Optional
from app.core.config import settings

logger = logging.getLogger("osint.cache")

class MemoryCache:
    """Cache em memória rápido e fiável com expiração TTL por chave,
    não necessitando de Redis externo obrigatoriamente."""
    def __init__(self):
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        if key in self._store:
            expires_at, value = self._store[key]
            if time.time() < expires_at:
                return value
            else:
                del self._store[key]
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        ttl = ttl or settings.CACHE_TTL_SECONDS
        self._store[key] = (time.time() + ttl, value)

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()

cache = MemoryCache()
