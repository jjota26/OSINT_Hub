// URL Base Dinâmica da API
// Em produção, no domínio web com Cloudflare Tunnel e no Centauro, as rotas /api/ são servidas na mesma origem (URL relativo)
const API_BASE = '';

// Estado global
let foundProfiles = [];
let eventSource = null;
let currentPersonData = null;

// Helper para copiar texto
function copyToClipboard(text, btnElement) {
  navigator.clipboard.writeText(text).then(() => {
    if (btnElement) {
      const original = btnElement.innerHTML;
      btnElement.innerHTML = `<i class="fa-solid fa-check text-emerald-400"></i>`;
      setTimeout(() => { btnElement.innerHTML = original; }, 2000);
    }
  });
}

// Tab switcher
function switchTab(tabId) {
  document.querySelectorAll('.tab-pane').forEach(el => el.classList.add('hidden'));
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.classList.remove('bg-indigo-600', 'text-white', 'shadow-md', 'shadow-indigo-600/20');
    btn.classList.add('bg-zinc-900', 'text-zinc-400');
  });

  const activeContent = document.getElementById(`tab-content-${tabId}`);
  const activeBtn = document.getElementById(`tab-btn-${tabId}`);
  if (activeContent) activeContent.classList.remove('hidden');
  if (activeBtn) {
    activeBtn.classList.remove('bg-zinc-900', 'text-zinc-400');
    activeBtn.classList.add('bg-indigo-600', 'text-white', 'shadow-md', 'shadow-indigo-600/20');
  }
}

// Icon helper
function getPlatformIcon(siteName) {
  const name = (siteName || '').toLowerCase();
  if (name.includes('github') || name.includes('gitlab')) return 'fa-brands fa-github';
  if (name.includes('twitter') || name.includes('x')) return 'fa-brands fa-x-twitter';
  if (name.includes('linkedin')) return 'fa-brands fa-linkedin text-sky-400';
  if (name.includes('reddit')) return 'fa-brands fa-reddit-alien';
  if (name.includes('telegram')) return 'fa-brands fa-telegram';
  if (name.includes('steam')) return 'fa-brands fa-steam';
  if (name.includes('youtube')) return 'fa-brands fa-youtube';
  if (name.includes('twitch')) return 'fa-brands fa-twitch';
  if (name.includes('pinterest')) return 'fa-brands fa-pinterest';
  if (name.includes('spotify') || name.includes('soundcloud')) return 'fa-brands fa-spotify';
  if (name.includes('medium')) return 'fa-brands fa-medium';
  if (name.includes('instagram')) return 'fa-brands fa-instagram text-pink-400';
  if (name.includes('facebook')) return 'fa-brands fa-facebook text-blue-500';
  if (name.includes('tiktok')) return 'fa-brands fa-tiktok';
  return 'fa-solid fa-link';
}

// ==========================================
// 1. INVESTIGAÇÃO DE PESSOAS & EMPRESAS
// ==========================================

