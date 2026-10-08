# 🛰️ NetContactos — Plataforma de Investigação e OSINT

Plataforma completa de inteligência de fontes abertas (OSINT) construída em **FastAPI**, com integração de **Sherlock**, **Maigret**, **SearXNG** e **Web Scraper**, desenhada para ser assíncrona, escalável e 100% gratuita.

---

## ⚡ Funcionalidades

1. **Pesquisa de Username (OSINT)**:
   - **QuickScan**: Varredura ultra-rápida (2 a 4 segundos) em redes prioritárias (GitHub, Reddit, Telegram, Steam, Twitch, etc.).
   - **Sherlock**: Varredura profunda em 400+ plataformas.
   - **Maigret**: Varredura avançada com ranking de tráfego.
   - **Streaming em Tempo Real**: Conexão Server-Sent Events (SSE) sem timeout HTTP.
2. **Busca Web Geral (SearXNG)**:
   - Consulta meta-motor SearXNG local ou via instâncias públicas seguras/DuckDuckGo.
   - Ideal para pesquisar por nome completo, email corporativo ou palavras-chave.
3. **Extrator de Contactos & Scraping**:
   - Extrai automaticamente emails, telefones e redes sociais vinculadas de qualquer página web.
4. **Dashboard Web Moderno**:
   - Interface SPA escura, intuitiva, com filtros em direto e exportação para **JSON** e **CSV**.
5. **Resiliência e Proteções**:
   - Rate limiting automático com SlowAPI (evita bloqueios de IP).
   - Cache com TTL para não repetir consultas idênticas.
   - Correção automática de certificados SSL para Windows.

---

## 🚀 Como Executar Localmente (Windows)

### Opção 1: Clique Duplo
Basta dar duplo clique no ficheiro:
```cmd
run.bat
```

### Opção 2: Linha de Comandos
Com o ambiente virtual configurado:
```powershell
.\.venv\Scripts\python.exe start.py
```

Aceda no navegador:
* **Interface Web:** [http://localhost:8000](http://localhost:8000)
* **Documentação Swagger:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🐳 Como Executar com Docker (SearXNG + Redis + API)

Se tiver o Docker instalado ou for fazer deploy num VPS:
```bash
docker-compose up -d
```
Isto iniciará automaticamente:
* A API em `http://localhost:8000`
* O SearXNG local em `http://localhost:8080`
* O Redis para cache em `localhost:6379`

---

## 📡 Endpoints Principais da API

| Método | Endpoint | Descrição |
|---|---|---|
| `GET` | `/` | Interface Gráfica Web |
| `GET` | `/api/username/quick/{username}` | Verificação rápida JSON (~3 seg) |
| `GET` | `/api/username/stream/{username}?engine=all` | Streaming SSE em tempo real |
| `GET` | `/api/search/web?q=termo` | Busca web meta-engine (SearXNG) |
| `GET` | `/api/scraper/extract?url=...` | Extrai emails, telefones e redes sociais |
| `GET` | `/api/system/health` | Estado dos motores e da API |
