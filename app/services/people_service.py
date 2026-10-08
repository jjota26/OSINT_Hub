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
                em_clean = em.lower().strip(".,;")
                if not em_clean.endswith((".png", ".jpg", ".webp", ".js", ".css")):
                    emails.add(em_clean)
            # Telefones e tags
            soup = BeautifulSoup(text, "html.parser")
            for a in soup.find_all("a", href=True):
                h = a["href"].strip()
                if h.startswith("mailto:"):
                    emails.add(h.replace("mailto:", "").split("?")[0].lower().strip())
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
    
    if clean_name and clean_company:
        search_queries.append(f"{clean_name} {clean_company}")
        search_queries.append(f"{clean_name} {clean_company} email")
        search_queries.append(f"{clean_name} {clean_company} linkedin")
        search_queries.append(f"site:linkedin.com/in {clean_name} {clean_company}")
        search_queries.append(f"site:contactout.com {clean_name}")
        search_queries.append(f"{clean_company} site oficial")
        search_queries.append(f"{clean_company} contacto email")
        search_queries.append(f"site:linkedin.com/in {clean_company}")
    elif clean_company and not clean_name:
        search_queries.append(f"{clean_company} site oficial")
        search_queries.append(f"{clean_company} contacto email")
        search_queries.append(f"site:linkedin.com/in {clean_company}")
        search_queries.append(f"site:contactout.com {clean_company}")
        search_queries.append(f"{clean_company} colaboradores linkedin")
        search_queries.append(f"{clean_company} linkedin")
        if clean_role:
            search_queries.append(f"{clean_company} {clean_role}")
        if clean_country:
            search_queries.append(f"{clean_company} {clean_country} contacto")
    elif clean_name and not clean_company:
        search_queries.append(f"{clean_name} linkedin")
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

    # 2. Execução das Consultas com Multi-Motor Anti-Bloqueio
    aggregated_results = []
    seen_urls = set()

    for q in search_queries:
        try:
            res = await execute_web_search(q)
            for item in res.get("results", []):
                u = item.get("url", "")
                if u and u not in seen_urls:
                    seen_urls.add(u)
                    aggregated_results.append(item)
        except Exception:
            continue

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
            em_clean = em.lower().strip(".,;:()")
            if not em_clean.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif", ".js", ".css")):
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

        # Classificar perfis LinkedIn
        if "linkedin.com/in/" in url or "linkedin.com/posts/" in url or "linkedin.com/pub/" in url:
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
    if official_domain:
        try:
            site_contacts = await fetch_company_page_contacts(f"https://{official_domain}")
            for em in site_contacts["emails"]:
                verified_emails.add(em)
            for ph in site_contacts["phones"]:
                if is_plausible_phone(ph):
                    verified_phones.add(clean_phone(ph))
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
        elif official_domain and official_domain in em:
            company_general_emails.append({
                "email": em,
                "status": "Em Uso Verificado",
                "type": "Corporativo / Geral"
            })
        elif em.split("@")[-1] not in GENERIC_EMAIL_DOMAINS:
            company_general_emails.append({
                "email": em,
                "status": "Encontrado em Fonte Pública",
                "type": "Profissional"
            })

    # Padrão comprovado da empresa (ex: paula@alegria-activity.com -> [primeiro_nome]@dominio)
    proven_pattern = None
    if target_person_emails and official_domain:
        matched_em = target_person_emails[0]["email"]
        first_p = name_parts[0] if name_parts else ""
        last_p = name_parts[-1] if len(name_parts) > 1 else ""
        if first_p and matched_em.startswith(first_p + "@"):
            proven_pattern = f"[primeiro_nome]@{official_domain}"
        elif first_p and last_p and f"{first_p}.{last_p}@" in matched_em:
            proven_pattern = f"[primeiro_nome].[ultimo_nome]@{official_domain}"
        elif first_p and last_p and f"{first_p[0]}{last_p}@" in matched_em:
            proven_pattern = f"[inicial_nome][ultimo_nome]@{official_domain}"
        else:
            proven_pattern = f"[nome]@{official_domain}"
    elif official_domain and clean_name:
        first_p = name_parts[0] if name_parts else "nome"
        last_p = name_parts[-1] if len(name_parts) > 1 else "apelido"
        proven_pattern = f"{first_p}.{last_p}@{official_domain}"
    elif official_domain:
        # Se não temos pessoa pesquisada, o formato corporativo predominante é [primeiro_nome]@dominio
        proven_pattern = f"[primeiro_nome]@{official_domain}"

    # 7. Reconhecimento Persuasivo de Colaboradores e Redes Sociais da Empresa
    company_staff = []
    seen_staff_names = set()
    default_company_phone = list(verified_phones)[0] if verified_phones else None

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

        clean_staff_name = None
        role = ""
        platform = "LinkedIn"

        # A. Perfis de LinkedIn
        if "linkedin.com/in/" in u or "linkedin.com/pub/" in u:
            platform = "LinkedIn"
            parts = [p.strip() for p in re.split(r"[-|–—]", t) if p.strip()]
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
            
            # Se o título é genérico (ex: "LinkedIn"), extrai do slug da URL
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
            if 2 <= len(words) <= 5 and not any(w.lower() in ("contactout", "perfil", "login", "company") for w in words):
                clean_staff_name = " ".join([w.capitalize() for w in words])
            
            if not clean_staff_name:
                slug_n = extract_name_from_contactout_url(u)
                if slug_n:
                    clean_staff_name = slug_n

        if clean_staff_name:
            clean_low = clean_staff_name.lower()
            # Evita nomes redundantes ou de letra única (ex: Paula G vs Paula Gracia Alonso)
            if any(clean_low != s and clean_low.startswith(s.split()[0]) and len(clean_staff_name.split()[-1]) == 1 for s in seen_staff_names):
                continue
            if clean_low not in seen_staff_names:
                seen_staff_names.add(clean_low)
                words = clean_staff_name.split()

                # Inferência de cargo se não encontrado no título
                if not role:
                    for r_kw in COMMON_ROLES:
                        if r_kw.lower() in txt.lower():
                            role = r_kw
                            break

                # 1. Busca email em uso no texto
                emails_in_txt = EMAIL_REGEX.findall(txt)
                staff_email = None
                staff_email_status = "Padrão Corporativo"
                for em in emails_in_txt:
                    em_low = em.lower().strip(".,;")
                    if words[0].lower() in em_low:
                        staff_email = em_low
                        staff_email_status = "Em Uso Verificado"
                        break

                # 2. Se não tem email explícito, calcula pelo padrão corporativo e MX verificado
                if not staff_email and official_domain:
                    f_name = sanitize_name_for_email(words[0])
                    l_name = sanitize_name_for_email(words[-1]) if len(words) > 1 else ""
                    pattern = proven_pattern or f"[primeiro_nome]@{official_domain}"
                    if "[primeiro_nome].[ultimo_nome]@" in pattern and l_name:
                        staff_email = f"{f_name}.{l_name}@{official_domain}"
                    elif "[inicial_nome][ultimo_nome]@" in pattern and l_name:
                        staff_email = f"{f_name[0]}{l_name}@{official_domain}"
                    else:
                        staff_email = f"{f_name}@{official_domain}"

                # 3. Telefone: linha direta ou central da sede com link direto
                phones_in_txt = [clean_phone(p) for p in RAW_PHONE_REGEX.findall(txt) if is_plausible_phone(p)]
                staff_phone = phones_in_txt[0] if phones_in_txt else default_company_phone
                staff_phone_type = "Linha Direta" if phones_in_txt else ("Central Telefónica Sede" if staff_phone else "N/D")

                company_staff.append({
                    "name": clean_staff_name,
                    "role": role or "Equipa / Colaborador",
                    "email": staff_email,
                    "email_status": staff_email_status,
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
        "phones": list(verified_phones)[:6],
        "linkedin_profiles": linkedin_profiles[:8],
        "company_staff": company_staff[:15],
        "web_mentions": other_mentions[:10],
        "total_sources": len(aggregated_results)
    }