async function startPersonSearch(event) {
  if (event) event.preventDefault();
  const name = document.getElementById('person-name-input').value.trim();
  const company = document.getElementById('person-company-input').value.trim();
  const role = document.getElementById('person-role-input').value.trim();
  const country = document.getElementById('person-country-input').value.trim();

  if (!name) return;

  const btn = document.getElementById('btn-search-person');
  const container = document.getElementById('person-results-container');

  btn.disabled = true;
  btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i><span>A investigar na web...</span>`;
  container.classList.remove('hidden');
  container.innerHTML = `
    <div class="bg-zinc-900/60 border border-zinc-800 rounded-2xl p-8 text-center space-y-4">
      <div class="inline-flex p-3 rounded-2xl bg-indigo-600/10 text-indigo-400 border border-indigo-500/20 pulsing">
        <i class="fa-solid fa-magnifying-glass text-2xl"></i>
      </div>
      <div>
        <h3 class="text-base font-bold text-white">A investigar ${name}${company ? ' na ' + company : ''}...</h3>
        <p class="text-xs text-zinc-400 mt-1">A consultar motores de busca, LinkedIn, bases públicas e a calcular probabilidades de emails.</p>
      </div>
    </div>
  `;

  try {
    const params = new URLSearchParams({ name });
    if (company) params.append('company', company);
    if (role) params.append('role', role);
    if (country) params.append('country', country);

    const res = await fetch(`${API_BASE}/api/person/search?${params.toString()}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    currentPersonData = data;
    renderPersonResults(data);
  } catch (err) {
    container.innerHTML = `
      <div class="bg-red-500/10 border border-red-500/30 rounded-2xl p-6 text-red-300 text-sm">
        <i class="fa-solid fa-triangle-exclamation mr-2"></i> Erro ao realizar pesquisa: ${err.message}
      </div>
    `;
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i class="fa-solid fa-magnifying-glass"></i><span>Investigar Pessoa</span>`;
  }
}

function renderPersonResults(data) {
  const container = document.getElementById('person-results-container');
  const hasLinkedIn = data.linkedin_profiles && data.linkedin_profiles.length > 0;
  const hasEmails = data.predicted_emails && data.predicted_emails.length > 0;
  const hasMentions = data.web_mentions && data.web_mentions.length > 0;
  const hasExtracted = data.extracted_emails && data.extracted_emails.length > 0;

  let html = `
    <!-- Top Summary Card -->
    <div class="bg-gradient-to-r from-zinc-900 to-zinc-900/80 border border-zinc-800 rounded-2xl p-6 flex flex-wrap items-center justify-between gap-4 shadow-xl">
      <div class="flex items-center space-x-4">
        <div class="w-12 h-12 rounded-xl bg-indigo-600/20 border border-indigo-500/30 text-indigo-400 flex items-center justify-center text-xl font-bold">
          ${data.person_name.charAt(0).toUpperCase()}
        </div>
        <div>
          <h3 class="text-lg font-bold text-white">${data.person_name}</h3>
          <p class="text-xs text-zinc-400 flex items-center space-x-2 mt-0.5">
            ${data.company ? `<span><i class="fa-solid fa-building text-indigo-400 mr-1"></i>${data.company}</span>` : ''}
            ${data.role ? `<span>• <i class="fa-solid fa-briefcase text-zinc-400 mr-1"></i>${data.role}</span>` : ''}
          </p>
        </div>
      </div>
      <div class="flex items-center space-x-3 text-xs">
        <span class="px-3 py-1.5 rounded-lg bg-zinc-800 text-zinc-300 font-mono">
          <strong class="text-emerald-400">${data.total_mentions}</strong> referências web
        </span>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
      
      <!-- Coluna Esquerda: Perfis Profissionais & Menções -->
      <div class="lg:col-span-7 space-y-6">
        
        <!-- LinkedIn e Perfis Profissionais -->
        <div class="bg-zinc-900/60 border border-zinc-800 rounded-2xl p-6 space-y-4">
          <h4 class="text-xs uppercase font-bold tracking-wider text-zinc-400 flex items-center justify-between">
            <span class="flex items-center space-x-2">
              <i class="fa-brands fa-linkedin text-sky-400 text-base"></i>
              <span>Perfis Profissionais Detetados</span>
            </span>
            <span class="text-sky-400 font-mono">${data.linkedin_profiles.length}</span>
          </h4>

          <div class="space-y-3">
            ${hasLinkedIn ? data.linkedin_profiles.map(p => `
              <div class="p-4 bg-zinc-950 rounded-xl border border-zinc-800/80 hover:border-sky-500/40 transition space-y-2 group">
                <div class="flex items-start justify-between">
                  <h5 class="text-sm font-semibold text-white group-hover:text-sky-400 transition">
                    <a href="${p.url}" target="_blank" rel="noopener noreferrer">${p.title}</a>
                  </h5>
                  <a href="${p.url}" target="_blank" rel="noopener noreferrer" class="text-zinc-500 hover:text-white text-xs pl-2">
                    <i class="fa-solid fa-arrow-up-right-from-square"></i>
                  </a>
                </div>
                <p class="text-xs text-zinc-400 line-clamp-3">${p.snippet || 'Sem pré-visualização'}</p>
                <div class="pt-1">
                  <span class="text-[11px] font-mono text-sky-400/80 truncate block">${p.url}</span>
                </div>
              </div>
            `).join('') : '<p class="text-xs text-zinc-500 py-3">Nenhum perfil direto do LinkedIn detetado com estes termos exatos.</p>'}
          </div>
        </div>

        <!-- Redes Sociais Gerais & Menções Web -->
        <div class="bg-zinc-900/60 border border-zinc-800 rounded-2xl p-6 space-y-4">
          <h4 class="text-xs uppercase font-bold tracking-wider text-zinc-400 flex items-center justify-between">
            <span class="flex items-center space-x-2">
              <i class="fa-solid fa-globe text-indigo-400 text-sm"></i>
              <span>Menções na Web & Notícias</span>
            </span>
            <span class="text-indigo-400 font-mono">${data.web_mentions.length}</span>
          </h4>

          <div class="space-y-3">
            ${hasMentions ? data.web_mentions.map(m => `
              <div class="p-3 bg-zinc-950/80 rounded-xl border border-zinc-800/60 hover:border-zinc-700 transition space-y-1">
                <div class="flex items-start justify-between">
                  <h5 class="text-xs font-semibold text-white truncate max-w-md">
                    <a href="${m.url}" target="_blank" rel="noopener noreferrer" class="hover:text-indigo-400 hover:underline">${m.title}</a>
                  </h5>
                  <a href="${m.url}" target="_blank" rel="noopener noreferrer" class="text-zinc-500 hover:text-white text-[11px] pl-2">
                    <i class="fa-solid fa-arrow-up-right-from-square"></i>
                  </a>
                </div>
                <p class="text-[11px] text-zinc-400 line-clamp-2">${m.snippet || ''}</p>
                <span class="text-[10px] font-mono text-zinc-500 truncate block">${m.url}</span>
              </div>
            `).join('') : '<p class="text-xs text-zinc-500 py-2">Sem menções adicionais encontradas.</p>'}
          </div>
        </div>

      </div>

      <!-- Coluna Direita: Previsão de Emails & Usernames -->
      <div class="lg:col-span-5 space-y-6">
        
        <!-- Emails Corporativos Previstos -->
        <div class="bg-zinc-900/60 border border-zinc-800 rounded-2xl p-6 space-y-4">
          <div>
            <h4 class="text-xs uppercase font-bold tracking-wider text-zinc-400 flex items-center justify-between">
              <span class="flex items-center space-x-2">
                <i class="fa-solid fa-envelope text-emerald-400 text-sm"></i>
                <span>Emails Profissionais Prováveis</span>
              </span>
              <span class="text-emerald-400 font-mono">${data.predicted_emails.length}</span>
            </h4>
            <p class="text-[11px] text-zinc-500 mt-1">Padrões de email mais utilizados pelas empresas para este nome:</p>
          </div>

          <div class="space-y-2 max-h-72 overflow-y-auto pr-1">
            ${hasEmails ? data.predicted_emails.map(e => `
              <div class="flex items-center justify-between p-2.5 bg-zinc-950 rounded-xl border border-zinc-800 hover:border-emerald-500/40 transition">
                <span class="font-mono text-xs text-zinc-200 select-all">${e.email}</span>
                <button onclick="copyToClipboard('${e.email}', this)" class="p-1.5 px-2 bg-zinc-900 hover:bg-zinc-800 rounded-lg text-zinc-400 hover:text-white transition text-xs" title="Copiar Email">
                  <i class="fa-regular fa-copy"></i>
                </button>
              </div>
            `).join('') : '<p class="text-xs text-zinc-500 py-2">Indique a empresa para calcular previsões de email corporativo.</p>'}
          </div>

          ${hasExtracted ? `
            <div class="pt-3 border-t border-zinc-800">
              <span class="text-[11px] font-semibold text-emerald-400 block mb-2">Emails Encontrados no Texto Público:</span>
              <div class="space-y-1.5">
                ${data.extracted_emails.map(em => `
                  <div class="flex items-center justify-between p-2 bg-emerald-950/20 border border-emerald-500/30 rounded-lg text-xs font-mono text-emerald-300">
                    <span>${em}</span>
                    <button onclick="copyToClipboard('${em}', this)" class="text-zinc-400 hover:text-white"><i class="fa-regular fa-copy"></i></button>
                  </div>
                `).join('')}
              </div>
            </div>
          ` : ''}
        </div>

        <!-- Variações de Username para OSINT -->
        <div class="bg-zinc-900/60 border border-zinc-800 rounded-2xl p-6 space-y-4">
          <div>
            <h4 class="text-xs uppercase font-bold tracking-wider text-zinc-400 flex items-center space-x-2">
              <i class="fa-solid fa-at text-indigo-400 text-sm"></i>
              <span>Variações de Username (OSINT)</span>
            </h4>
            <p class="text-[11px] text-zinc-500 mt-1">Possíveis perfis associados a esta pessoa nas redes:</p>
          </div>

          <div class="flex flex-wrap gap-2">
            ${data.username_variants.map(u => `
              <button onclick="investigateVariant('${u}')" class="px-2.5 py-1.5 rounded-lg bg-zinc-950 border border-zinc-800 hover:border-indigo-500/50 hover:bg-zinc-900 text-xs font-mono text-zinc-300 hover:text-white transition flex items-center space-x-1.5">
                <span>@${u}</span>
                <i class="fa-solid fa-magnifying-glass text-[9px] text-indigo-400"></i>
              </button>
            `).join('')}
          </div>
        </div>

      </div>

    </div>
  `;

  container.innerHTML = html;
}

// Investigar variação de username diretamente
function investigateVariant(username) {
  switchTab('username');
  document.getElementById('username-input').value = username;
  startUsernameSearch();
}

// ==========================================
// 2. PESQUISA DE USERNAME (OSINT)
// ==========================================

function checkUsernameInput(val) {
  const warning = document.getElementById('username-name-warning');
  if (warning) {
    if (val.trim().includes(' ')) {
      warning.classList.remove('hidden');
    } else {
      warning.classList.add('hidden');
    }
  }
}

function switchToPeopleSearchFromUsername() {
  const raw = document.getElementById('username-input').value.trim();
  switchTab('people');
  document.getElementById('person-name-input').value = raw;
  document.getElementById('person-name-input').focus();
}

function startUsernameSearch(event) {
  if (event) event.preventDefault();
  let username = document.getElementById('username-input').value.trim();
  const engine = document.getElementById('engine-select').value;
  if (!username) return;

  // Se o utilizador escreveu com espaços, limpa internamente para o motor não bloquear
  username = username.lstrip ? username.lstrip('@') : username.replace(/^@+/, '');
  if (username.includes(' ')) {
    username = username.replace(/\s+/g, '').toLowerCase();
  }

  // Reset de estado
  if (eventSource) {
    eventSource.close();
  }
  foundProfiles = [];
  const grid = document.getElementById('username-results-grid');
  grid.innerHTML = '';
  document.getElementById('found-count').textContent = '0';
  document.getElementById('username-empty-state').classList.add('hidden');
  document.getElementById('username-progress').classList.remove('hidden');
  document.getElementById('results-bar').classList.remove('hidden');
  document.getElementById('progress-bar').style.width = '10%';
  document.getElementById('progress-status-text').textContent = 'A conectar ao motor de varredura...';

  const btn = document.getElementById('btn-search-username');
  btn.disabled = true;
  btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i><span>A procurar...</span>`;

  // Conecta ao endpoint de SSE do FastAPI
  const url = `${API_BASE}/api/username/stream/${encodeURIComponent(username)}?engine=${engine}`;
  eventSource = new EventSource(url);

  eventSource.onmessage = function (e) {
    try {
      const data = JSON.parse(e.data);

      if (data.type === 'stage') {
        document.getElementById('progress-status-text').textContent = data.message;
        document.getElementById('progress-bar').style.width = '35%';
      } else if (data.type === 'progress') {
        document.getElementById('progress-status-text').textContent = data.message;
        document.getElementById('progress-bar').style.width = '60%';
      } else if (data.type === 'found') {
        addProfileCard(data);
      } else if (data.type === 'completed') {
        document.getElementById('progress-status-text').textContent = 'Varredura concluída!';
        document.getElementById('progress-bar').style.width = '100%';
        finishSearch();
      }
    } catch (err) {
      console.error("Erro ao analisar mensagem SSE", err);
    }
  };

  eventSource.onerror = function (err) {
    console.warn("Stream terminado ou fechado:", err);
    finishSearch();
  };
}

