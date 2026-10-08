import re
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from typing import Dict, Any, Set
from app.core.config import settings

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_REGEX = re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}")

SOCIAL_DOMAINS = {
    "github.com": "GitHub",
    "gitlab.com": "GitLab",
    "twitter.com": "Twitter / X",
    "x.com": "Twitter / X",
    "linkedin.com": "LinkedIn",
    "instagram.com": "Instagram",
    "facebook.com": "Facebook",
    "youtube.com": "YouTube",
    "tiktok.com": "TikTok",
    "t.me": "Telegram",
    "wa.me": "WhatsApp",
    "reddit.com": "Reddit",
    "pinterest.com": "Pinterest",
    "medium.com": "Medium"
}

IGNORABLE_EMAIL_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".css", ".js"}

def is_valid_email(email: str) -> bool:
    email_lower = email.lower()
    for ext in IGNORABLE_EMAIL_EXTS:
        if email_lower.endswith(ext):
            return False
    if "example.com" in email_lower or "yourdomain.com" in email_lower:
        return False
    return len(email) < 80

async def scrape_target_url(target_url: str) -> Dict[str, Any]:
    """Extrai contactos, redes sociais e metadados de uma página web alvo."""
    if not target_url.startswith(("http://", "https://")):
        target_url = "https://" + target_url

    headers = {
        "User-Agent": settings.USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }

    async with httpx.AsyncClient(timeout=12.0, headers=headers, follow_redirects=True, verify=False) as client:
        res = await client.get(target_url)
        res.raise_for_status()

    soup = BeautifulSoup(res.text, "html.parser")

    # Título e Descrição
    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    meta_desc = ""
    desc_tag = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
    if desc_tag and desc_tag.get("content"):
        meta_desc = desc_tag["content"].strip()

    # Extração de Emails
    raw_emails: Set[str] = set()
    # 1. Links mailto:
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("mailto:"):
            clean_mail = href.replace("mailto:", "").split("?")[0].strip()
            if clean_mail:
                raw_emails.add(clean_mail)

    # 2. Texto na página
    page_text = soup.get_text()
    for match in EMAIL_REGEX.findall(page_text):
        raw_emails.add(match.strip())

    emails = [e for e in raw_emails if is_valid_email(e)]

    # Extração de Telefones
    raw_phones: Set[str] = set()
    # 1. Links tel:
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("tel:"):
            clean_phone = href.replace("tel:", "").split("?")[0].strip()
            if clean_phone:
                raw_phones.add(clean_phone)

    # 2. Regex no texto
    for match in PHONE_REGEX.findall(page_text):
        cleaned = match.strip()
        # Filtra números demasiado pequenos ou puramente anos/datas
        digits = re.sub(r"\D", "", cleaned)
        if 8 <= len(digits) <= 15:
            raw_phones.add(cleaned)

    # Redes Sociais detetadas
    social_profiles: list[dict[str, str]] = []
    seen_social_urls = set()

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        full_url = urljoin(target_url, href)
        parsed = urlparse(full_url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]

        for soc_domain, soc_name in SOCIAL_DOMAINS.items():
            if soc_domain in domain and full_url not in seen_social_urls:
                # Evita links de partilha genéricos
                if "share" not in full_url.lower() and "intent/tweet" not in full_url.lower():
                    seen_social_urls.add(full_url)
                    social_profiles.append({
                        "platform": soc_name,
                        "url": full_url
                    })

    return {
        "target_url": target_url,
        "title": title,
        "description": meta_desc,
        "emails": sorted(list(emails)),
        "phones": sorted(list(raw_phones))[:10],
        "social_profiles": social_profiles,
        "status_code": res.status_code
    }
