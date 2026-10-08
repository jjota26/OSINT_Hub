import urllib.parse
import base64
import re
import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from app.core.config import settings
from app.core.cache import cache

try:
    from curl_cffi import requests as cffi_requests
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False

PUBLIC_SEARXNG_INSTANCES = [
    "https://searx.be",
    "https://search.ononoki.org",
    "https://searx.tiekoetter.com",
    "https://search.sapti.me"
]

def decode_bing_url(href: str) -> str:
    """Descodifica o URL real embutido em redirecionamentos do Bing."""
    if not href:
        return ""
    if "bing.com/ck/a" in href and "u=a1" in href:
        try:
            u_part = href.split("u=a1")[1].split("&")[0]
            rem = len(u_part) % 4
            if rem > 0:
                u_part += "=" * (4 - rem)
            return base64.urlsafe_b64decode(u_part).decode("utf-8", errors="ignore")
        except Exception:
            return href
    return href

async def search_brave_cffi(query: str) -> List[Dict[str, Any]]:
    """Consulta o Brave Search com personificação TLS Chrome para evasão de bloqueios."""
    if not HAS_CURL_CFFI:
        return []
    url = f"https://search.brave.com/search?q={urllib.parse.quote(query)}"
    results = []
    try:
        res = cffi_requests.get(url, impersonate="chrome120", verify=False, timeout=6.5)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            for sn in soup.select("div.snippet"):
                a = sn.select_one("a[href^='http']")
                title = sn.select_one(".title")
                all_p = [p.get_text(strip=True) for p in sn.find_all(["p", "div", "span"]) if p.get_text(strip=True) and (not title or p.get_text(strip=True) != title.get_text(strip=True))]
                desc = " ".join(all_p[:2])
                if a and title:
                    results.append({
                        "title": title.get_text(strip=True),
                        "url": a["href"],
                        "content": desc,
                        "engine": "brave",
                        "source": "brave_cffi"
                    })
    except Exception:
        pass
    return results[:20]

async def search_yahoo_cffi(query: str) -> List[Dict[str, Any]]:
    """Consulta o Yahoo Search com personificação TLS Chrome e descodificação de URLs /RU=."""
    if not HAS_CURL_CFFI:
        return []
    url = f"https://search.yahoo.com/search?p={urllib.parse.quote(query)}"
    results = []
    try:
        res = cffi_requests.get(url, impersonate="chrome120", verify=False, timeout=6.5)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            for li in soup.find_all(["li", "div"], class_=re.compile(r"\balgo\b")):
                a = li.find("a", href=re.compile(r"/RU="))
                if a:
                    m = re.search(r"/RU=(.*?)/RK=", a["href"])
                    clean_url = urllib.parse.unquote(m.group(1)) if m else a["href"]
                    title = a.get_text(strip=True)
                    # Limpa prefixos do Yahoo tipo "LinkedInhttps://..."
                    if "http" in title:
                        title_clean = title.split("http")[0].strip() or title
                    else:
                        title_clean = title
                    sn_elem = li.find(["p", "div"], class_=re.compile(r"compText|lh-16|abstract"))
                    content = sn_elem.get_text(strip=True) if sn_elem else ""
                    results.append({
                        "title": title_clean,
                        "url": clean_url,
                        "content": content,
                        "engine": "yahoo",
                        "source": "yahoo_cffi"
                    })
    except Exception:
        pass
    return results[:20]