function finishSearch() {
  if (eventSource) {
    eventSource.close();
    eventSource = null;
  }
  const btn = document.getElementById('btn-search-username');
  btn.disabled = false;
  btn.innerHTML = `<i class="fa-solid fa-magnifying-glass"></i><span>Investigar</span>`;
}

function addProfileCard(item) {
  // Evita duplicados
  if (foundProfiles.some(p => p.url === item.url)) return;
  foundProfiles.push(item);

  document.getElementById('found-count').textContent = foundProfiles.length;
  const grid = document.getElementById('username-results-grid');

  const card = document.createElement('div');
  card.className = "profile-card bg-zinc-900/70 border border-zinc-800 hover:border-indigo-500/50 rounded-xl p-4 transition-all duration-200 flex flex-col justify-between space-y-3 group shadow-md hover:shadow-indigo-500/10";
  card.dataset.site = (item.site || '').toLowerCase();

  const iconClass = getPlatformIcon(item.site);
  const engineLabel = item.engine || 'OSINT';

  card.innerHTML = `
    <div class="flex items-start justify-between">
      <div class="flex items-center space-x-3">
        <div class="w-9 h-9 rounded-lg bg-zinc-800 group-hover:bg-indigo-600/20 text-zinc-300 group-hover:text-indigo-400 flex items-center justify-center transition">
          <i class="${iconClass} text-base"></i>
        </div>
        <div>
          <h4 class="font-semibold text-sm text-white">${item.site}</h4>
          <span class="text-[10px] uppercase font-bold text-zinc-500">${item.category || engineLabel}</span>
        </div>
      </div>
      <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
    </div>

    <div class="pt-1">
      <a href="${item.url}" target="_blank" rel="noopener noreferrer" 
         class="text-xs text-indigo-400 hover:text-indigo-300 truncate block hover:underline font-mono">
        ${item.url}
      </a>
    </div>

    <div class="flex items-center justify-between pt-2 border-t border-zinc-800/80 text-[11px] text-zinc-400">
      <span class="bg-zinc-800 px-2 py-0.5 rounded text-[10px] text-zinc-400">${engineLabel}</span>
      <a href="${item.url}" target="_blank" rel="noopener noreferrer" class="hover:text-white flex items-center space-x-1">
        <span>Abrir</span>
        <i class="fa-solid fa-arrow-up-right-from-square text-[9px]"></i>
      </a>
    </div>
  `;

  grid.appendChild(card);
}

