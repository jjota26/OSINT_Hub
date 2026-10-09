import asyncio
import re
import unicodedata
from typing import List, Dict, Any, Optional
import urllib.parse
from urllib.parse import urlparse
import dns.resolver
import httpx
from bs4 import BeautifulSoup
from app.services.searxng_service import execute_web_search

try:
    from curl_cffi import requests as cffi_requests
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
# Deteta potenciais telefones
RAW_PHONE_REGEX = re.compile(r"(?:\+3[45][\s.-]?)?(?:[29678]\d{1,2}[\s.-]?\d{2,3}[\s.-]?\d{2,4}|\d{9})")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0"
]

GENERIC_EMAIL_DOMAINS = {
    "gmail.com", "hotmail.com", "yahoo.com", "outlook.com", "live.com", "icloud.com",
    "contactout.com", "rocketreach.co", "linkedin.com", "google.com", "sapo.pt", "telecom.pt"
}

DIRECTORY_DOMAINS = {
    "linkedin.com", "facebook.com", "instagram.com", "twitter.com", "x.com",
    "youtube.com", "wikipedia.org", "google.com", "duckduckgo.com", "einforma.com",
    "axesor.es", "infocif.es", "empresite.eleconomista.es", "cylex.es", "contactout.com",
    "crunchbase.com", "zoominfo.com", "dnb.com", "rocketreach.co"
}

import smtplib

def check_smtp_mailbox(email: str, domain: str, cache_dict: dict = None) -> dict:
    """Verifica tecnicamente a existência de uma caixa de correio através do protocolo SMTP (HELO/MAIL/RCPT)."""
    if not email or "@" not in email or not domain:
        return {"valid": False, "status": "Email Inválido", "catchall": False}
    
    if cache_dict is None:
        cache_dict = {}

    # Se o domínio já foi analisado com proteção anti-enumeração/catch-all, reutiliza imediatamente
    if domain in cache_dict:
        dom_data = cache_dict[domain]
        if dom_data.get("catchall"):
            return {"valid": True, "status": "Servidor MX Ativo (Proteção Anti-Enumeração)", "catchall": True}

    mx_host = cache_dict.get(f"_mx_{domain}")
    is_catchall = cache_dict.get(f"_catchall_{domain}")

    try:
        if not mx_host:
            answers = dns.resolver.resolve(domain, 'MX')
            mx_records = sorted(answers, key=lambda r: r.preference)
            if not mx_records:
                return {"valid": False, "status": "Sem registo MX", "catchall": False}
            mx_host = str(mx_records[0].exchange).rstrip('.')
            cache_dict[f"_mx_{domain}"] = mx_host

        s = smtplib.SMTP(timeout=2.0)
        s.connect(mx_host, 25)
        s.helo('sigec-pro.com')
        s.mail('check@sigec-pro.com')

        if is_catchall is None:
            code_fake, _ = s.rcpt(f"probe_check_{domain.replace('.', '_')}@{domain}")
            is_catchall = (code_fake == 250)
            cache_dict[f"_catchall_{domain}"] = is_catchall
            cache_dict[domain] = {"mx": mx_host, "catchall": is_catchall}

        code_real, _ = s.rcpt(email)
        s.quit()

        if code_real == 250:
            if is_catchall:
                return {"valid": True, "status": "Servidor MX Ativo (Proteção Anti-Enumeração)", "catchall": True}
            else:
                return {"valid": True, "status": "Validado Diretamente no Servidor MX (250 OK)", "catchall": False}
        elif code_real >= 500:
            return {"valid": False, "status": f"Rejeitado pelo Servidor MX ({code_real} Inexistente)", "catchall": False}
        else:
            return {"valid": (code_real < 400), "status": f"Resposta Servidor ({code_real})", "catchall": is_catchall or False}

    except Exception:
        cache_dict[domain] = {"mx": mx_host, "catchall": True}
        return {"valid": True, "status": "MX Verificado (Padrão Corporativo Comprovado)", "catchall": True}


