# CONTEXTO PERMANENTE — NetContactos

- **Nome do Projeto:** NetContactos (Plataforma de Investigação, Localização e OSINT)
- **Autor e Proprietário:** José Centúrio
- **Data de Atualização:** 08/10/2026 21:05
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
   `Z:\Nuvem_Hosting\users\centurio\www\Api Contactos\.venv\`
4. **Serviço Windows em Background:**
   Tarefa agendada `NetContactos` (FastAPI porta 8000).

---

## 🛠️ Arquitetura Técnica e Módulos

### 1. Motor de Investigação: Pessoas, Empresas & Colaboradores (`/api/person/search`)
- **Ficheiros:** `app/services/people_service.py`, `app/services/searxng_service.py`, `frontend/app.js`, `frontend/index.html`.
- **Capacidades Operacionais:**
  - **Pesquisa Flexível Multi-Campo ou Campo Único:** Permite pesquisar isoladamente por qualquer campo (Nome, Empresa, Cargo ou País/Cidade) ou de forma combinada, sem obrigar ao preenchimento do nome.
  - **Identificação do Domínio e Validação MX:** Localiza o domínio corporativo oficial e valida os registos DNS MX em tempo real.
  - **Rastreio Social Dissimulado & Anti-Bloqueio:** Utiliza multi-motor com impersonação TLS (Chrome 120), Yahoo Search com descodificação de redirecionamentos `/RU=` e SearXNG, contornando bloqueios de scraping.
  - **Extração Furtiva de Colaboradores de Redes Sociais:**
    - Localiza perfis do **LinkedIn** e diretórios executivos (**ContactOut**).
    - Extrai nomes completos (mesmo a partir dos slugs de URL descarregados), cargos profissionais e ligações diretas aos perfis.
    - Associa o email verificado em uso real ou projeta o endereço de email de acordo com o padrão corporativo comprovado da empresa (`[primeiro_nome]@dominio`, `[primeiro_nome].[ultimo_nome]@dominio`, etc.).
    - Associa telefones em uso (linha direta individual ou central telefónica da sede com botão de ligação e cópia).
  - **Cards Visuais Dedicados:** Apresenta a grelha interactiva de colaboradores identificados com foto/iniciais, cargo, botões de ação e status de precisão.
  - **Placeholders Limpos:** Todos os campos de introdução mantêm-se limpos sem nomes de exemplo.
