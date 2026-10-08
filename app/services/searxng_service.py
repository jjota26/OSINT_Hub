import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from app.core.config import settings
from app.core.cache import cache

PUBLIC_SEARXNG_INSTANCES = [
    "https://searx.be",
    "https://search.ononoki.org",
    "https://searx.tiekoetter.com",
    "https://search.sapti.me"
]

async def search_local_searxng(query: str, categories: str = "general") -> List[Dict[str, Any]]:
    """Tenta consultar a instância local do SearXNG configurada."""
    url = f"{settings.SEARXNG_URL.rstrip('/')}/search"
    params = {
        "q": query,
        "format": "json",
        "categories": categories,
        "language": "pt"
    }
    async with httpx.AsyncClient(timeout=8.0) as client:
        res = await client.get(url, params=params)
        if res.status_code == 200:
            data = res.json()
            results = []
            for item in data.get("results", []):
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "content": item.get("content", ""),
                    "engine": item.get("engine", "searxng"),
                    "source": "local_searxng"
                })
            return results
    return []

async def search_public_searxng(query: str) -> List[Dict[str, Any]]:
    """Consulta instâncias públicas do SearXNG como fallback quando o local não está ativo."""
    params = {"q": query, "format": "json", "language": "pt"}
    headers = {"User-Agent": settings.USER_AGENT}

    for base_url in PUBLIC_SEARXNG_INSTANCES:
        try:
            url = f"{base_url}/search"
            async with httpx.AsyncClient(timeout=6.0, headers=headers) as client:
                res = await client.get(url, params=params)
                if res.status_code == 200:
                    data = res.json()
                    results = []
                    for item in data.get("results", [])[:20]:
                        results.append({
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "content": item.get("content", ""),
                            "engine": item.get("engine", "searxng"),
                            "source": f"public_searxng ({base_url})"
                        })
                    if results:
                        return results
        except Exception:
            continue
    return []

async def search_duckduckgo_fallback(query: str) -> List[Dict[str, Any]]:
    """Fallback direto via DuckDuckGo HTML se nenhuma instância SearXNG estiver acessível."""
    url = "https://html.duckduckgo.com/html/"
    data = {"q": query}
    headers = {
        "User-Agent": settings.USER_AGENT,
        "Referer": "https://html.duckduckgo.com/"
    }
    async with httpx.AsyncClient(timeout=8.0, headers=headers) as client:
        res = await client.post(url, data=data)
        if res.status_code != 200:
            return []
        
        soup = BeautifulSoup(res.text, "html.parser")
        results = []
        for result in soup.select(".result"):
            title_elem = result.select_one(".result__title .result__a")
            snippet_elem = result.select_one(".result__snippet")
            if title_elem and title_elem.get("href"):
                link = title_elem["href"]
                # Desembrulha URLs do DuckDuckGo
                if "uddg=" in link:
                    import urllib.parse
                    parsed = urllib.parse.parse_qs(urllib.parse.urlparse(link).query)
                    link = parsed.get("uddg", [link])[0]
                results.append({
                    "title": title_elem.get_text(strip=True),
                    "url": link,
                    "content": snippet_elem.get_text(strip=True) if snippet_elem else "",
                    "engine": "duckduckgo",
                    "source": "fallback_ddg"
                })
        return results[:15]

async def execute_web_search(query: str, categories: str = "general") -> Dict[str, Any]:
    """Motor de busca inteligente com cache e fallbacks sucessivos."""
    cache_key = f"web_search:{query}:{categories}"
    cached = cache.get(cache_key)
    if cached:
        return {"query": query, "cached": True, "results": cached, "total": len(cached)}

    results = []
    engine_used = "local_searxng"

    # 1. Tenta SearXNG local
    try:
        results = await search_local_searxng(query, categories)
    except Exception:
        results = []

    # 2. Se falhar, tenta instâncias públicas do SearXNG
    if not results:
        engine_used = "public_searxng"
        results = await search_public_searxng(query)

    # 3. Se ainda não houver resultados, tenta DuckDuckGo
    if not results:
        engine_used = "duckduckgo_fallback"
        try:
            results = await search_duckduckgo_fallback(query)
        except Exception:
            results = []

    if results:
        cache.set(cache_key, results, ttl=1800)

    return {
        "query": query,
        "cached": False,
        "engine_used": engine_used,
        "results": results,
        "total": len(results)
    }