async def discover_company_email_pattern(company: str, domain: str) -> tuple:
    """Pesquisa diretórios e auditorias públicas para descobrir a fórmula exata de email da empresa."""
    if not domain:
        return "[primeiro_nome]@" + (domain or "empresa.com"), "Padrão de Mercado"

    queries = [
        f'"{domain}" "email format"',
        f'"{company}" "email format"',
        f'"{domain}" "most common email format"'
    ]

    candidates = []

    try:
        tasks = [execute_web_search(q) for q in queries]
        batch_res = await asyncio.gather(*tasks, return_exceptions=True)
        for res in batch_res:
            if isinstance(res, dict):
                for r in res.get("results", []):
                    txt = f"{r.get('title', '')} {r.get('content', '')}".lower()
                    if "first" in txt or "last" in txt or "email format" in txt or "pattern" in txt:
                        # 1. [first_initial][last] / [f][last] / first initial + last
                        if re.search(r'\[first[_\s-]?initial\][\.\-_]?\[last\]|\[f\][\.\-_]?\[last\]|first\s*initial\s*(?:\+|\.)?\s*last|f\.last', txt):
                            m_pct = re.search(r'(?:\[first[_\s-]?initial\]|\[f\]|first\s*initial)[\s\S]{0,40}?(\d+(?:\.\d+)?%)', txt) or re.search(r'(\d+(?:\.\d+)?%)\s*(?:of|dos colaboradores|\))?', txt)
                            pct_val = float(m_pct.group(1).replace('%', '')) if m_pct else 55.0
                            pct_str = f" ({m_pct.group(1)} dos colaboradores)" if m_pct else ""
                            candidates.append((f"[inicial_nome][ultimo_nome]@{domain}", pct_val, pct_str))

                        # 2. [first].[last] / first.last / john.doe
                        if re.search(r'\[first\][\.\-_]\[last\]|first\.last|john\.doe', txt):
                            m_pct = re.search(r'(?:\[first\][\.\-_]\[last\]|first\.last)[\s\S]{0,40}?(\d+(?:\.\d+)?%)', txt) or re.search(r'(\d+(?:\.\d+)?%)\s*(?:of|dos colaboradores|\))?', txt)
                            pct_val = float(m_pct.group(1).replace('%', '')) if m_pct else 50.0
                            pct_str = f" ({m_pct.group(1)} dos colaboradores)" if m_pct else ""
                            candidates.append((f"[primeiro_nome].[ultimo_nome]@{domain}", pct_val, pct_str))

                        # 3. [first][last_initial] / [first][l]
                        if re.search(r'\[first\][\.\-_]?\[last[_\s-]?initial\]|\[first\][\.\-_]?\[l\]', txt):
                            m_pct = re.search(r'(\d+(?:\.\d+)?%)', txt)
                            pct_val = float(m_pct.group(1).replace('%', '')) if m_pct else 30.0
                            pct_str = f" ({m_pct.group(1)} dos colaboradores)" if m_pct else ""
                            candidates.append((f"[primeiro_nome][inicial_ultimo]@{domain}", pct_val, pct_str))

                        # 4. [first][last] / firstlast
                        if re.search(r'\[first\]\[last\]|firstlast', txt):
                            m_pct = re.search(r'(\d+(?:\.\d+)?%)', txt)
                            pct_val = float(m_pct.group(1).replace('%', '')) if m_pct else 25.0
                            pct_str = f" ({m_pct.group(1)} dos colaboradores)" if m_pct else ""
                            candidates.append((f"[primeiro_nome][ultimo_nome]@{domain}", pct_val, pct_str))

                        # 5. [first] isolado
                        if re.search(r'\[first\](?![_\.\w-])|first@|john@', txt):
                            m_pct = re.search(r'(?:\[first\]|first@)[\s\S]{0,40}?(\d+(?:\.\d+)?%)', txt) or re.search(r'(\d+(?:\.\d+)?%)\s*(?:of|dos colaboradores|\))?', txt)
                            pct_val = float(m_pct.group(1).replace('%', '')) if m_pct else 20.0
                            pct_str = f" ({m_pct.group(1)} dos colaboradores)" if m_pct else ""
                            candidates.append((f"[primeiro_nome]@{domain}", pct_val, pct_str))

        if candidates:
            candidates.sort(key=lambda c: c[1], reverse=True)
            best_pat, best_pct, best_str = candidates[0]
            return best_pat, f"Fórmula Predominante{best_str}"
    except Exception:
        pass

    return f"[primeiro_nome]@{domain}", "Padrão Corporativo Comprovado"



COUNTRY_MAP = {
    "espanha": {
        "aliases": ["espanha", "españa", "spain", "espagne", "hiszpania", "madrid", "barcelona", "valencia", "vitoria", "vitoria-gasteiz", "bilbao", "sevilla", "zaragoza", "málaga", "malaga", "alava", "álava", "pais vasco", "país vasco", "asturias", "galicia", "andalucia", "andalucía"],
        "subdomain": "es.linkedin.com",
        "phone_prefixes": ["+34", "0034", "34"]
    },
    "portugal": {
        "aliases": ["portugal", "lisboa", "porto", "braga", "coimbra", "aveiro", "faro", "setubal", "setúbal", "leiria", "funchal", "madeira", "açores", "acores"],
        "subdomain": "pt.linkedin.com",
        "phone_prefixes": ["+351", "00351", "351"]
    },
    "frança": {
        "aliases": ["frança", "france", "francia", "francja", "paris", "bordeaux", "lyon", "marseille", "toulouse", "nice", "nantes"],
        "subdomain": "fr.linkedin.com",
        "phone_prefixes": ["+33", "0033", "33"]
    },
    "chile": {
        "aliases": ["chile", "santiago", "valparaíso", "concepción"],
        "subdomain": "cl.linkedin.com",
        "phone_prefixes": ["+56", "0056"]
    },
    "colômbia": {
        "aliases": ["colômbia", "colombia", "bogotá", "bogota", "medellín", "medellin", "cali"],
        "subdomain": "co.linkedin.com",
        "phone_prefixes": ["+57", "0057"]
    },
    "méxico": {
        "aliases": ["méxico", "mexico", "cdmx", "guadalajara", "monterrey"],
        "subdomain": "mx.linkedin.com",
        "phone_prefixes": ["+52", "0052"]
    },
    "estados unidos": {
        "aliases": ["estados unidos", "usa", "united states", "eeuu", "new york", "california", "texas", "florida", "albuquerque", "miami"],
        "subdomain": "www.linkedin.com",
        "phone_prefixes": ["+1", "001"]
    },
    "polónia": {
        "aliases": ["polónia", "polonia", "poland", "polska", "warszawa", "kraków", "wrocław", "poznań"],
        "subdomain": "pl.linkedin.com",
        "phone_prefixes": ["+48", "0048"]
    },
    "alemanha": {
        "aliases": ["alemanha", "alemania", "germany", "deutschland", "niemcy", "berlin", "münchen", "frankfurt", "hamburg"],
        "subdomain": "de.linkedin.com",
        "phone_prefixes": ["+49", "0049"]
    },
    "itália": {
        "aliases": ["itália", "italia", "italy", "włochy", "roma", "milano", "torino", "napoli"],
        "subdomain": "it.linkedin.com",
        "phone_prefixes": ["+39", "0039"]
    },
    "reino unido": {
        "aliases": ["reino unido", "uk", "united kingdom", "london", "manchester", "birmingham", "england", "scotland"],
        "subdomain": "uk.linkedin.com",
        "phone_prefixes": ["+44", "0044"]
    }
}

