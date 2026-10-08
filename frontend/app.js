// URL Base Dinâmica da API (Suporta FastAPI na porta 8000, Centauro na porta 80, e Render)
function getApiBase() {
  if (window.location.port === '8000') {
    return '';
  }
  // Se estiver a correr pelo Centauro em localhost ou IP local
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    return 'http://localhost:8000';
  }
  if (window.location.hostname.startsWith('192.168.') || window.location.hostname.startsWith('10.')) {
    return `http://${window.location.hostname}:8000`;
  }
  // Se for no domínio público do Centauro
  if (window.location.hostname.includes('sigec-pro.com')) {
    return `https://${window.location.hostname}:8000`;
  }
  return '';
}

const API_BASE = getApiBase();

// Estado global
let foundProfiles = [];
let eventSource = null;

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
  const name = siteName.toLowerCase();
  if (name.includes('github') || name.includes('gitlab')) return 'fa-brands fa-github';
  if (name.includes('twitter') || name.includes('x')) return 'fa-brands fa-x-twitter';
  if (name.includes('reddit')) return 'fa-brands fa-reddit-alien';
  if (name.includes('telegram')) return 'fa-brands fa-telegram';
  if (name.includes('steam')) return 'fa-brands fa-steam';
  if (name.includes('youtube')) return 'fa-brands fa-youtube';
  if (name.includes('twitch')) return 'fa-brands fa-twitch';
  if (name.includes('pinterest')) return 'fa-brands fa-pinterest';
  if (name.includes('spotify') || name.includes('soundcloud')) return 'fa-brands fa-spotify';
  if (name.includes('medium')) return 'fa-brands fa-medium';
  if (name.includes('instagram')) return 'fa-brands fa-instagram';
  if (name.includes('tiktok')) return 'fa-brands fa-tiktok';
  return 'fa-solid fa-link';
}

// Inicia Pesquisa de Username (SSE Streaming)
function startUsernameSearch(event) {
  if (event) event.preventDefault();
  const username = document.getElementById('username-input').value.trim();
  const engine = document.getElementById('engine-select').value;
  if (!username) return;

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
  card.dataset.site = item.site.toLowerCase();

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

// Busca Web (SearXNG)
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

// Scraper de contactos
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
                  <button onclick="navigator.clipboard.writeText('${e}')" class="text-zinc-500 hover:text-white" title="Copiar"><i class="fa-regular fa-copy"></i></button>
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
                  <button onclick="navigator.clipboard.writeText('${p}')" class="text-zinc-500 hover:text-white" title="Copiar"><i class="fa-regular fa-copy"></i></button>
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
