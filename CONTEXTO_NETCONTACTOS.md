# CONTEXTO PERMANENTE — NetContactos

- **Nome do Projeto:** NetContactos (Plataforma de Investigação, Localização e OSINT)
- **Autor e Proprietário:** José Centúrio
- **Data de Atualização:** 08/10/2026 19:30
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

### 1. Novo Motor: Pesquisa de Pessoas & Empresas (`/api/person/search`)
- **Ficheiros:** `app/services/people_service.py` e `app/routers/people.py`
- **Capacidades:**
  - Localiza perfis profissionais no **LinkedIn**, **CVs**, redes empresariais e diretórios com excertos da carreira.
  - Extrai emails reais presentes nas páginas públicas.
  - Gera **previsões de emails corporativos** (`nome.apelido@empresa.com`, `napelido@empresa.com`, etc.) com botão de cópia com 1 clique.
  - Recolhe menções em notícias, comunicados e páginas oficiais da empresa.
  - Gera variações de username para testar nas redes sociais.

### 2. Correção de Conexão Web & Portas Cloudflare
- **Causa Raiz Identificada:** O `app.js` antigo forçava a porta `:8000` quando acedido pelo domínio `sigec-pro.com`. Como a Cloudflare apenas aceita a porta padrão 443 (HTTPS), o browser ficava eternamente bloqueado em *"A conectar ao motor de varredura..."*.
- **Solução Implementada:** `API_BASE = ''` (URL relativo). O tráfego passa na porta 443 normal para o Centauro (`server.js`), que faz proxy reverso transparente para o FastAPI na porta 8000.
- **Cache-Buster & Headers:** Atualizado `app.js?v=20261008_2` e adicionados cabeçalhos `Cache-Control: no-cache` em `server.js`.

### 3. Blindagem da Aba de Username
- **Deteção de Nomes com Espaço:** Se o utilizador escrever um nome como `Paula Gracia`, o sistema:
  - Exibe um alerta inteligente sugerindo a nova aba "Pessoas & Empresas".
  - Higieniza automaticamente o username para `@paulagracia` sem crashar nem bloquear a pesquisa.