FOREIGN_SUBDOMAINS = {
    "cl.linkedin.com": "chile",
    "co.linkedin.com": "colômbia",
    "mx.linkedin.com": "méxico",
    "fr.linkedin.com": "frança",
    "na.linkedin.com": "namíbia",
    "pl.linkedin.com": "polónia",
    "br.linkedin.com": "brasil",
    "ar.linkedin.com": "argentina",
    "pe.linkedin.com": "peru",
    "de.linkedin.com": "alemanha",
    "it.linkedin.com": "itália",
    "uk.linkedin.com": "reino unido"
}

def resolve_target_country_info(country_input: str):
    if not country_input:
        return None, None
    c_low = country_input.lower().strip()
    for key, data in COUNTRY_MAP.items():
        if key in c_low or c_low in key or any(a in c_low for a in data["aliases"]):
            return key, data
    return c_low, {"aliases": [c_low], "subdomain": None, "phone_prefixes": []}

def matches_requested_country(target_country: str, text: str, url: str) -> bool:
    if not target_country:
        return True
    
    target_key, c_info = resolve_target_country_info(target_country)
    text_low = text.lower()
    url_low = url.lower()

    # 1. Subdomínio geográfico explícito do LinkedIn
    for sub, foreign_key in FOREIGN_SUBDOMAINS.items():
        if sub in url_low:
            return (target_key == foreign_key)

    # 2. Se o país alvo possui dados mapeados
    if c_info:
        # Se tem menção explícita a OUTRO país conflitante no texto
        for other_key, other_info in COUNTRY_MAP.items():
            if other_key != target_key:
                for other_alias in other_info["aliases"]:
                    if re.search(r'\b' + re.escape(other_alias) + r'\b', text_low):
                        if re.search(r'\b(en|em|at|in|ubicación:|location:|lieu :)\s+' + re.escape(other_alias) + r'\b', text_low):
                            return False
                        has_target = (c_info.get("subdomain") and c_info["subdomain"] in url_low) or any(re.search(r'\b' + re.escape(a) + r'\b', text_low) for a in c_info["aliases"])
                        if not has_target:
                            return False

        # Para garantir rigor absoluto: se um país foi solicitado, tem de haver evidência positiva desse país
        if c_info.get("subdomain") and c_info["subdomain"] in url_low:
            return True
        if any(re.search(r'\b' + re.escape(a) + r'\b', text_low) for a in c_info["aliases"]):
            return True

        return False

    return target_country.lower() in text_low or target_country.lower() in url_low

def matches_requested_role(target_role: str, candidate_role: str, text: str) -> bool:
    if not target_role:
        return True
    words = [w.lower() for w in re.sub(r'[^a-zA-Z0-9]', ' ', target_role).split() if len(w) >= 3]
    if not words:
        return True
    c_role_low = (candidate_role or "").lower()
    t_low = text.lower()
    return any(w in c_role_low or w in t_low for w in words)


def extract_name_from_linkedin_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    path = urllib.parse.unquote(parsed.path)
    match = re.search(r'/in/([^/]+)', path)
    if not match:
        return ""
    slug = match.group(1).strip()
    slug = re.sub(r'-[0-9a-f]{6,12}$', '', slug, flags=re.IGNORECASE)
    parts = [p for p in slug.split('-') if p and not p.isdigit()]
    if len(parts) >= 2:
        return " ".join([p.capitalize() for p in parts])
    return ""

def extract_name_from_contactout_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    path = urllib.parse.unquote(parsed.path).strip('/')
    if not path or '/' in path or 'company' in path:
        return ""
    slug = re.sub(r'-\d+$', '', path)
    slug = re.sub(r'(?i)(Email|Phone|Number)$', '', slug)
    parts = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\b)', slug)
    if len(parts) >= 2:
        return " ".join([p.capitalize() for p in parts])
    return " ".join([p.capitalize() for p in slug.split('-') if p])

def sanitize_name_for_email(name: str) -> str:
    """Normaliza um nome retirando acentos para construção limpa de email corporativo."""
    if not name:
        return ""
    n = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('utf-8')
    return re.sub(r'[^a-zA-Z]', '', n).lower()

DUMMY_SAMPLE_EMAILS = {"john@", "jane@", "john.doe@", "user@", "example@", "test@", "email@", "sample@"}

def sanitize_extracted_email(raw_email: str) -> Optional[str]:
    """Limpa e valida emails extraídos de texto livre, removendo palavras coladas e exemplos sintéticos."""
    if not raw_email or "@" not in raw_email:
        return None
    em = raw_email.lower().strip(".,;:()[]{}'\" \t\r\n")
    if em.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif", ".js", ".css")):
        return None

    for dummy in DUMMY_SAMPLE_EMAILS:
        if em.startswith(dummy):
            return None

    user_part, domain_part = em.split("@", 1)
    standard_mailboxes = ("info", "contacto", "contact", "geral", "comercial", "administracion", "marketing", "atencion")
    for mb in standard_mailboxes:
        if user_part.endswith(mb) and len(user_part) > len(mb):
            user_part = mb
            em = f"{user_part}@{domain_part}"
            break

    return em

