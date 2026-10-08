import re
import unicodedata
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
from app.services.searxng_service import execute_web_search

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_REGEX = re.compile(r"(?:\+?\d{1,3}[\s.-]?)?\(?\d{2,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,4}")

def normalize_text(text: str) -> str:
    """Remove acentos e converte para minúsculas."""
    if not text:
        return ""
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    ).lower().strip()

def generate_username_variants(name: str) -> List[str]:
    """Gera variações comuns de username a partir de um nome próprio."""
    clean = normalize_text(name)
    parts = re.split(r"[\s._-]+", clean)
    parts = [p for p in parts if p]
    if not parts:
        return []
    if len(parts) == 1:
        return [parts[0]]

    first = parts[0]
    last = parts[-1]
    variants = [
        f"{first}{last}",
        f"{first}.{last}",
        f"{first}_{last}",
        f"{first[0]}{last}",
        f"{first}{last[0]}",
        f"{first}-{last}"
    ]
    if len(parts) > 2:
        middle = parts[1]
        variants.append(f"{first}.{middle}.{last}")
        variants.append(f"{first[0]}{middle[0]}{last}")
    return list(dict.fromkeys(variants))

def guess_company_domain(company: str) -> Optional[str]:
    """Infere o provável domínio corporativo da empresa."""
    clean = normalize_text(company)
    clean = re.sub(r"\b(sa|lda|unipessoal|inc|ltd|gmbh|corp|group|grupo|llc)\b", "", clean).strip()
    clean = re.sub(r"[^\w]", "", clean)
    if not clean:
        return None
    return f"{clean}.com"

def generate_email_predictions(name: str, domain: str) -> List[Dict[str, str]]:
    """Gera combinações comuns de email corporativo."""
    clean_domain = domain.lower().replace("https://", "").replace("http://", "").split("/")[0].strip()
    if not clean_domain or "." not in clean_domain:
        return []
    variants = generate_username_variants(name)
    predictions = []
    for v in variants:
        predictions.append({
            "email": f"{v}@{clean_domain}",
            "pattern": v
        })
    return predictions

async def search_person_osint(
    name: str,
    company: Optional[str] = None,
    role: Optional[str] = None,
    country: Optional[str] = None
) -> Dict[str, Any]:
    """
    Motor especializado em investigação de pessoas e empresas.
    Combina busca web, deteção de perfis LinkedIn, extração de menções e previsão de emails corporativos.
    """
    clean_name = name.strip()
    clean_company = company.strip() if company else ""
    clean_role = role.strip() if role else ""

    # 1. Construir termos de busca
    queries = []
    if clean_company:
        queries.append(f'"{clean_name}" "{clean_company}"')
        queries.append(f'"{clean_name}" "{clean_company}" site:linkedin.com/in')
    else:
        queries.append(f'"{clean_name}" site:linkedin.com/in')
        queries.append(f'"{clean_name}"')

    if clean_role:
        queries.append(f'"{clean_name}" "{clean_role}"')

    # 2. Executar buscas
    aggregated_results = []
    seen_urls = set()

    for q in queries:
        try:
            res = await execute_web_search(q)
            for item in res.get("results", []):
                u = item.get("url", "")
                if u and u not in seen_urls:
                    seen_urls.add(u)
                    aggregated_results.append(item)
        except Exception:
            continue

    # 3. Categorizar resultados
    linkedin_profiles = []
    social_profiles = []
    other_mentions = []
    found_emails = set()
    found_phones = set()
    detected_domains = set()

    for item in aggregated_results:
        url = item.get("url", "")
        title = item.get("title", "")
        content = item.get("content", "")
        text_block = f"{title} {content}"

        # Extrair emails do texto
        for email in EMAIL_REGEX.findall(text_block):
            if not email.endswith((".png", ".jpg", ".jpeg", ".webp")):
                found_emails.add(email)

        # Extrair domínio para inferência
        parsed = urlparse(url)
        if parsed.netloc and not any(ign in parsed.netloc for ign in ["linkedin", "google", "facebook", "twitter", "instagram", "youtube", "duckduckgo"]):
            detected_domains.add(parsed.netloc.replace("www.", ""))

        # Classificar por rede
        if "linkedin.com/in/" in url or "linkedin.com/pub/" in url:
            linkedin_profiles.append({
                "title": title,
                "url": url,
                "snippet": content
            })
        elif any(s in url for s in ["twitter.com", "x.com", "facebook.com", "instagram.com", "github.com"]):
            social_profiles.append({
                "title": title,
                "url": url,
                "snippet": content
            })
        else:
            other_mentions.append({
                "title": title,
                "url": url,
                "snippet": content
            })

    # 4. Inferir domínios corporativos e previsões de email
    predicted_emails = []
    target_domain = None

    if clean_company:
        target_domain = guess_company_domain(clean_company)
        if target_domain:
            predicted_emails.extend(generate_email_predictions(clean_name, target_domain))

    # Adicionar também domínios específicos detetados na web se houver
    for dom in list(detected_domains)[:2]:
        if dom != target_domain:
            predicted_emails.extend(generate_email_predictions(clean_name, dom))

    # Limitar previsões para as 8 mais comuns
    predicted_emails = predicted_emails[:8]

    # 5. Variações de username para testar nas redes
    username_variants = generate_username_variants(clean_name)

    return {
        "person_name": clean_name,
        "company": clean_company,
        "role": clean_role,
        "linkedin_profiles": linkedin_profiles,
        "social_profiles": social_profiles,
        "web_mentions": other_mentions[:12],
        "extracted_emails": list(found_emails),
        "predicted_emails": predicted_emails,
        "username_variants": username_variants,
        "total_mentions": len(aggregated_results)
    }