async def search_duckduckgo_cffi(query: str) -> List[Dict[str, Any]]:
    """Consulta o DuckDuckGo HTML com personificação TLS Chrome e sessão persistente."""
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
    results = []

    if HAS_CURL_CFFI:
        try:
            s = cffi_requests.Session()
            s.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Referer": "https://duckduckgo.com/"
            })
            res = s.get(url, impersonate="chrome120", verify=False, timeout=6.5)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                for r in soup.select(".result"):
                    title_elem = r.select_one(".result__title .result__a")
                    snippet_elem = r.select_one(".result__snippet")
                    if title_elem and title_elem.get("href"):
                        link = title_elem["href"]
                        if "uddg=" in link:
                            parsed = urllib.parse.parse_qs(urllib.parse.urlparse(link).query)
                            link = parsed.get("uddg", [link])[0]
                        results.append({
                            "title": title_elem.get_text(strip=True),
                            "url": link,
                            "content": snippet_elem.get_text(strip=True) if snippet_elem else "",
                            "engine": "duckduckgo",
                            "source": "cffi_ddg"
                        })
                if results:
                    return results[:20]
        except Exception:
            pass

    # Fallback normal via httpx
    try:
        headers = {
            "User-Agent": settings.USER_AGENT,
            "Referer": "https://html.duckduckgo.com/"
        }
        async with httpx.AsyncClient(timeout=6.0, headers=headers, verify=False) as client:
            res = await client.post("https://html.duckduckgo.com/html/", data={"q": query})
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                for r in soup.select(".result"):
                    title_elem = r.select_one(".result__title .result__a")
                    snippet_elem = r.select_one(".result__snippet")
                    if title_elem and title_elem.get("href"):
                        link = title_elem["href"]
                        if "uddg=" in link:
                            parsed = urllib.parse.parse_qs(urllib.parse.urlparse(link).query)
                            link = parsed.get("uddg", [link])[0]
                        results.append({
                            "title": title_elem.get_text(strip=True),
                            "url": link,
                            "content": snippet_elem.get_text(strip=True) if snippet_elem else "",
                            "engine": "duckduckgo",
                            "source": "httpx_ddg"
                        })
    except Exception:
        pass

    return results[:20]

async def search_bing_fallback(query: str) -> List[Dict[str, Any]]:
    """Consulta Bing com extração limpa e descodificação de URLs."""
    results = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "es-ES,es;q=0.9,pt-PT;q=0.8,pt;q=0.7,en;q=0.6"
    }
    try:
        async with httpx.AsyncClient(timeout=6.0, headers=headers, verify=False) as client:
            res = await client.get("https://www.bing.com/search", params={"q": query})
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                for item in soup.select("li.b_algo"):
                    h2 = item.select_one("h2 a")
                    snippet = item.select_one(".b_caption p, .b_lineclamp, p")
                    if h2 and h2.get("href"):
                        raw_url = h2["href"]
                        clean_url = decode_bing_url(raw_url)
                        results.append({
                            "title": h2.get_text(strip=True),
                            "url": clean_url,
                            "content": snippet.get_text(strip=True) if snippet else "",
                            "engine": "bing",
                            "source": "bing_fallback"
                        })
    except Exception:
        pass
    return results[:15]

async def search_local_searxng(query: str, categories: str = "general") -> List[Dict[str, Any]]:
    """Tenta consultar a instância local do SearXNG configurada."""
    url = f"{settings.SEARXNG_URL.rstrip('/')}/search"
    params = {
        "q": query,
        "format": "json",
        "categories": categories,
        "language": "pt"
    }
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
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
    except Exception:
        pass
    return []

async def execute_web_search(query: str, categories: str = "general") -> Dict[str, Any]:
    """Motor de busca inteligente com multi-motor anti-bloqueio, cache e agregação de fontes."""
    cache_key = f"web_search:{query}:{categories}"
    cached = cache.get(cache_key)
    if cached:
        return {"query": query, "cached": True, "results": cached, "total": len(cached)}

    results = []
    seen_urls = set()

    # 1. Tenta SearXNG local (se ativo)
    local_res = await search_local_searxng(query, categories)
    for r in local_res:
        if r["url"] not in seen_urls:
            seen_urls.add(r["url"])
            results.append(r)

    # 2. Brave Search (Alta precisão, anti-bot TLS Chrome)
    brave_res = await search_brave_cffi(query)
    for r in brave_res:
        if r["url"] not in seen_urls:
            seen_urls.add(r["url"])
            results.append(r)

    # 3. Yahoo Search (Excelente para LinkedIn, diretórios e perfis)
    yahoo_res = await search_yahoo_cffi(query)
    for r in yahoo_res:
        if r["url"] not in seen_urls:
            seen_urls.add(r["url"])
            results.append(r)

    # 4. DuckDuckGo (snippets e diretórios ricos)
    ddg_res = await search_duckduckgo_cffi(query)
    for r in ddg_res:
        if r["url"] not in seen_urls:
            seen_urls.add(r["url"])
            results.append(r)

    # 5. Se ainda houver poucos resultados (< 4), complementa com Bing
    if len(results) < 4:
        bing_res = await search_bing_fallback(query)
        for r in bing_res:
            if r["url"] not in seen_urls:
                seen_urls.add(r["url"])
                results.append(r)

    if results:
        cache.set(cache_key, results, ttl=1800)

    return {
        "query": query,
        "cached": False,
        "engine_used": "multi_engine_cffi",
        "results": results,
        "total": len(results)
    }