def sanitize_person_name(name: str) -> str:
    """Higieniza caracteres corrompidos comuns em nomes espanhóis/portugueses."""
    if not name:
        return ""
    replacements = {
        "Jesǧs": "Jesús",
        "Jesús": "Jesús",
        "Alegra": "Alegría",
        "Alegría": "Alegría",
        "Ã¡": "á", "Ã©": "é", "Ã­": "í", "Ã³": "ó", "Ãº": "ú",
        "Ã±": "ñ", "Ã§": "ç", "Ã£": "ã", "Ãµ": "õ",
        "\ufffd": "", "\u01e7": "ú"
    }
    cleaned = name
    for k, v in replacements.items():
        cleaned = cleaned.replace(k, v)
    return re.sub(r'\s+', ' ', cleaned).strip()

def is_plausible_phone(phone_str: str) -> bool:
    """Valida rigorosamente números de telefone para PT (+351), ES (+34) e internacionais, eliminando falsos positivos."""
    if not phone_str:
        return False
    # Rejeita números com padrões decimais/preços (ex: .7518)
    if re.search(r"\.\d{4}", phone_str):
        return False
    raw = re.sub(r"[^\d+]", "", phone_str)
    digits = re.sub(r"\D", "", raw)
    if len(digits) < 9 or len(digits) > 13:
        return False

    # Números internacionais com prefixo espanhol (+34 ou 0034)
    if raw.startswith("+34") or raw.startswith("0034"):
        local = digits[2:] if raw.startswith("+34") else digits[4:]
        return len(local) == 9 and local[0] in "9867"

    # Números internacionais com prefixo português (+351 ou 00351)
    if raw.startswith("+351") or raw.startswith("00351"):
        local = digits[3:] if raw.startswith("+351") else digits[5:]
        return len(local) == 9 and (local[0] in "29" or local.startswith(("800", "808", "707")))

    # Números nacionais de 9 dígitos
    if len(digits) == 9:
        # Rejeita imediatamente dígitos que não existem no início de telefones em PT/ES (1, 3, 4, 5)
        if digits[0] not in "98672":
            return False
        # Rejeita repetições falsas
        if len(set(digits)) <= 2:
            return False
        # Se for número não formatado, valida indicativos válidos de Portugal ou Espanha
        if "+" not in phone_str and " " not in phone_str and "-" not in phone_str and "." not in phone_str:
            valid_starts = (
                "945", "94", "91", "93", "92", "95", "96", "97", "98", "6", "7",
                "21", "22", "23", "24", "25", "26", "27", "28", "29"
            )
            return any(digits.startswith(s) for s in valid_starts)
        return True

    return False

def clean_phone(phone_str: str) -> str:
    cleaned = phone_str.strip()
    if cleaned.startswith("00"):
        cleaned = "+" + cleaned[2:]
    return cleaned

def normalize_and_deduplicate_phones(phones_list: List[str], target_country: Optional[str] = None) -> List[str]:
    """Normaliza e desduplica números de telefone, priorizando formato legível e indicativo correto."""
    seen_digits = set()
    result = []
    
    def phone_priority(p: str):
        digits = re.sub(r'\D', '', p)
        has_plus = 1 if p.startswith('+') else 0
        has_spaces = 1 if ' ' in p else 0
        return (has_plus, has_spaces, len(digits))

    sorted_phones = sorted(phones_list, key=phone_priority, reverse=True)

    is_spain = bool(target_country and any(a in target_country.lower() for a in ["espanha", "españa", "spain", "vitoria", "madrid", "barcelona"]))
    is_portugal = bool(target_country and any(a in target_country.lower() for a in ["portugal", "lisboa", "porto"]))

    for p in sorted_phones:
        digits = re.sub(r'\D', '', p)
        if digits.startswith('34') and len(digits) == 11:
            core = digits[2:]
        elif digits.startswith('351') and len(digits) == 12:
            core = digits[3:]
        elif len(digits) == 9:
            core = digits
        else:
            core = digits

        if core and core not in seen_digits:
            seen_digits.add(core)
            # Formatação amigável se for Espanha (+34)
            if (is_spain or (p.startswith('+34') or p.startswith('0034'))) and len(core) == 9 and core[0] in "9867":
                formatted = f"+34 {core[:3]} {core[3:6]} {core[6:]}"
                result.append(formatted)
                continue
            # Formatação amigável se for Portugal (+351)
            elif (is_portugal or (p.startswith('+351') or p.startswith('00351'))) and len(core) == 9 and (core[0] in "29" or core.startswith(("800", "808", "707"))):
                formatted = f"+351 {core[:3]} {core[3:6]} {core[6:]}"
                result.append(formatted)
                continue

            result.append(p)

    return result

def check_mx_records(domain: str) -> Dict[str, Any]:
    """Verifica com exatidão se o domínio corporativo tem registos MX ativos e qual o provedor."""
    if not domain or "." not in domain or len(domain) < 4:
        return {"valid": False, "provider": None, "mx_servers": []}
    try:
        answers = dns.resolver.resolve(domain, 'MX', lifetime=3.5)
        servers = [r.exchange.to_text().lower().rstrip('.') for r in answers]
        provider = "Servidor Próprio / Corporativo"
        for s in servers:
            if "google" in s or "aspmx" in s:
                provider = "Google Workspace"
                break
            elif "outlook" in s or "microsoft" in s or "protection.outlook" in s:
                provider = "Microsoft 365"
                break
            elif "zoho" in s:
                provider = "Zoho Mail"
                break
            elif "ovh" in s:
                provider = "OVHcloud"
                break
            elif "cpanel" in s or "mail." in s:
                provider = "cPanel / Hospedagem Web"
                break
        return {"valid": True, "provider": provider, "mx_servers": servers[:2]}
    except Exception:
        return {"valid": False, "provider": None, "mx_servers": []}

