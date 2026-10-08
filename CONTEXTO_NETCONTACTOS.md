# CONTEXTO PERMANENTE — NetContactos

- **Nome do Projeto:** NetContactos (Plataforma de Investigação, Localização e OSINT)
- **Autor e Proprietário:** José Centúrio
- **Data de Criação:** 08/10/2026
- **Estado do Sistema:** ✅ 100% Operacional, Online e Conectado Globalmente

---

## 🌐 URLs de Produção e Acesso

- **Domínio Principal Dedicado (HTTPS):** [https://netcontactos.sigec-pro.com](https://netcontactos.sigec-pro.com)
- **Acesso via Centauro (HTTPS):** [https://centauro.sigec-pro.com/sites/centurio/Api%20Contactos/index.html](https://centauro.sigec-pro.com/sites/centurio/Api%20Contactos/index.html)
- **Servidor Local (Swagger / API Docs):** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Servidor Local (Dashboard Web):** [http://localhost:8000](http://localhost:8000)
- **Repositório GitHub Oficial:** [https://github.com/jjota26/OSINT_Hub](https://github.com/jjota26/OSINT_Hub)

---

## 📁 Estrutura de Ficheiros e Diretórios

1. **Servidor Local (Disco Z:\):**
   `Z:\Nuvem_Hosting\users\centurio\www\Api Contactos\`
2. **Ambiente de Desenvolvimento (Disco N:\):**
   `N:\Projectos Python\OSINT_Hub\`
3. **Ambiente Virtual Python:**
   `N:\Projectos Python\OSINT_Hub\.venv\`
4. **Scripts de Arranque do Servidor:**
   - `Z:\Nuvem_Hosting\INICIAR_CENTAURO.bat` (inicia Centauro + NetContactos em segundo plano)
   - `Z:\Nuvem_Hosting\PARAR_CENTAURO.bat` (encerra os serviços)
   - `Z:\Nuvem_Hosting\scripts\start_centauro.ps1` (orquestrador de processos em background)
   - `run.bat` e `start.py` (arranque direto independente do NetContactos)

---

## 🛠️ Arquitetura Técnica e Módulos

### 1. Backend (FastAPI + Python 3.14)
- **Framework:** FastAPI assíncrono com Uvicorn.
- **Resolução SSL:** `app/core/ssl_patch.py` (corrige certificados SSL no Windows com `certifi` e `truststore`).
- **Rate Limiting:** `app/core/limiter.py` (SlowAPI prevenindo bloqueios de IP).
- **Cache:** `app/core/cache.py` (Cache em memória com TTL).

### 2. Motores de Investigação
- **QuickScan (`app/services/quick_checker.py`):**
  - Varredura assíncrona nas 25 maiores redes (GitHub, Reddit, Telegram, Steam, Twitch, GitLab, etc.) em 2 a 4 segundos.
- **Sherlock (`app/services/sherlock_service.py`):**
  - Subprocesso assíncrono para 400+ plataformas com streaming SSE (`/api/username/stream/{user}?engine=sherlock`).
- **Maigret (`app/services/maigret_service.py`):**
  - Subprocesso assíncrono cobrindo 6000+ plataformas com ranking de tráfego.
- **SearXNG & Meta-Busca Web (`app/services/searxng_service.py`):**
  - Conecta-se ao SearXNG local (`http://localhost:8080`) com fallback inteligente para DuckDuckGo e instâncias públicas seguras.
- **Scraper de Contactos (`app/services/scraper_service.py`):**
  - Extrai emails, telemóveis/telefones e redes sociais vinculadas em qualquer URL.

### 3. Frontend Reativo
- **Dashboard Web SPA:** `frontend/index.html` e `frontend/app.js` servido na raiz.
- **Design:** Tema escuro moderno com Tailwind CSS.
- **Comunicação em Tempo Real:** Server-Sent Events (SSE) com preenchimento progressivo de resultados sem recarregar a página.
- **Exportação:** Exportação dos dados encontrados para JSON e CSV.

### 4. Infraestrutura de Rede
- **Cloudflare Tunnel (`cloudflared`):** Rota DNS automática `netcontactos.sigec-pro.com`.
- **Servidor Centauro (`Z:\Nuvem_Hosting\server\server.js`):** Virtual Host dedicado encaminhando `/api` e o frontend na raiz para a porta 8000.
