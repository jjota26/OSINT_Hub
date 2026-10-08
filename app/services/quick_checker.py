import asyncio
import httpx
from typing import AsyncGenerator, Dict, Any, List
from app.core.config import settings

# Catálogo rápido com regras de verificação das principais plataformas
POPULAR_SITES = [
    {
        "name": "GitHub",
        "category": "Desenvolvimento",
        "url": "https://github.com/{}",
        "check_url": "https://api.github.com/users/{}",
        "type": "status_code",
        "found_code": 200,
        "not_found_code": 404
    },
    {
        "name": "GitLab",
        "category": "Desenvolvimento",
        "url": "https://gitlab.com/{}",
        "check_url": "https://gitlab.com/{}",
        "type": "status_code",
        "found_code": 200,
        "not_found_code": 404
    },
    {
        "name": "DockerHub",
        "category": "Desenvolvimento",
        "url": "https://hub.docker.com/u/{}",
        "check_url": "https://hub.docker.com/v2/users/{}/",
        "type": "status_code",
        "found_code": 200,
        "not_found_code": 404
    },
    {
        "name": "Reddit",
        "category": "Redes Sociais",
        "url": "https://www.reddit.com/user/{}",
        "check_url": "https://www.reddit.com/user/{}/about.json",
        "type": "status_code",
        "found_code": 200,
        "not_found_code": 404
    },
    {
        "name": "Telegram",
        "category": "Mensagens",
        "url": "https://t.me/{}",
        "check_url": "https://t.me/{}",
        "type": "body_text_absent",
        "absent_pattern": "tgme_page_action",
    },
    {
        "name": "Pinterest",
        "category": "Redes Sociais",
        "url": "https://www.pinterest.com/{}/",
        "check_url": "https://www.pinterest.com/{}/",
        "type": "status_code",
        "found_code": 200,
        "not_found_code": 404
    },
    {
        "name": "Medium",
        "category": "Blog & Artigos",
        "url": "https://medium.com/@{}",
        "check_url": "https://medium.com/@{}",
        "type": "status_code",
        "found_code": 200,
        "not_found_code": 404
    },
    {
        "name": "Twitch",
        "category": "Streaming & Gaming",
        "url": "https://www.twitch.tv/{}",
        "check_url": "https://www.twitch.tv/{}",
        "type": "status_code",
        "found_code": 200,
        "not_found_code": 404
    },
    {
        "name": "Steam",
        "category": "Gaming",
        "url": "https://steamcommunity.com/id/{}",
        "check_url": "https://steamcommunity.com/id/{}",
        "type": "body_text_absent",
        "absent_pattern": "The specified profile could not be found",
    },
    {
        "name": "SoundCloud",
        "category": "Música",
        "url": "https://soundcloud.com/{}",
        "check_url": "https://soundcloud.com/{}",
        "type": "status_code",
        "found_code": 200,
        "not_found_code": 404
    },
    {
        "name": "DeviantArt",
        "category": "Arte",
        "url": "https://www.deviantart.com/{}",
        "check_url": "https://www.deviantart.com/{}",
        "type": "status_code",
        "found_code": 200,
        "not_found_code": 404
    },
    {
        "name": "Vimeo",
        "category": "Vídeo",
        "url": "https://vimeo.com/{}",
        "check_url": "https://vimeo.com/{}",
        "type": "status_code",
        "found_code": 200,
        "not_found_code": 404
    },
    {
        "name": "HackerNews",
        "category": "Tech",
        "url": "https://news.ycombinator.com/user?id={}",
        "check_url": "https://news.ycombinator.com/user?id={}",
        "type": "body_text_absent",
        "absent_pattern": "No such user",
    },
    {
        "name": "Disqus",
        "category": "Comunidade",
        "url": "https://disqus.com/by/{}/",
        "check_url": "https://disqus.com/by/{}/",
        "type": "status_code",
        "found_code": 200,
        "not_found_code": 404
    },
    {
        "name": "Replit",
        "category": "Desenvolvimento",
        "url": "https://replit.com/@{}",
        "check_url": "https://replit.com/@{}",
        "type": "status_code",
        "found_code": 200,
        "not_found_code": 404
    },
    {
        "name": "Substack",
        "category": "Blog & Artigos",
        "url": "https://{}.substack.com",
        "check_url": "https://{}.substack.com",
        "type": "status_code",
        "found_code": 200,
        "not_found_code": 404
    },
    {
        "name": "Patreon",
        "category": "Comunidade",
        "url": "https://www.patreon.com/{}",
        "check_url": "https://www.patreon.com/{}",
        "type": "status_code",
        "found_code": 200,
        "not_found_code": 404
    },
    {
        "name": "Mastodon (Social)",
        "category": "Redes Sociais",
        "url": "https://mastodon.social/@{}",
        "check_url": "https://mastodon.social/@{}",
        "type": "status_code",
        "found_code": 200,
        "not_found_code": 404
    },
    {
        "name": "Kaggle",
        "category": "Data Science",
        "url": "https://www.kaggle.com/{}",
        "check_url": "https://www.kaggle.com/{}",
        "type": "status_code",
        "found_code": 200,
        "not_found_code": 404
    },
    {
        "name": "LeetCode",
        "category": "Desenvolvimento",
        "url": "https://leetcode.com/{}",
        "check_url": "https://leetcode.com/{}",
        "type": "status_code",
        "found_code": 200,
        "not_found_code": 404
    }
]

async def check_single_site(client: httpx.AsyncClient, site: dict, username: str) -> Dict[str, Any]:
    url = site["url"].format(username)
    check_url = site["check_url"].format(username)
    name = site["name"]
    category = site.get("category", "Geral")
    
    try:
        res = await client.get(check_url, timeout=7.0, follow_redirects=True)
        is_found = False

        if site["type"] == "status_code":
            if res.status_code == site.get("found_code", 200):
                is_found = True
        elif site["type"] == "body_text_absent":
            pattern = site.get("absent_pattern", "")
            if res.status_code == 200 and (pattern not in res.text):
                is_found = True

        return {
            "site": name,
            "category": category,
            "url": url,
            "found": is_found,
            "status_code": res.status_code
        }
    except Exception as e:
        return {
            "site": name,
            "category": category,
            "url": url,
            "found": False,
            "error": str(e)
        }

async def stream_quick_check(username: str) -> AsyncGenerator[Dict[str, Any], None]:
    """Verifica concorrentemente as plataformas mais populares e faz stream em tempo real."""
    headers = {"User-Agent": settings.USER_AGENT}
    async with httpx.AsyncClient(headers=headers, verify=False) as client:
        tasks = [check_single_site(client, site, username) for site in POPULAR_SITES]
        for completed_task in asyncio.as_completed(tasks):
            result = await completed_task
            yield result