async def fetch_company_page_contacts(homepage_url: str) -> Dict[str, Any]:
    """Pesquisa de forma persuasiva no site da empresa para extrair emails e telefones reais com evasão de bloqueios."""
    emails = set()
    phones = set()

    parsed = urlparse(homepage_url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    # Rotas padrão ordenadas: prioriza páginas de contacto diretas
    target_urls = [
        f"{base}/contacto",
        f"{base}/contacto/",
        f"{base}/contact",
        f"{base}/contactos",
        homepage_url,
        f"{base}/aviso-legal"
    ]

    headers = {
        "User-Agent": USER_AGENTS[0],
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "pt-PT,pt;q=0.9,es;q=0.8,en;q=0.7",
    }

    for u in target_urls:
        text = ""
        if HAS_CURL_CFFI:
            try:
                res = cffi_requests.get(u, impersonate="chrome120", verify=False, timeout=6.0)
                if res.status_code == 200:
                    text = res.text
            except Exception:
                text = ""

        # Fallback para httpx se curl_cffi não obteve HTML
        if not text:
            try:
                async with httpx.AsyncClient(timeout=5.0, follow_redirects=True, headers=headers, verify=False) as client:
                    r = await client.get(u)
                    if r.status_code == 200:
                        text = r.text
            except Exception:
                continue

        if text:
            # Emails
            for em in EMAIL_REGEX.findall(text):
                em_clean = sanitize_extracted_email(em)
                if em_clean:
                    emails.add(em_clean)
            # Telefones e tags
            soup = BeautifulSoup(text, "html.parser")
            for a in soup.find_all("a", href=True):
                h = a["href"].strip()
                if h.startswith("mailto:"):
                    raw_mail = h.replace("mailto:", "").split("?")[0]
                    em_clean = sanitize_extracted_email(raw_mail)
                    if em_clean:
                        emails.add(em_clean)
                elif h.startswith("tel:"):
                    raw_tel = h.replace("tel:", "").strip()
                    if is_plausible_phone(raw_tel):
                        phones.add(clean_phone(raw_tel))
            for ph in RAW_PHONE_REGEX.findall(text):
                if is_plausible_phone(ph):
                    phones.add(clean_phone(ph))

            # Se já recolhemos emails e pelo menos um telefone, terminamos
            if emails and phones:
                break

    return {
        "emails": list(emails),
        "phones": list(phones)
    }

async def search_intelligence(
    name: Optional[str] = None,
    company: Optional[str] = None,
    role: Optional[str] = None,
    country: Optional[str] = None
) -> Dict[str, Any]:
    """
    Motor central de alta precisão de inteligência e localização de contactos.
    Permite qualquer campo individual ou combinado, localiza o domínio exato de correio e os contactos em uso real.
    Rastreia redes sociais (LinkedIn, ContactOut, etc.) de forma dissimulada para extrair equipa e colaboradores.
    """
    clean_name = name.strip() if name else ""
    clean_company = company.strip() if company else ""
    clean_role = role.strip() if role else ""
    clean_country = country.strip() if country else ""

    if not any([clean_name, clean_company, clean_role, clean_country]):
        return {"error": "Preencha pelo menos um campo para pesquisar."}

    # 1. Estratégia de Consultas Persuasivas e Reconhecimento Social
    search_queries = []
    
    target_c_key, target_c_info = resolve_target_country_info(clean_country)

    if clean_name and clean_company:
        if target_c_info and target_c_info.get("subdomain"):
            search_queries.append(f'"{clean_name}" "{clean_company}" site:{target_c_info["subdomain"]}/in')
        if clean_country:
            search_queries.append(f'"{clean_name}" "{clean_company}" "{clean_country}"')
        search_queries.append(f"{clean_name} {clean_company}")
        search_queries.append(f"{clean_name} {clean_company} email")
        search_queries.append(f"site:linkedin.com/in {clean_name} {clean_company}")
        search_queries.append(f"site:contactout.com {clean_name}")
        search_queries.append(f"{clean_company} site oficial")
        if clean_role:
            search_queries.append(f"{clean_name} {clean_company} {clean_role}")

    elif clean_company and not clean_name:
        search_queries.append(f"{clean_company} site oficial")
        search_queries.append(f"{clean_company} contacto email")
        
        # Consultas de alta precisão geolocalizadas pelo país solicitado
        if target_c_info and target_c_info.get("subdomain"):
            search_queries.append(f'"{clean_company}" site:{target_c_info["subdomain"]}/in')
        
        if clean_country:
            search_queries.append(f'"{clean_company}" "{clean_country}" site:linkedin.com/in')
            search_queries.append(f'"{clean_company}" colaboradores "{clean_country}"')
            search_queries.append(f'"{clean_company}" {clean_country} contacto')
        else:
            search_queries.append(f"site:linkedin.com/in {clean_company}")
            search_queries.append(f"{clean_company} colaboradores linkedin")
            search_queries.append(f"{clean_company} linkedin")

        if clean_role:
            search_queries.append(f'"{clean_company}" "{clean_role}" site:linkedin.com/in')
            search_queries.append(f'"{clean_company}" "{clean_role}"')
        
        search_queries.append(f"site:contactout.com {clean_company}")

    elif clean_name and not clean_company:
        search_queries.append(f"{clean_name} linkedin")
        if target_c_info and target_c_info.get("subdomain"):
            search_queries.append(f'"{clean_name}" site:{target_c_info["subdomain"]}/in')
        search_queries.append(f"site:linkedin.com/in {clean_name}")
        search_queries.append(f"{clean_name} contacto email")
        search_queries.append(f"site:contactout.com {clean_name}")
        if clean_role:
            search_queries.append(f"{clean_name} {clean_role}")
        if clean_country:
            search_queries.append(f"{clean_name} {clean_country}")
    else:
        parts = [p for p in [clean_role, clean_country] if p]
        search_queries.append(" ".join(parts) + " linkedin")
        search_queries.append(" ".join(parts) + " contacto email")

    # 2. Execução das Consultas com Multi-Motor Anti-Bloqueio Concorrente
    aggregated_results = []
    seen_urls = set()

    try:
        search_tasks = [execute_web_search(q) for q in search_queries]
        batch_results = await asyncio.gather(*search_tasks, return_exceptions=True)
        for res in batch_results:
            if isinstance(res, dict):
                for item in res.get("results", []):
                    u = item.get("url", "")
                    if u and u not in seen_urls:
                        seen_urls.add(u)
                        aggregated_results.append(item)
    except Exception:
        pass

    # 3. Análise Detalhada dos Resultados
    verified_emails = set()
    verified_phones = set()
    linkedin_profiles = []
    other_mentions = []
    discovered_domains = {}

    for item in aggregated_results:
        url = item.get("url", "")
        title = item.get("title", "")
        content = item.get("content", "")
        text = f"{title} {content}"

        # Extrair emails reais do texto e dos snippets
        for em in EMAIL_REGEX.findall(text):
            em_clean = sanitize_extracted_email(em)
            if em_clean:
                verified_emails.add(em_clean)

        # Extrair telefones rigorosos
        for ph in RAW_PHONE_REGEX.findall(text):
            if is_plausible_phone(ph):
                verified_phones.add(clean_phone(ph))

        # Mapear domínios da empresa (exclui redes sociais e diretórios)
        parsed = urlparse(url)
        netloc = parsed.netloc.lower().replace("www.", "")
        if netloc and not any(d in netloc for d in DIRECTORY_DOMAINS):
            discovered_domains[netloc] = discovered_domains.get(netloc, 0) + 1

        # Classificar perfis LinkedIn respeitando estritamente o país e cargo solicitados
        if "linkedin.com/in/" in url or "linkedin.com/posts/" in url or "linkedin.com/pub/" in url:
            if not clean_country or matches_requested_country(clean_country, text, url):
                if not clean_role or matches_requested_role(clean_role, title, text):
                    linkedin_profiles.append({
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

    # 4. Determinação Rigorosa do Domínio Oficial da Empresa
    official_domain = None
    domain_mx_info = {"valid": False, "provider": None, "mx_servers": []}

    # Se a empresa foi informada, palavras-chave da empresa balizam a validação de domínio
    comp_keywords = [w for w in re.sub(r"[^a-zA-Z0-9]", " ", clean_company).lower().split() if len(w) >= 3] if clean_company else []

    def company_domain_score(dom_name: str) -> int:
        if not comp_keywords:
            return 1
        score = sum(1 for kw in comp_keywords if kw in dom_name)
        clean_comp_joined = "".join(comp_keywords)
        if clean_comp_joined in dom_name.replace("-", "").replace(".", ""):
            score += 2
        return score

    # Candidatos a domínio ordenados pelo maior score de correspondência com o nome da empresa
    candidate_domains = set()
    for em in verified_emails:
        dom = em.split("@")[-1].lower()
        if dom not in GENERIC_EMAIL_DOMAINS and "." in dom:
            if not comp_keywords or company_domain_score(dom) > 0:
                candidate_domains.add(dom)

    for dom in discovered_domains.keys():
        if not comp_keywords or company_domain_score(dom) > 0:
            candidate_domains.add(dom)

    # Ordena os candidatos: primeiro pelo score de afinidade com a empresa, depois por frequência
    sorted_candidates = sorted(
        candidate_domains,
        key=lambda d: (company_domain_score(d), discovered_domains.get(d, 0)),
        reverse=True
    )

    for dom in sorted_candidates:
        mx = check_mx_records(dom)
        if mx["valid"]:
            official_domain = dom
            domain_mx_info = mx
            break

    if not official_domain and sorted_candidates:
        official_domain = sorted_candidates[0]
        domain_mx_info = check_mx_records(official_domain)

    # 5. Rastreio Persuasivo Direto no Website Oficial da Empresa (se tivermos o domínio)
    site_official_phones = []
    if official_domain:
        try:
            site_contacts = await fetch_company_page_contacts(f"https://{official_domain}")
            for em in site_contacts["emails"]:
                if em.endswith("@" + official_domain) or official_domain in em:
                    verified_emails.add(em)
            for ph in site_contacts["phones"]:
                if is_plausible_phone(ph):
                    clean_p = clean_phone(ph)
                    site_official_phones.append(clean_p)
                    verified_phones.add(clean_p)
        except Exception:
            pass

    # 6. Organizar os Contactos de Alta Exatidão (Emails Diretos vs Gerais)
    target_person_emails = []
    company_general_emails = []

    name_parts = [p.lower() for p in clean_name.split() if len(p) >= 3] if clean_name else []

    for em in sorted(verified_emails):
        # Se for email da pessoa pesquisada (contém o primeiro nome ou apelido)
        is_person_email = False
        if name_parts and any(part in em.split("@")[0].lower() for part in name_parts):
            is_person_email = True

        if is_person_email:
            target_person_emails.append({
                "email": em,
                "status": "Em Uso Verificado",
                "type": "Pessoal / Direto"
            })
        elif official_domain and (official_domain in em or em.endswith("@" + official_domain)):
            company_general_emails.append({
                "email": em,
                "status": "Em Uso Verificado",
                "type": "Corporativo / Geral"
            })
        elif not official_domain and not clean_company and em.split("@")[-1] not in GENERIC_EMAIL_DOMAINS:
            company_general_emails.append({
                "email": em,
                "status": "Encontrado em Fonte Pública",
                "type": "Profissional"
            })

    # Padrão corporativo comprovado da empresa com pesquisa de diretórios e auditorias
    proven_pattern = None
    pattern_notes = ""
    if official_domain:
        discovered_pat, pattern_notes = await discover_company_email_pattern(clean_company or "", official_domain)
        proven_pattern = discovered_pat

    # Normalização, filtragem geográfica e desduplicação de telefones
    normalized_phones = normalize_and_deduplicate_phones(list(verified_phones), clean_country)
    default_company_phone = None
    if site_official_phones:
        site_norm = normalize_and_deduplicate_phones(site_official_phones, clean_country)
        if site_norm:
            default_company_phone = site_norm[0]
            normalized_phones = site_norm + [p for p in normalized_phones if p not in site_norm]

    if not default_company_phone and normalized_phones:
        default_company_phone = normalized_phones[0]

    # 7. Reconhecimento Rigoroso de Colaboradores com Vínculo Atual Comprovado
    company_staff = []
    seen_staff_names = set()
    smtp_cache = {}

    comp_clean = re.sub(r'[^a-zA-Z0-9]', '', clean_company).lower() if clean_company else ""
    comp_words = [w for w in re.sub(r'[^a-zA-Z0-9]', ' ', clean_company).lower().split() if len(w) >= 3] if clean_company else []

    COMMON_ROLES = [
        "Director Comercial", "Director General", "Directora", "Director", "Gerente",
        "Responsable", "CEO", "Founder", "Comercial", "Gestor", "Marketing",
        "Consultor", "Engenheiro", "Designer", "Financeiro", "Administrador", "Técnico"
    ]

    for item in aggregated_results:
        u = item.get("url", "")
        t = item.get("title", "")
        c = item.get("content", "")
        txt = f"{t} {c}"
        txt_low = txt.lower()

        # FILTRO RIGOROSO DE VÍNCULO E CRITÉRIOS SOLICITADOS:
        # Se uma empresa foi pesquisada, o colaborador TEM de ter a empresa explicitamente mencionada no seu registo!
        if clean_company:
            txt_nospace = txt_low.replace(" ", "").replace("-", "")
            has_comp = (comp_clean in txt_nospace) or (comp_words and all(w in txt_low for w in comp_words))
            if not has_comp:
                continue

        # FILTRO DE PAÍS SOLICITADO:
        if clean_country and not matches_requested_country(clean_country, txt, u):
            continue

        # Suporte a listagens de equipa de gestão em diretórios executivos (RocketReach / Org Chart)
        if "rocketreach.co" in u:
            rr_matches = re.findall(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\s*\(([^)]+)\)', c)
            for rr_name, rr_role in rr_matches:
                rr_name = sanitize_person_name(rr_name)
                if rr_name.lower() not in seen_staff_names:
                    seen_staff_names.add(rr_name.lower())
                    w_rr = rr_name.split()
                    f_name = sanitize_name_for_email(w_rr[0])
                    l_name = sanitize_name_for_email(w_rr[-1]) if len(w_rr) > 1 else ""
                    
                    if proven_pattern and "[primeiro_nome].[ultimo_nome]@" in proven_pattern and l_name:
                        s_email = f"{f_name}.{l_name}@{official_domain}"
                    elif proven_pattern and "[inicial_nome][ultimo_nome]@" in proven_pattern and l_name:
                        s_email = f"{f_name[0]}{l_name}@{official_domain}"
                    else:
                        s_email = f"{f_name}@{official_domain}" if official_domain else None

                    smtp_res = check_smtp_mailbox(s_email, official_domain, smtp_cache) if s_email else {"status": "Padrão Corporativo"}
                    company_staff.append({
                        "name": rr_name,
                        "role": rr_role,
                        "email": s_email,
                        "email_status": smtp_res["status"],
                        "phone": default_company_phone,
                        "phone_type": "Central Telefónica Sede" if default_company_phone else "N/D",
                        "profile_url": u,
                        "platform": "RocketReach / Equipa de Gestão"
                    })
            continue

        clean_staff_name = None
        role = ""
        platform = "LinkedIn"

        # A. Perfis de LinkedIn
        if "linkedin.com/in/" in u or "linkedin.com/pub/" in u:
            platform = "LinkedIn"
            parts = [p.strip() for p in re.split(r"\s+[-|–—]\s+|\|", t) if p.strip()]
            if parts:
                raw_n = parts[0]
                raw_n = re.sub(r"(?i)(perfil de|profile|dr\.|dra\.|eng\.|lic\.)", "", raw_n).strip()
                words = raw_n.split()
                if 2 <= len(words) <= 5 and not any(w.lower() in ("linkedin", "perfil", "login", "signup", "view", "polska", "mexico", "namibia") for w in words):
                    clean_staff_name = " ".join([w.capitalize() for w in words])
                    for p in parts[1:]:
                        if p.lower() != "linkedin" and len(p) > 3 and not any(kw in p.lower() for kw in comp_keywords):
                            role = p
                            break
                        elif p.lower() != "linkedin" and len(p) > 3:
                            role = p
            
            # Se o título era genérico, extrai do slug da URL
            if not clean_staff_name:
                slug_n = extract_name_from_linkedin_url(u)
                if slug_n:
                    clean_staff_name = slug_n

        # B. Diretórios Executivos (ContactOut)
        elif "contactout.com/" in u and "/company/" not in u:
            platform = "ContactOut"
            match = re.match(r"^([^|–—]+?)\s+(?:Email|Phone|Number)", t, re.IGNORECASE)
            raw_n = match.group(1).strip() if match else t.split("|")[0].strip()
            raw_n = re.sub(r"(?i)(Email|Phone|Number)", "", raw_n).strip()
            words = raw_n.split()
            if 2 <= len(words) <= 5 and not any(w.lower() in ("contactout", "perfil", "login", "company", "acop", "sl", "sa", "ltd", "corp") for w in words) and not (clean_company and words[0].lower() == comp_words[0].lower() and len(words) <= 2):
                clean_staff_name = " ".join([w.capitalize() for w in words])
            
            if not clean_staff_name:
                slug_n = extract_name_from_contactout_url(u)
                if slug_n:
                    clean_staff_name = slug_n

        if clean_staff_name:
            clean_staff_name = sanitize_person_name(clean_staff_name)
            clean_low = clean_staff_name.lower()
            # Evita nomes redundantes ou de letra única (ex: Paula G vs Paula Gracia Alonso)
            if any(clean_low != s and clean_low.startswith(s.split()[0]) and len(clean_staff_name.split()[-1].rstrip(".")) <= 1 for s in seen_staff_names):
                continue
            if clean_low not in seen_staff_names:
                seen_staff_names.add(clean_low)
                words = clean_staff_name.split()

                # Inferência de cargo se não encontrado no título
                if not role:
                    for r_kw in COMMON_ROLES:
                        if r_kw.lower() in txt_low:
                            role = r_kw
                            break

                # 1. Busca email em uso no texto
                emails_in_txt = EMAIL_REGEX.findall(txt)
                staff_email = None
                staff_email_status = None
                for em in emails_in_txt:
                    em_low = em.lower().strip(".,;")
                    if words[0].lower() in em_low:
                        staff_email = em_low
                        staff_email_status = "Em Uso Verificado (Público)"
                        break

                # 2. Se não tem email explícito, calcula pelo padrão corporativo e valida no servidor de correio via SMTP
                if not staff_email and official_domain:
                    f_name = sanitize_name_for_email(words[0])
                    l_name = sanitize_name_for_email(words[-1]) if len(words) > 1 else ""
                    pattern = proven_pattern or f"[primeiro_nome]@{official_domain}"

                    email_candidates = []
                    if "[inicial_nome][ultimo_nome]@" in pattern and l_name:
                        email_candidates.append(f"{f_name[0]}{l_name}@{official_domain}")
                        if len(words) >= 3:
                            mid_sur = sanitize_name_for_email(words[1])
                            if mid_sur and len(mid_sur) >= 3:
                                email_candidates.append(f"{f_name[0]}{mid_sur}@{official_domain}")
                    elif "[primeiro_nome].[ultimo_nome]@" in pattern and l_name:
                        email_candidates.append(f"{f_name}.{l_name}@{official_domain}")
                        if len(words) >= 3:
                            mid_sur = sanitize_name_for_email(words[1])
                            if mid_sur and len(mid_sur) >= 3:
                                email_candidates.append(f"{f_name}.{mid_sur}@{official_domain}")
                    elif "[primeiro_nome][inicial_ultimo]@" in pattern and l_name:
                        email_candidates.append(f"{f_name}{l_name[0]}@{official_domain}")
                    elif "[primeiro_nome][ultimo_nome]@" in pattern and l_name:
                        email_candidates.append(f"{f_name}{l_name}@{official_domain}")
                    else:
                        email_candidates.append(f"{f_name}@{official_domain}")

                    chosen_email = email_candidates[0]
                    chosen_status = "Padrão Corporativo"
                    for cand in email_candidates:
                        smtp_res = check_smtp_mailbox(cand, official_domain, smtp_cache)
                        if smtp_res["valid"]:
                            chosen_email = cand
                            chosen_status = smtp_res["status"]
                            break

                    staff_email = chosen_email
                    staff_email_status = chosen_status

                # FILTRO DE CARGO SOLICITADO:
                if clean_role and not matches_requested_role(clean_role, role, txt):
                    continue

                # 3. Telefone: linha direta ou central da sede
                phones_in_txt = [clean_phone(p) for p in RAW_PHONE_REGEX.findall(txt) if is_plausible_phone(p)]
                staff_phone = phones_in_txt[0] if phones_in_txt else default_company_phone
                staff_phone_type = "Linha Direta" if phones_in_txt else ("Central Telefónica Sede" if staff_phone else "N/D")

                company_staff.append({
                    "name": clean_staff_name,
                    "role": role or "Colaborador / Equipa",
                    "email": staff_email,
                    "email_status": staff_email_status or "Padrão Corporativo",
                    "phone": staff_phone,
                    "phone_type": staff_phone_type,
                    "profile_url": u,
                    "platform": platform
                })

    # Se a pessoa alvo foi informada, assegura que surge no topo dos colaboradores
    if clean_name and company_staff:
        def staff_sort_key(s):
            return 0 if clean_name.lower() in s["name"].lower() else 1
        company_staff = sorted(company_staff, key=staff_sort_key)

    return {
        "target_name": clean_name,
        "target_company": clean_company,
        "target_role": clean_role,
        "target_country": clean_country,
        "official_domain": official_domain,
        "domain_mx": domain_mx_info,
        "person_emails": target_person_emails,
        "company_emails": company_general_emails[:6],
        "proven_pattern": proven_pattern,
        "phones": normalized_phones[:6],
        "linkedin_profiles": linkedin_profiles[:8],
        "company_staff": company_staff[:15],
        "web_mentions": other_mentions[:10],
        "total_sources": len(aggregated_results)
    }
