# CONTEXTO PERMANENTE — NetContactos

- **Nome do Projeto:** NetContactos (Plataforma de Investigação, Localização e OSINT)
- **Autor e Proprietário:** José Centúrio
- **Data de Atualização:** 09/10/2026 17:48
- **Estado do Sistema:** ✅ 100% Operacional — Formatos de Email Corporativo Rigorosos e Validados (Sem Falsos Positivos de Primeiro Nome Isolado)

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
   `Z:\Nuvem_Hosting\users\centurio\www\Api Contactos\.venv\`
4. **Serviço Windows em Background & Auto-Healing:**
   - Tarefa Agendada `Centauro_Watchdog` executa a cada 2 minutos `start_centauro_boot.ps1` com verificação da porta 8000.
   - Supervisor Integrado em `Z:\Nuvem_Hosting\server\server.js`: verificação ativa a cada 30s e arranque automático on-demand com retry transparente na receção de pedidos API.

---

## 🛠️ Arquitetura Técnica e Módulos

### 1. Motor de Investigação: Pessoas, Empresas & Colaboradores (`/api/person/search`)
- **Ficheiros:** `app/services/people_service.py`, `app/services/searxng_service.py`, `frontend/app.js`, `frontend/index.html`.
- **Capacidades Operacionais:**
  - **Pesquisa Flexível Multi-Campo ou Campo Único:** Permite pesquisar isoladamente por qualquer campo (Nome, Empresa, Cargo ou País/Cidade) ou de forma combinada, sem obrigar ao preenchimento do nome.
  - **Filtragem Geográfica e de Cargo Estrita Multi-Critério:** Quando é indicado um país (ex: Espanha, Portugal), apenas colaboradores comprovadamente sediados nesse país são retornados. Colaboradores de filiais estrangeiras ou outros países são estritamente excluídos.
  - **Isolamento Absoluto do Domínio Corporativo Oficial:** Identifica o domínio oficial e os registos MX da empresa. A lista de emails corporativos gerais inclui exclusivamente endereços pertencentes ao domínio da empresa pesquisada, eliminando ruído ou domínios de terceiros.
  - **Priorização do Telefone da Sede e Desduplicação:** O número de telefone recolhido diretamente da página de contacto oficial da empresa é colocado em prioridade máxima, formatado internacionalmente (ex: `+34 945 128 415`, `+351 961 001 626`) e atribuído como central da sede aos colaboradores.
  - **Fórmula de Email Preditiva e Verificação SMTP:** Analisa a percentagem predominante dos padrões corporativos (`[inicial_nome][ultimo_nome]`, `[primeiro_nome].[ultimo_nome]`, `[primeiro_nome]`) e valida caixas ativas com handshake SMTP contra o servidor de correio da empresa.
  - **Correção Automática de Caracteres Acentuados:** Normalização algorítmica para nomes espanhóis e portugueses com acentuação correta (`Jesús`, `Alegría`, `José`, `Luís`, `Patrícia`, etc.).
  - **Cards Visuais Dedicados:** Apresenta a grelha interactiva de colaboradores identificados com foto/iniciais, cargo, botões de ação e status de precisão.
  - **Placeholders Limpos:** Todos os campos de introdução mantêm-se limpos sem nomes ou empresas de exemplo.

### 2. Auto-Healing e Resiliência Permanente (Eliminação do Erro 502)
- O servidor Centauro (`server.js`) intercepta chamadas na porta 8000. Caso a porta esteja em baixo por reinício ou suspensão do sistema, o Centauro dispara autonomamente o daemon Python em segundo plano, aguarda pela prontidão e serve o pedido com HTTP 200 OK sem expor erros ao utilizador.