// Filtro de resultados
function filterResults() {
  const query = document.getElementById('filter-input').value.toLowerCase().trim();
  document.querySelectorAll('.profile-card').forEach(card => {
    const site = card.dataset.site;
    if (site.includes(query)) {
      card.classList.remove('hidden');
    } else {
      card.classList.add('hidden');
    }
  });
}

// Exportações
function exportJSON() {
  if (!foundProfiles.length) return alert('Nenhum resultado para exportar.');
  const blob = new Blob([JSON.stringify(foundProfiles, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `osint_profiles_${Date.now()}.json`;
  a.click();
}

function exportCSV() {
  if (!foundProfiles.length) return alert('Nenhum resultado para exportar.');
  let csv = "Plataforma,URL,Motor,Categoria\n";
  foundProfiles.forEach(p => {
    csv += `"${p.site}","${p.url}","${p.engine || ''}","${p.category || ''}"\n`;
  });
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `osint_profiles_${Date.now()}.csv`;
  a.click();
}

// ==========================================
// 3. BUSCA WEB (SEARXNG)
// ==========================================

async function startWebSearch(event) {
  event.preventDefault();
  const q = document.getElementById('web-query-input').value.trim();
  const cat = document.getElementById('web-category-select').value;
  if (!q) return;

  const container = document.getElementById('web-results-container');
  const btn = document.getElementById('btn-search-web');
  btn.disabled = true;
  btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i><span>A pesquisar...</span>`;
  container.innerHTML = `<div class="text-zinc-500 text-sm py-4">A consultar motores de busca...</div>`;

  try {
    const res = await fetch(`${API_BASE}/api/search/web?q=${encodeURIComponent(q)}&categories=${cat}`);
    const data = await res.json();

    if (!data.results || data.results.length === 0) {
      container.innerHTML = `<div class="text-zinc-500 text-sm py-4">Nenhum resultado encontrado.</div>`;
      return;
    }

    let html = `
      <div class="text-xs text-zinc-400 mb-2">
        Encontrados <span class="text-white font-bold">${data.total}</span> resultados usando o motor <span class="text-indigo-400 font-mono">${data.engine_used}</span>
      </div>
    `;

    data.results.forEach(r => {
      html += `
        <div class="bg-zinc-900/60 border border-zinc-800 hover:border-zinc-700 rounded-xl p-4 transition space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-[11px] font-mono text-indigo-400 truncate max-w-md">${r.url}</span>
            <span class="text-[10px] bg-zinc-800 text-zinc-400 px-2 py-0.5 rounded">${r.engine || 'Web'}</span>
          </div>
          <h4 class="font-semibold text-sm text-white">
            <a href="${r.url}" target="_blank" rel="noopener noreferrer" class="hover:text-indigo-400 hover:underline">
              ${r.title}
            </a>
          </h4>
          <p class="text-xs text-zinc-400 line-clamp-2">${r.content || ''}</p>
        </div>
      `;
    });

    container.innerHTML = html;
  } catch (err) {
    container.innerHTML = `<div class="text-red-400 text-sm py-4">Erro ao realizar pesquisa: ${err.message}</div>`;
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i class="fa-solid fa-magnifying-glass"></i><span>Pesquisar</span>`;
  }
}

// ==========================================
// 4. SCRAPER DE CONTACTOS
// ==========================================

async function startScrape(event) {
  event.preventDefault();
  const url = document.getElementById('scrape-url-input').value.trim();
  if (!url) return;

  const btn = document.getElementById('btn-scrape');
  const container = document.getElementById('scraper-results-container');
  btn.disabled = true;
  btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i><span>A extrair...</span>`;
  container.classList.remove('hidden');
  container.innerHTML = `<div class="text-zinc-500 text-sm py-4">A analisar o website e a extrair contactos...</div>`;

  try {
    const res = await fetch(`${API_BASE}/api/scraper/extract?url=${encodeURIComponent(url)}`);
    if (!res.ok) {
      const errData = await res.json();
      throw new Error(errData.detail || 'Erro na requisição');
    }
    const data = await res.json();

    let html = `
      <div class="bg-zinc-900/80 border border-zinc-800 rounded-2xl p-6 space-y-6">
        <div>
          <h3 class="text-base font-bold text-white">${data.title || 'Página Web'}</h3>
          <p class="text-xs text-zinc-400 mt-1">${data.description || 'Sem descrição'}</p>
          <a href="${data.target_url}" target="_blank" class="text-xs text-indigo-400 font-mono hover:underline mt-1 inline-block">${data.target_url}</a>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <!-- Emails -->
          <div class="bg-zinc-950 p-4 rounded-xl border border-zinc-800">
            <h4 class="text-xs uppercase font-semibold text-zinc-400 mb-3 flex items-center justify-between">
              <span><i class="fa-regular fa-envelope text-indigo-400 mr-2"></i>Emails Detetados</span>
              <span class="text-emerald-400 font-bold">${data.emails.length}</span>
            </h4>
            <div class="space-y-1.5 max-h-48 overflow-y-auto">
              ${data.emails.length ? data.emails.map(e => `
                <div class="flex items-center justify-between bg-zinc-900 px-3 py-1.5 rounded text-xs">
                  <span class="font-mono text-zinc-200 select-all">${e}</span>
                  <button onclick="copyToClipboard('${e}', this)" class="text-zinc-500 hover:text-white" title="Copiar"><i class="fa-regular fa-copy"></i></button>
                </div>
              `).join('') : '<p class="text-xs text-zinc-600">Nenhum email detetado.</p>'}
            </div>
          </div>

          <!-- Telefones -->
          <div class="bg-zinc-950 p-4 rounded-xl border border-zinc-800">
            <h4 class="text-xs uppercase font-semibold text-zinc-400 mb-3 flex items-center justify-between">
              <span><i class="fa-solid fa-phone text-emerald-400 mr-2"></i>Telefones Detetados</span>
              <span class="text-emerald-400 font-bold">${data.phones.length}</span>
            </h4>
            <div class="space-y-1.5 max-h-48 overflow-y-auto">
              ${data.phones.length ? data.phones.map(p => `
                <div class="flex items-center justify-between bg-zinc-900 px-3 py-1.5 rounded text-xs">
                  <span class="font-mono text-zinc-200 select-all">${p}</span>
                  <button onclick="copyToClipboard('${p}', this)" class="text-zinc-500 hover:text-white" title="Copiar"><i class="fa-regular fa-copy"></i></button>
                </div>
              `).join('') : '<p class="text-xs text-zinc-600">Nenhum telefone detetado.</p>'}
            </div>
          </div>
        </div>

        <!-- Redes sociais detetadas -->
        <div>
          <h4 class="text-xs uppercase font-semibold text-zinc-400 mb-3">Redes Sociais Encontradas na Página</h4>
          <div class="flex flex-wrap gap-2">
            ${data.social_profiles.length ? data.social_profiles.map(s => `
              <a href="${s.url}" target="_blank" class="px-3 py-1.5 bg-zinc-950 border border-zinc-800 hover:border-indigo-500 rounded-lg text-xs text-zinc-300 flex items-center space-x-2 transition">
                <i class="${getPlatformIcon(s.platform)} text-indigo-400"></i>
                <span class="font-medium">${s.platform}</span>
              </a>
            `).join('') : '<p class="text-xs text-zinc-600">Nenhum perfil social vinculado encontrado.</p>'}
          </div>
        </div>

      </div>
    `;

    container.innerHTML = html;
  } catch (err) {
    container.innerHTML = `<div class="text-red-400 text-sm py-4">Erro ao extrair dados: ${err.message}</div>`;
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i class="fa-solid fa-spider"></i><span>Extrair Dados</span>`;
  }
}
