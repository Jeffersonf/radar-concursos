/**
 * Radar de Concursos Públicos - Controlador Ultraleve
 * Inspirado em Linear / shadcn/ui. 0 dependências externas.
 */

let debounceTimer = null;
let currentConcursos = [];
let currentCareerFilter = "TODOS";
let activeModalConcurso = null;

// Estados de Geolocalização e Distância
let userCoordinates = null; // { lat, lon, name }
let maxDistanceKm = 0;
let suggestedCities = [];

// Estados do Comparador e Visualização
let selectedForCompare = new Set();
let currentViewMode = "cards"; // "cards" ou "table"

// Suporte Híbrido Estático (GitHub Pages e Local)
let allStaticConcursos = null;

function isStaticEnvironment() {
  return window.location.protocol === "file:" ||
         window.location.hostname.includes("github.io") ||
         window.location.hostname.includes("pages.dev") ||
         (window.location.port === "" && !window.location.hostname.includes("localhost"));
}

function calculateHaversineDistance(lat1, lon1, lat2, lon2) {
  if (lat1 === null || lon1 === null || lat2 === null || lon2 === null) return null;
  const R = 6371; // Raio da Terra em km
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
            Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return Math.round(R * c);
}

function getStoredFavorites() {
  try {
    return JSON.parse(localStorage.getItem("monitor_favorites") || "[]");
  } catch (_) {
    return [];
  }
}

function saveStoredFavorites(favs) {
  try {
    localStorage.setItem("monitor_favorites", JSON.stringify(favs));
  } catch (_) {}
}

async function fetchDatasetStatic() {
  if (allStaticConcursos) return allStaticConcursos;
  const paths = ["./concursos.json", "./data/concursos.json", "concursos.json"];
  for (const p of paths) {
    try {
      const res = await fetch(p);
      if (res.ok) {
        const data = await res.json();
        const list = data.concursos || data || [];
        const favs = new Set(getStoredFavorites());
        list.forEach(c => {
          c.is_favorite = favs.has(c.external_id);
          const savedNote = localStorage.getItem("monitor_notes_" + c.external_id);
          if (savedNote) c.user_notes = savedNote;
        });
        allStaticConcursos = list;
        return allStaticConcursos;
      }
    } catch (_) {}
  }
  return [];
}

// Ícones SVG Inline Reutilizáveis (Lucide Style)
const ICONS = {
  pin: `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/></svg>`,
  cash: `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect width="20" height="14" x="2" y="5" rx="2"/><line x1="2" x2="22" y1="10" y2="10"/></svg>`,
  users: `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>`,
  calendar: `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect width="18" height="18" x="3" y="4" rx="2"/><line x1="16" x2="16" y1="2" y2="6"/><line x1="8" x2="8" y1="2" y2="6"/><line x1="3" x2="21" y1="10" y2="10"/></svg>`,
  briefcase: `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect width="20" height="14" x="2" y="7" rx="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>`,
  star: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>`,
  starFilled: `<svg width="14" height="14" viewBox="0 0 24 24" fill="#f59e0b" stroke="#f59e0b" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>`,
  arrowUpRight: `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="7" y1="17" x2="17" y2="7"/><polyline points="7 7 17 7 17 17"/></svg>`
};

document.addEventListener("DOMContentLoaded", () => {
  setupTheme();
  setupTabs();
  setupCareerPills();
  setupGeoRadar();
  setupComparisonTray();
  setupModals();
  setupEventListeners();
  loadStats();
  loadCities();
  loadConcursos();
  loadConfig();
});

/* -------------------------------------------------------------
 * 1. GERENCIAMENTO DE TEMA (CLARO / ESCURO)
 * ------------------------------------------------------------- */
function setupTheme() {
  const toggleBtn = document.getElementById("btn-theme-toggle");
  const sunIcon = document.getElementById("theme-icon-sun");
  const moonIcon = document.getElementById("theme-icon-moon");

  const savedTheme = localStorage.getItem("app-theme") || "dark";
  applyTheme(savedTheme);

  if (toggleBtn) {
    toggleBtn.addEventListener("click", () => {
      const current = document.body.getAttribute("data-theme") || "dark";
      const next = current === "dark" ? "light" : "dark";
      applyTheme(next);
      localStorage.setItem("app-theme", next);
    });
  }

  function applyTheme(theme) {
    document.body.setAttribute("data-theme", theme);
    if (theme === "dark") {
      if (sunIcon) sunIcon.style.display = "block";
      if (moonIcon) moonIcon.style.display = "none";
    } else {
      if (sunIcon) sunIcon.style.display = "none";
      if (moonIcon) moonIcon.style.display = "block";
    }
  }
}

/* -------------------------------------------------------------
 * 2. NAVEGAÇÃO DE ABAS
 * ------------------------------------------------------------- */
function switchTab(targetId) {
  // Update desktop tabs
  const tabs = document.querySelectorAll(".nav-tab");
  tabs.forEach(t => {
    if (t.getAttribute("data-tab") === targetId) {
      t.classList.add("active");
    } else {
      t.classList.remove("active");
    }
  });

  // Update mobile tabs
  const mobTabs = document.querySelectorAll(".mobile-tab-btn");
  mobTabs.forEach(btn => {
    if (btn.getAttribute("data-tab") === targetId) {
      btn.classList.add("active");
    } else {
      btn.classList.remove("active");
    }
  });

  // Show corresponding tab pane
  document.querySelectorAll(".tab-content-pane").forEach(pane => {
    pane.style.display = "none";
  });

  const activePane = document.getElementById(targetId);
  if (activePane) {
    activePane.style.display = "block";
  }

  if (targetId === "tab-analytics") {
    loadAnalytics();
  } else if (targetId === "tab-favoritos") {
    loadFavoritos();
  }
}

function setupTabs() {
  const tabs = document.querySelectorAll(".nav-tab");
  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      const targetId = tab.getAttribute("data-tab");
      if (targetId) switchTab(targetId);
    });
  });

  const mobTabs = document.querySelectorAll(".mobile-tab-btn[data-tab]");
  mobTabs.forEach(btn => {
    btn.addEventListener("click", () => {
      const targetId = btn.getAttribute("data-tab");
      if (targetId) switchTab(targetId);
    });
  });

  // Mobile Radar shortcut
  const mobRadarBtn = document.getElementById("mobile-btn-radar");
  if (mobRadarBtn) {
    mobRadarBtn.addEventListener("click", () => {
      switchTab("tab-editais");
      const radarBar = document.querySelector(".radar-bar");
      if (radarBar) {
        radarBar.scrollIntoView({ behavior: "smooth", block: "center" });
      }
      const cityInput = document.getElementById("geo-city-input");
      if (cityInput) {
        setTimeout(() => cityInput.focus(), 350);
      }
    });
  }
}

/* -------------------------------------------------------------
 * 3. RADAR DE PROXIMIDADE E DISTÂNCIA (KM)
 * ------------------------------------------------------------- */
function setupGeoRadar() {
  const cityInput = document.getElementById("geo-city-input");
  const autocomplete = document.getElementById("geo-autocomplete");
  const btnGps = document.getElementById("btn-use-gps");
  const btnClearLoc = document.getElementById("btn-clear-location");
  const radiusSelector = document.getElementById("radius-selector");

  if (cityInput && autocomplete) {
    cityInput.addEventListener("input", () => {
      const q = cityInput.value.trim().toLowerCase();
      if (q.length < 2) {
        autocomplete.style.display = "none";
        return;
      }

      const matches = suggestedCities.filter(c => 
        c.name.toLowerCase().includes(q) || (c.query && c.query.includes(q))
      ).slice(0, 8);

      if (matches.length === 0) {
        autocomplete.style.display = "none";
        return;
      }

      autocomplete.innerHTML = matches.map(m => `
        <div class="autocomplete-item" data-name="${escapeHtml(m.name)}" data-lat="${m.lat}" data-lon="${m.lon}">
          📍 ${escapeHtml(m.name)}
        </div>
      `).join("");
      autocomplete.style.display = "block";
    });

    autocomplete.addEventListener("click", (e) => {
      const item = e.target.closest(".autocomplete-item");
      if (!item) return;

      const name = item.getAttribute("data-name");
      const lat = parseFloat(item.getAttribute("data-lat"));
      const lon = parseFloat(item.getAttribute("data-lon"));

      setUserLocation(name, lat, lon);
      cityInput.value = "";
      autocomplete.style.display = "none";
    });

    cityInput.addEventListener("keydown", async (e) => {
      if (e.key === "Enter") {
        const q = cityInput.value.trim();
        if (!q) return;
        autocomplete.style.display = "none";

        let found = false;
        if (!isStaticEnvironment()) {
          try {
            const res = await fetch(`/api/resolve-location?city=${encodeURIComponent(q)}`);
            if (res.ok) {
              const data = await res.json();
              if (data.found) {
                setUserLocation(data.name, data.lat, data.lon);
                cityInput.value = "";
                found = true;
              }
            }
          } catch (_) {}
        }

        if (!found) {
          const lowerQ = q.toLowerCase();
          const match = suggestedCities.find(c => 
            c.name.toLowerCase().includes(lowerQ) || (c.query && c.query.includes(lowerQ))
          );
          if (match) {
            setUserLocation(match.name, match.lat, match.lon);
            cityInput.value = "";
          } else {
            showToast("Localidade não encontrada. Digite e selecione da lista de sugestões.");
          }
        }
      }
    });

    document.addEventListener("click", (e) => {
      if (!cityInput.contains(e.target) && !autocomplete.contains(e.target)) {
        autocomplete.style.display = "none";
      }
    });
  }

  // GPS do Navegador
  if (btnGps) {
    btnGps.addEventListener("click", () => {
      if (!navigator.geolocation) {
        showToast("Geolocalização não disponível no navegador.");
        return;
      }

      const originalHtml = btnGps.innerHTML;
      btnGps.innerHTML = '<span class="spinner"></span> Localizando...';
      btnGps.disabled = true;

      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const lat = pos.coords.latitude;
          const lon = pos.coords.longitude;
          setUserLocation("Meu GPS", lat, lon);
          btnGps.innerHTML = originalHtml;
          btnGps.disabled = false;
        },
        () => {
          btnGps.innerHTML = originalHtml;
          btnGps.disabled = false;
          showToast("Permissão de localização negada ou indisponível.");
        },
        { timeout: 8000 }
      );
    });
  }

  // Limpar localização
  if (btnClearLoc) {
    btnClearLoc.addEventListener("click", () => {
      userCoordinates = null;
      document.getElementById("user-location-badge").style.display = "none";
      loadConcursos();
    });
  }

  // Seletor de Raio
  if (radiusSelector) {
    radiusSelector.addEventListener("click", (e) => {
      const chip = e.target.closest(".radius-chip");
      if (!chip) return;

      radiusSelector.querySelectorAll(".radius-chip").forEach(c => c.classList.remove("active"));
      chip.classList.add("active");

      maxDistanceKm = parseFloat(chip.getAttribute("data-radius") || "0");
      loadConcursos();
    });
  }
}

function setUserLocation(name, lat, lon) {
  userCoordinates = { name, lat, lon };
  const badge = document.getElementById("user-location-badge");
  document.getElementById("user-location-text").innerText = name;
  badge.style.display = "inline-flex";

  const sortSelect = document.getElementById("filter-sort");
  if (sortSelect && (sortSelect.value === "default" || !sortSelect.value)) {
    sortSelect.value = "distance_asc";
  }

  showToast(`Localização: ${name} 📍`);
  loadConcursos();
}

async function loadCities() {
  if (!isStaticEnvironment()) {
    try {
      const res = await fetch("/api/cities");
      if (res.ok) {
        const data = await res.json();
        suggestedCities = data.cities || [];
        return;
      }
    } catch (_) {}
  }
  const fallbackPaths = ["./cities.json", "./data/cities.json", "cities.json"];
  for (const p of fallbackPaths) {
    try {
      const res = await fetch(p);
      if (res.ok) {
        const data = await res.json();
        suggestedCities = data.cities || [];
        return;
      }
    } catch (_) {}
  }
}

/* -------------------------------------------------------------
 * 4. FILTROS RÁPIDOS POR CARREIRA
 * ------------------------------------------------------------- */
function setupCareerPills() {
  const container = document.getElementById("career-pills-container");
  if (!container) return;

  container.addEventListener("click", (e) => {
    const chip = e.target.closest(".career-chip");
    if (!chip) return;

    container.querySelectorAll(".career-chip").forEach(c => c.classList.remove("active"));
    chip.classList.add("active");

    currentCareerFilter = chip.getAttribute("data-area") || "TODOS";
    loadConcursos();
  });
}

/* -------------------------------------------------------------
 * 5. MODAIS & FECHAMENTO
 * ------------------------------------------------------------- */
function setupModals() {
  const detailsModal = document.getElementById("modal-details");
  const compareModal = document.getElementById("modal-compare");
  const detailsClose = document.getElementById("modal-close");
  const compareClose = document.getElementById("modal-compare-close");

  if (detailsClose) detailsClose.addEventListener("click", () => detailsModal.style.display = "none");
  if (compareClose) compareClose.addEventListener("click", () => compareModal.style.display = "none");

  [detailsModal, compareModal].forEach(m => {
    if (m) {
      m.addEventListener("click", (e) => {
        if (e.target === m) m.style.display = "none";
      });
    }
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      if (detailsModal) detailsModal.style.display = "none";
      if (compareModal) compareModal.style.display = "none";
    }
    // Atalho "/" para focar busca rápida (estilo Linear)
    if (e.key === "/" && document.activeElement.tagName !== "INPUT" && document.activeElement.tagName !== "TEXTAREA") {
      e.preventDefault();
      const searchInput = document.getElementById("filter-search");
      if (searchInput) searchInput.focus();
    }
  });
}

/* -------------------------------------------------------------
 * 6. COMPARADOR DE EDITAIS
 * ------------------------------------------------------------- */
function setupComparisonTray() {
  const btnOpenCompare = document.getElementById("btn-open-compare");
  const btnClearCompare = document.getElementById("btn-clear-compare");

  if (btnOpenCompare) btnOpenCompare.addEventListener("click", openCompareModal);
  if (btnClearCompare) btnClearCompare.addEventListener("click", clearComparison);
}

function toggleCompare(externalId, isChecked) {
  if (isChecked) {
    if (selectedForCompare.size >= 3) {
      showToast("Você pode comparar até 3 editais simultaneamente.");
      return false;
    }
    selectedForCompare.add(externalId);
  } else {
    selectedForCompare.delete(externalId);
  }

  updateCompareTray();
  return true;
}

function updateCompareTray() {
  const tray = document.getElementById("compare-tray");
  const countEl = document.getElementById("compare-count");
  if (!tray || !countEl) return;

  const count = selectedForCompare.size;
  countEl.innerText = count;
  tray.style.display = count > 0 ? "flex" : "none";
}

function clearComparison() {
  selectedForCompare.clear();
  updateCompareTray();
  document.querySelectorAll(".compare-checkbox").forEach(cb => cb.checked = false);
}

function openCompareModal() {
  if (selectedForCompare.size === 0) return;

  const items = currentConcursos.filter(c => selectedForCompare.has(c.external_id));
  const table = document.getElementById("compare-table");

  let html = `
    <thead>
      <tr>
        <th style="min-width: 140px;">Critério</th>
        ${items.map(it => `<th><strong>${escapeHtml(it.title)}</strong></th>`).join("")}
      </tr>
    </thead>
    <tbody>
      <tr>
        <td style="color: var(--text-muted);">Município / UF</td>
        ${items.map(it => `<td><span class="badge-uf">${it.uf}</span> ${escapeHtml(it.cidade || it.uf)} ${it.distance_km !== null && it.distance_km !== undefined ? `(~${it.distance_km} km)` : ''}</td>`).join("")}
      </tr>
      <tr>
        <td style="color: var(--text-muted);">Salário</td>
        ${items.map(it => `<td style="color: var(--accent-emerald); font-weight: 600;">${it.salary ? 'R$ ' + it.salary.toLocaleString("pt-BR", { minimumFractionDigits: 2 }) : 'N/I'}</td>`).join("")}
      </tr>
      <tr>
        <td style="color: var(--text-muted);">Vagas</td>
        ${items.map(it => `<td>${escapeHtml(it.vacancies_text || 'N/I')}</td>`).join("")}
      </tr>
      <tr>
        <td style="color: var(--text-muted);">Escolaridade</td>
        ${items.map(it => `<td>${(it.education || []).join(' / ') || 'Geral'}</td>`).join("")}
      </tr>
      <tr>
        <td style="color: var(--text-muted);">Banca</td>
        ${items.map(it => `<td>${escapeHtml(it.banca || 'Órgão Próprio')}</td>`).join("")}
      </tr>
      <tr>
        <td style="color: var(--text-muted);">Prazo</td>
        ${items.map(it => `<td>${escapeHtml(it.deadline_text || 'Aberto')} ${it.days_remaining !== null ? `(${it.days_remaining}d)` : ''}</td>`).join("")}
      </tr>
      <tr>
        <td style="color: var(--text-muted);">Link</td>
        ${items.map(it => `<td><a href="${it.url}" target="_blank" rel="noopener" class="btn btn-sm btn-primary">Abrir Edital ↗</a></td>`).join("")}
      </tr>
    </tbody>
  `;

  table.innerHTML = html;
  document.getElementById("modal-compare").style.display = "flex";
}

/* -------------------------------------------------------------
 * 7. EVENTOS E INTERAÇÃO
 * ------------------------------------------------------------- */
function setupEventListeners() {
  const searchInput = document.getElementById("filter-search");
  const clearSearchBtn = document.getElementById("btn-clear-search");
  const ufSelect = document.getElementById("filter-uf");
  const salarySelect = document.getElementById("filter-salary");
  const educationSelect = document.getElementById("filter-education");
  const tipoSelect = document.getElementById("filter-tipo");
  const sortSelect = document.getElementById("filter-sort");

  const btnScan = document.getElementById("btn-scan");
  const btnExportCsv = document.getElementById("btn-export-csv");

  // Alternador de Visualização Cards / Tabela
  const btnViewCards = document.getElementById("btn-view-cards");
  const btnViewTable = document.getElementById("btn-view-table");

  if (btnViewCards && btnViewTable) {
    btnViewCards.addEventListener("click", () => {
      currentViewMode = "cards";
      btnViewCards.classList.add("active");
      btnViewTable.classList.remove("active");
      renderCurrentConcursos();
    });

    btnViewTable.addEventListener("click", () => {
      currentViewMode = "table";
      btnViewTable.classList.add("active");
      btnViewCards.classList.remove("active");
      renderCurrentConcursos();
    });
  }

  // Busca rápida (Debounce ágil de 150ms)
  if (searchInput) {
    searchInput.addEventListener("input", () => {
      if (clearSearchBtn) clearSearchBtn.style.display = searchInput.value ? "block" : "none";
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(loadConcursos, 150);
    });
  }

  if (clearSearchBtn) {
    clearSearchBtn.addEventListener("click", () => {
      searchInput.value = "";
      clearSearchBtn.style.display = "none";
      loadConcursos();
    });
  }

  [ufSelect, salarySelect, educationSelect, tipoSelect, sortSelect].forEach(el => {
    if (el) el.addEventListener("change", loadConcursos);
  });

  if (btnScan) btnScan.addEventListener("click", runScan);
  if (btnExportCsv) btnExportCsv.addEventListener("click", exportCsv);

  // Modal Actions
  const modalFavBtn = document.getElementById("modal-fav-btn");
  const btnSaveNotes = document.getElementById("btn-save-notes");

  if (modalFavBtn) {
    modalFavBtn.addEventListener("click", () => {
      if (activeModalConcurso) {
        toggleFavorite(activeModalConcurso.external_id);
      }
    });
  }

  if (btnSaveNotes) btnSaveNotes.addEventListener("click", saveModalNotes);

  // Configurações e Notificações
  const btnSaveSettings = document.getElementById("btn-save-settings");
  const btnTestTelegram = document.getElementById("btn-test-telegram");
  const btnTestDiscord = document.getElementById("btn-test-discord");

  if (btnSaveSettings) btnSaveSettings.addEventListener("click", saveSettings);
  if (btnTestTelegram) btnTestTelegram.addEventListener("click", testTelegram);
  if (btnTestDiscord) btnTestDiscord.addEventListener("click", testDiscord);
}

/* -------------------------------------------------------------
 * 8. BUSCA E CARREGAMENTO DE CONCURSOS
 * ------------------------------------------------------------- */
function getActiveFilterParams(includeSort = true) {
  const search = document.getElementById("filter-search").value.trim();
  const uf = document.getElementById("filter-uf").value;
  const minSalary = document.getElementById("filter-salary").value;
  const education = document.getElementById("filter-education").value;
  const tipo = document.getElementById("filter-tipo").value;
  const sort = document.getElementById("filter-sort") ? document.getElementById("filter-sort").value : "default";

  const params = new URLSearchParams();
  if (search) params.set("search", search);
  if (uf && uf !== "TODOS") params.set("uf", uf);
  if (parseFloat(minSalary) > 0) params.set("min_salary", minSalary);
  if (education && education !== "TODOS") params.set("education", education);
  if (tipo && tipo !== "TODOS") params.set("tipo", tipo);
  if (currentCareerFilter && currentCareerFilter !== "TODOS") params.set("area", currentCareerFilter);
  if (includeSort && sort) params.set("sort_by", sort);
  params.set("only_active", "true");

  if (userCoordinates) {
    params.set("user_lat", userCoordinates.lat);
    params.set("user_lon", userCoordinates.lon);
    if (maxDistanceKm > 0) {
      params.set("max_distance", maxDistanceKm);
    }
  }

  return params;
}

function filterAndSortClientSide(dataset) {
  const searchInput = document.getElementById("filter-search");
  const q = searchInput ? searchInput.value.trim().toLowerCase() : "";
  const uf = document.getElementById("filter-uf")?.value || "TODOS";
  const minSal = parseFloat(document.getElementById("filter-salary")?.value || "0") || 0;
  const edu = document.getElementById("filter-education")?.value || "TODOS";
  const tipo = document.getElementById("filter-tipo")?.value || "TODOS";
  const sort = document.getElementById("filter-sort")?.value || "default";

  const favSet = new Set(getStoredFavorites());

  let filtered = dataset.filter(item => {
    item.is_favorite = favSet.has(item.external_id);

    // Distância por raio se houver localização
    if (userCoordinates && item.lat && item.lon) {
      item.distance_km = calculateHaversineDistance(userCoordinates.lat, userCoordinates.lon, item.lat, item.lon);
    } else {
      item.distance_km = null;
    }

    if (maxDistanceKm > 0) {
      if (item.distance_km === null || item.distance_km > maxDistanceKm) return false;
    }
    if (uf !== "TODOS" && item.uf !== uf) return false;
    if (minSal > 0 && (item.salary || 0) < minSal) return false;
    if (edu !== "TODOS" && (!item.education || !item.education.includes(edu))) return false;
    if (tipo !== "TODOS" && item.tipo !== tipo) return false;
    if (currentCareerFilter !== "TODOS") {
      const area = (item.area || "").toLowerCase();
      if (!area.includes(currentCareerFilter.toLowerCase())) return false;
    }
    if (q) {
      const hay = `${item.title} ${item.details} ${item.banca || ''} ${item.cidade || ''}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });

  // Ordenação
  if (sort === "distance_asc") {
    filtered.sort((a, b) => (a.distance_km ?? 99999) - (b.distance_km ?? 99999));
  } else if (sort === "salary_desc") {
    filtered.sort((a, b) => (b.salary || 0) - (a.salary || 0));
  } else if (sort === "deadline_asc") {
    filtered.sort((a, b) => (a.days_remaining ?? 999) - (b.days_remaining ?? 999));
  } else if (sort === "vacancies_desc") {
    filtered.sort((a, b) => (b.vacancies || 0) - (a.vacancies || 0));
  }

  return filtered;
}

async function loadConcursos() {
  const countEl = document.getElementById("results-count");
  if (countEl) countEl.innerText = "Filtrando editais...";

  const isStatic = isStaticEnvironment();
  let fetchedFromServer = false;

  if (!isStatic) {
    try {
      const params = getActiveFilterParams(true);
      params.set("limit", "300");
      const res = await fetch(`/api/concursos?${params.toString()}`);
      if (res.ok) {
        const data = await res.json();
        currentConcursos = data.concursos || [];
        fetchedFromServer = true;
      }
    } catch (_) {
      fetchedFromServer = false;
    }
  }

  if (!fetchedFromServer) {
    const dataset = await fetchDatasetStatic();
    currentConcursos = filterAndSortClientSide(dataset);
  }

  if (countEl) {
    countEl.innerText = `${currentConcursos.length} editais encontrados`;
  }
  renderCurrentConcursos();
}

function renderCurrentConcursos() {
  const listEl = document.getElementById("concursos-list");
  if (!listEl) return;

  if (currentConcursos.length === 0) {
    listEl.className = "";
    listEl.innerHTML = `
      <div style="text-align: center; padding: 48px 16px; color: var(--text-secondary); background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: var(--radius-lg);">
        <p style="font-size: 1.1rem; font-weight: 600; color: var(--text-primary); margin-bottom: 6px;">Nenhum concurso encontrado</p>
        <p style="font-size: 0.84rem;">Tente ajustar os filtros, ampliar o raio de distância ou clique em 'Verificar Editais'.</p>
      </div>
    `;
    return;
  }

  if (currentViewMode === "table") {
    listEl.className = "concursos-table-wrap";
    listEl.innerHTML = renderTableView(currentConcursos);
  } else {
    listEl.className = "concursos-grid";
    listEl.innerHTML = currentConcursos.map(c => renderConcursoCard(c)).join("");
  }
}

async function loadFavoritos() {
  const listEl = document.getElementById("favoritos-list");
  if (!listEl) return;

  const favSet = new Set(getStoredFavorites());
  let favs = [];

  if (!isStaticEnvironment()) {
    try {
      let url = "/api/concursos?only_favorites=true&limit=150";
      if (userCoordinates) {
        url += `&user_lat=${userCoordinates.lat}&user_lon=${userCoordinates.lon}`;
      }
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        favs = data.concursos || [];
      }
    } catch (_) {}
  }

  if (favs.length === 0) {
    const dataset = await fetchDatasetStatic();
    favs = dataset.filter(c => favSet.has(c.external_id));
    favs.forEach(c => {
      c.is_favorite = true;
      if (userCoordinates && c.lat && c.lon) {
        c.distance_km = calculateHaversineDistance(userCoordinates.lat, userCoordinates.lon, c.lat, c.lon);
      }
    });
  }

  if (favs.length === 0) {
    listEl.innerHTML = `
      <div style="text-align: center; padding: 48px 16px; color: var(--text-secondary); background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: var(--radius-lg); grid-column: 1 / -1;">
        <p style="font-size: 1.1rem; font-weight: 600; color: var(--text-primary); margin-bottom: 6px;">Nenhum favorito salvo</p>
        <p style="font-size: 0.84rem;">Clique no ícone de estrela de qualquer concurso para acompanhá-lo aqui.</p>
      </div>
    `;
    return;
  }

  listEl.innerHTML = favs.map(c => renderConcursoCard(c)).join("");
}

/* -------------------------------------------------------------
 * 9. RENDERIZAÇÃO DE CARDS & TABELA (ESTILO LINEAR / SHADCN)
 * ------------------------------------------------------------- */
function renderConcursoCard(c) {
  const isFav = Boolean(c.is_favorite);
  const isChecked = selectedForCompare.has(c.external_id) ? "checked" : "";

  // Distância
  let distBadge = "";
  if (c.distance_km !== null && c.distance_km !== undefined) {
    const d = c.distance_km;
    const cls = d <= 50 ? "near" : (d <= 150 ? "mid" : "far");
    distBadge = `<span class="badge-dist ${cls}">${ICONS.pin} ~${d} km</span>`;
  }

  // Salário
  let salaryPill = "";
  if (c.salary) {
    const formatted = "R$ " + c.salary.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    salaryPill = `<span class="pill pill-salary">${ICONS.cash} ${formatted}</span>`;
  }

  // Vagas
  const vacanciesPill = `<span class="pill pill-vacancies">${ICONS.users} ${escapeHtml(c.vacancies_text || 'Vagas n/i')}</span>`;

  // Carreira
  let careerPill = "";
  if (c.area && c.area !== "Geral") {
    careerPill = `<span class="pill pill-career">${ICONS.briefcase} ${escapeHtml(c.area.split(',')[0])}</span>`;
  }

  // Prazo
  let deadlinePill = "";
  const days = c.days_remaining;
  if (days !== null && days !== undefined) {
    if (days <= 3) {
      deadlinePill = `<span class="pill pill-deadline urgent">${ICONS.calendar} Restam ${days}d</span>`;
    } else {
      deadlinePill = `<span class="pill pill-deadline">${ICONS.calendar} Até ${c.deadline_text}</span>`;
    }
  } else {
    deadlinePill = `<span class="pill pill-deadline">${ICONS.calendar} ${c.deadline_text || 'Inscrições abertas'}</span>`;
  }

  // Data da Prova (se já enriquecido)
  let examPill = "";
  if (c.exam_date) {
    examPill = `<span class="pill pill-deadline" style="color: var(--accent-rose); font-weight: 500;">📅 ${escapeHtml(c.exam_date.split('.')[0])}</span>`;
  }

  const notesPill = c.user_notes ? `<span class="pill pill-notes">📌 Nota</span>` : "";

  return `
    <article class="card-item ${isFav ? 'favorited' : ''}" id="card-${c.external_id}" onclick="openModalWithItem('${c.external_id}')">
      <div class="card-top">
        <div class="card-geo-badge">
          <span class="badge-uf">${c.uf || 'BR'}</span>
          <span class="badge-city">${escapeHtml(c.cidade || c.uf)}</span>
          ${distBadge}
        </div>
        <button class="star-btn ${isFav ? 'active' : ''}" onclick="event.stopPropagation(); toggleFavorite('${c.external_id}')" title="Favoritar">
          ${isFav ? ICONS.starFilled : ICONS.star}
        </button>
      </div>

      <h3 class="card-title">${escapeHtml(c.title)}</h3>

      <div class="card-pills">
        ${salaryPill}
        ${vacanciesPill}
        ${careerPill}
        ${deadlinePill}
        ${examPill}
        ${notesPill}
      </div>

      <p class="card-excerpt">${escapeHtml(c.details || 'Acesse o edital oficial para consultar as vagas e requisitos.')}</p>

      <div class="card-footer" onclick="event.stopPropagation()">
        <label class="compare-label">
          <input type="checkbox" class="compare-checkbox" ${isChecked} onchange="toggleCompare('${c.external_id}', this.checked)">
          <span>Comparar</span>
        </label>

        <div class="card-actions-right">
          <button class="btn-link-action" onclick="openModalWithItem('${c.external_id}'); event.stopPropagation();">
            <span>+ Detalhes</span>
          </button>
          <a href="${c.url}" target="_blank" rel="noopener" class="btn-link-action" onclick="event.stopPropagation()">
            <span>Edital</span>
            ${ICONS.arrowUpRight}
          </a>
        </div>
      </div>
    </article>
  `;
}

function renderTableView(concursos) {
  return `
    <table class="concursos-table">
      <thead>
        <tr>
          <th style="width: 32px;"></th>
          <th>UF / Local</th>
          <th>Órgão / Concurso</th>
          <th>Salário</th>
          <th>Vagas</th>
          <th>Carreira</th>
          <th>Prazo</th>
          <th>Distância</th>
          <th style="text-align: right;">Ações</th>
        </tr>
      </thead>
      <tbody>
        ${concursos.map(c => {
          const isFav = Boolean(c.is_favorite);
          return `
            <tr onclick="openModalWithItem('${c.external_id}')" style="cursor: pointer;">
              <td onclick="event.stopPropagation()">
                <button class="star-btn ${isFav ? 'active' : ''}" onclick="toggleFavorite('${c.external_id}')">
                  ${isFav ? ICONS.starFilled : ICONS.star}
                </button>
              </td>
              <td><span class="badge-uf">${c.uf}</span> <span style="font-size: 0.76rem; color: var(--text-secondary);">${escapeHtml(c.cidade || '')}</span></td>
              <td>
                <div style="font-weight: 600;">${escapeHtml(c.title)}</div>
                <div style="font-size: 0.74rem; color: var(--text-muted);">${escapeHtml(c.banca || 'Órgão Próprio')}</div>
              </td>
              <td style="color: var(--accent-emerald); font-weight: 600; white-space: nowrap;">
                ${c.salary ? 'R$ ' + c.salary.toLocaleString('pt-BR', { minimumFractionDigits: 2 }) : '-'}
              </td>
              <td style="white-space: nowrap;">${escapeHtml(c.vacancies_text || '-')}</td>
              <td><span class="pill pill-career" style="font-size: 0.72rem;">${escapeHtml(c.area || 'Geral')}</span></td>
              <td style="white-space: nowrap; font-size: 0.78rem;">${escapeHtml(c.deadline_text || '-')}</td>
              <td style="white-space: nowrap;">${c.distance_km !== null && c.distance_km !== undefined ? `<span class="badge-dist near">~${c.distance_km} km</span>` : '-'}</td>
              <td style="text-align: right;" onclick="event.stopPropagation()">
                <a href="${c.url}" target="_blank" rel="noopener" class="btn-link-action">
                  <span>Edital</span>
                  ${ICONS.arrowUpRight}
                </a>
              </td>
            </tr>
          `;
        }).join("")}
      </tbody>
    </table>
  `;
}

async function openModalWithItem(externalId) {
  const item = currentConcursos.find(c => c.external_id === externalId) || {};
  activeModalConcurso = item;

  document.getElementById("modal-uf").innerText = item.uf || "BR";
  document.getElementById("modal-cidade").innerText = item.cidade || item.uf;

  const distBadge = document.getElementById("modal-dist");
  if (item.distance_km !== null && item.distance_km !== undefined) {
    distBadge.innerHTML = `📍 ~${item.distance_km} km de você`;
    distBadge.style.display = "inline-flex";
  } else {
    distBadge.style.display = "none";
  }

  document.getElementById("modal-tipo").innerText = item.tipo || "Concurso Público";
  document.getElementById("modal-title").innerText = item.title;
  document.getElementById("modal-banca").innerText = item.banca || "Órgão Próprio / A Definir";
  document.getElementById("modal-exam-date").innerText = item.exam_date || "A definir / Consulte edital";
  document.getElementById("modal-fee").innerText = item.fee_text || "Consulte edital";
  document.getElementById("modal-workload").innerText = item.workload || "40h semanais (padrão)";
  document.getElementById("modal-regime").innerText = item.regime || "Estatutário / CLT";
  document.getElementById("modal-app-period").innerText = item.application_period || (item.deadline_text ? `Até ${item.deadline_text}` : "Inscrições Abertas");
  document.getElementById("modal-details-text").innerText = item.full_summary || item.details || "Carregando resumo oficial...";

  const officialBox = document.getElementById("modal-official-box");
  const officialLink = document.getElementById("modal-official-link");
  if (item.official_url) {
    officialLink.href = item.official_url;
    officialBox.style.display = "block";
  } else {
    officialBox.style.display = "none";
  }

  // Anotações
  document.getElementById("modal-user-notes").value = item.user_notes || "";

  // Pills
  const pillsEl = document.getElementById("modal-pills");
  let salStr = item.salary ? `R$ ${item.salary.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}` : "A combinar";
  pillsEl.innerHTML = `
    <span class="pill pill-salary" style="font-size: 0.85rem; padding: 4px 10px;">${ICONS.cash} ${salStr}</span>
    <span class="pill pill-vacancies" style="font-size: 0.85rem; padding: 4px 10px;">${ICONS.users} ${item.vacancies_text || 'Vagas N/I'}</span>
    <span class="pill pill-career" style="font-size: 0.85rem; padding: 4px 10px;">${(item.education || []).join(' / ') || 'Geral'}</span>
  `;

  // Botão Favorito no Modal
  const favBtn = document.getElementById("modal-fav-btn");
  favBtn.innerHTML = item.is_favorite ? "⭐ Remover Favorito" : "☆ Salvar nos Favoritos";

  document.getElementById("modal-link-btn").href = item.url;
  document.getElementById("modal-details").style.display = "flex";

  // Se ainda não tem o resumo completo aprofundado, busca no backend sob demanda
  if (!item.full_summary) {
    const loader = document.getElementById("modal-loading-indicator");
    if (loader) loader.style.display = "inline";
    try {
      const res = await fetch(`/api/concurso/details?id=${externalId}`);
      if (res.ok) {
        const fullData = await res.json();
        Object.assign(item, fullData);

        if (activeModalConcurso && activeModalConcurso.external_id === externalId) {
          if (fullData.full_summary) document.getElementById("modal-details-text").innerText = fullData.full_summary;
          if (fullData.exam_date) document.getElementById("modal-exam-date").innerText = fullData.exam_date;
          if (fullData.fee_text) document.getElementById("modal-fee").innerText = fullData.fee_text;
          if (fullData.workload) document.getElementById("modal-workload").innerText = fullData.workload;
          if (fullData.regime) document.getElementById("modal-regime").innerText = fullData.regime;
          if (fullData.application_period) document.getElementById("modal-app-period").innerText = fullData.application_period;
          if (fullData.banca) document.getElementById("modal-banca").innerText = fullData.banca;
          if (fullData.official_url) {
            officialLink.href = fullData.official_url;
            officialBox.style.display = "block";
          }
        }
      }
    } catch (err) {
      console.warn("Erro ao buscar detalhes completos:", err);
    } finally {
      if (loader) loader.style.display = "none";
    }
  }
}

async function saveModalNotes() {
  if (!activeModalConcurso) return;

  const notes = document.getElementById("modal-user-notes").value.trim();
  const extId = activeModalConcurso.external_id;

  try {
    localStorage.setItem("monitor_notes_" + extId, notes);
  } catch (_) {}

  activeModalConcurso.user_notes = notes;
  if (allStaticConcursos) {
    const sFound = allStaticConcursos.find(c => c.external_id === extId);
    if (sFound) sFound.user_notes = notes;
  }

  if (!isStaticEnvironment()) {
    try {
      fetch("/api/notes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ external_id: extId, notes })
      }).catch(() => {});
    } catch (_) {}
  }

  showToast("Anotação salva com sucesso! 📌");
  renderCurrentConcursos();
}

/* -------------------------------------------------------------
 * 10. ESTATÍSTICAS E ANALYTICS
 * ------------------------------------------------------------- */
async function loadStats() {
  const favs = getStoredFavorites();
  let statsLoaded = false;

  if (!isStaticEnvironment()) {
    try {
      const res = await fetch("/api/stats");
      if (res.ok) {
        const data = await res.json();
        document.getElementById("stat-total").innerText = data.total;
        document.getElementById("stat-open").innerText = data.open;
        const favCount = Math.max(data.favorites || 0, favs.length);
        document.getElementById("fav-count-badge").innerText = favCount;
        const mobFavBadge = document.getElementById("mobile-fav-badge");
        if (mobFavBadge) mobFavBadge.innerText = favCount;

        if (data.max_salary > 0) {
          document.getElementById("stat-salary").innerText = "R$ " + data.max_salary.toLocaleString("pt-BR", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
          });
        }
        statsLoaded = true;
      }
    } catch (_) {}
  }

  if (!statsLoaded) {
    try {
      const res = await fetch("./data/stats.json");
      if (res.ok) {
        const data = await res.json();
        document.getElementById("stat-total").innerText = data.total;
        document.getElementById("stat-open").innerText = data.open;
        document.getElementById("fav-count-badge").innerText = favs.length;
        const mobFavBadge = document.getElementById("mobile-fav-badge");
        if (mobFavBadge) mobFavBadge.innerText = favs.length;
        if (data.max_salary > 0) {
          document.getElementById("stat-salary").innerText = "R$ " + data.max_salary.toLocaleString("pt-BR", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
          });
        }
        statsLoaded = true;
      }
    } catch (_) {}
  }

  if (!statsLoaded) {
    const dataset = await fetchDatasetStatic();
    if (dataset.length > 0) {
      document.getElementById("stat-total").innerText = dataset.length;
      document.getElementById("stat-open").innerText = dataset.filter(c => !c.is_expired).length;
      document.getElementById("fav-count-badge").innerText = favs.length;
      const mobFavBadge = document.getElementById("mobile-fav-badge");
      if (mobFavBadge) mobFavBadge.innerText = favs.length;
      const maxSal = Math.max(...dataset.map(c => c.salary || 0));
      document.getElementById("stat-salary").innerText = "R$ " + maxSal.toLocaleString("pt-BR", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      });
    }
  }
}

async function loadAnalytics() {
  if (!isStaticEnvironment()) {
    try {
      const res = await fetch("/api/analytics");
      if (res.ok) {
        const data = await res.json();
        renderAnalyticsData(data);
        return;
      }
    } catch (_) {}
  }

  try {
    const res = await fetch("./data/analytics.json");
    if (res.ok) {
      const data = await res.json();
      renderAnalyticsData(data);
      return;
    }
  } catch (_) {}

  // Cálculo em memória caso API esteja offline
  const dataset = await fetchDatasetStatic();
  if (dataset.length > 0) {
    const brackets = {
      "Até R$ 3.000": 0,
      "R$ 3.001 a R$ 6.000": 0,
      "R$ 6.001 a R$ 10.000": 0,
      "R$ 10.001 a R$ 15.000": 0,
      "Acima de R$ 15.000": 0
    };
    const ufCounts = {};
    const careerCounts = {};
    const bancaCounts = {};

    dataset.forEach(c => {
      const s = c.salary || 0;
      if (s <= 3000) brackets["Até R$ 3.000"]++;
      else if (s <= 6000) brackets["R$ 3.001 a R$ 6.000"]++;
      else if (s <= 10000) brackets["R$ 6.001 a R$ 10.000"]++;
      else if (s <= 15000) brackets["R$ 10.001 a R$ 15.000"]++;
      else brackets["Acima de R$ 15.000"]++;

      const u = c.uf || "Outros";
      ufCounts[u] = (ufCounts[u] || 0) + 1;

      const a = c.area || "Geral";
      careerCounts[a] = (careerCounts[a] || 0) + 1;

      const b = c.banca || "Outras";
      bancaCounts[b] = (bancaCounts[b] || 0) + 1;
    });

    const topUfs = Object.entries(ufCounts).sort((a,b)=>b[1]-a[1]).slice(0,8).map(([uf,count])=>({uf,count}));
    const careers = Object.entries(careerCounts).sort((a,b)=>b[1]-a[1]).slice(0,8).map(([area,count])=>({area,count}));
    const bancas = Object.entries(bancaCounts).sort((a,b)=>b[1]-a[1]).slice(0,8).map(([banca,count])=>({banca,count}));

    renderAnalyticsData({
      salary_brackets: brackets,
      top_ufs: topUfs,
      careers: careers,
      bancas: bancas
    });
  }
}

function renderAnalyticsData(data) {
  renderProgressList("chart-salaries", data.salary_brackets || {}, "emerald");

  const ufsData = {};
  (data.top_ufs || []).forEach(item => ufsData[item.uf] = item.count);
  renderProgressList("chart-ufs", ufsData, "primary");

  const careersData = {};
  (data.careers || []).forEach(item => careersData[item.area] = item.count);
  renderProgressList("chart-careers", careersData, "purple");

  const bancasData = {};
  (data.bancas || []).forEach(item => bancasData[item.banca] = item.count);
  renderProgressList("chart-bancas", bancasData, "amber");
}

function renderProgressList(containerId, dataObj, colorClass) {
  const container = document.getElementById(containerId);
  if (!container) return;

  const entries = Object.entries(dataObj);
  const maxVal = Math.max(...entries.map(e => e[1]), 1);

  container.innerHTML = entries.map(([key, val]) => {
    const pct = Math.round((val / maxVal) * 100);
    return `
      <div class="stat-bar-item">
        <div class="stat-bar-header">
          <span style="color: var(--text-secondary);">${escapeHtml(key)}</span>
          <span style="font-weight: 600;">${val} editais</span>
        </div>
        <div class="stat-bar-track">
          <div class="stat-bar-fill ${colorClass}" style="width: ${pct}%"></div>
        </div>
      </div>
    `;
  }).join("");
}

/* -------------------------------------------------------------
 * 11. EXPORTAÇÃO CSV
 * ------------------------------------------------------------- */
function exportCsv() {
  if (!isStaticEnvironment()) {
    const params = getActiveFilterParams(false);
    window.open(`/api/export?${params.toString()}`, "_blank");
    return;
  }
  // Exportação CSV estática no navegador
  if (!currentConcursos || currentConcursos.length === 0) {
    showToast("Nenhum edital para exportar.");
    return;
  }
  const headers = ["Título", "UF", "Cidade", "Salário", "Vagas", "Escolaridade", "Prazo", "Banca", "Tipo", "Link"];
  const rows = currentConcursos.map(c => [
    `"${(c.title || '').replace(/"/g, '""')}"`,
    `"${c.uf || ''}"`,
    `"${c.cidade || ''}"`,
    c.salary ? c.salary.toFixed(2) : "0.00",
    `"${c.vacancies_text || c.vacancies || ''}"`,
    `"${(c.education || []).join(';')}"`,
    `"${c.deadline_text || ''}"`,
    `"${c.banca || ''}"`,
    `"${c.tipo || ''}"`,
    `"${c.url || ''}"`
  ]);
  const csvContent = "\uFEFF" + [headers.join(","), ...rows.map(r => r.join(","))].join("\n");
  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.setAttribute("href", url);
  link.setAttribute("download", `concursos_filtrados_${new Date().toISOString().slice(0,10)}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  showToast("CSV exportado com sucesso! 📄");
}

/* -------------------------------------------------------------
 * 12. FAVORITOS
 * ------------------------------------------------------------- */
async function toggleFavorite(externalId) {
  let favs = getStoredFavorites();
  const index = favs.indexOf(externalId);
  const isFav = index === -1;

  if (isFav) {
    favs.push(externalId);
  } else {
    favs.splice(index, 1);
  }
  saveStoredFavorites(favs);

  if (!isStaticEnvironment()) {
    try {
      fetch("/api/favorite", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ external_id: externalId })
      }).catch(() => {});
    } catch (_) {}
  }

  const found = currentConcursos.find(c => c.external_id === externalId);
  if (found) found.is_favorite = isFav;
  if (allStaticConcursos) {
    const sFound = allStaticConcursos.find(c => c.external_id === externalId);
    if (sFound) sFound.is_favorite = isFav;
  }

  if (activeModalConcurso && activeModalConcurso.external_id === externalId) {
    activeModalConcurso.is_favorite = isFav;
    document.getElementById("modal-fav-btn").innerHTML = isFav ? "⭐ Remover Favorito" : "☆ Salvar nos Favoritos";
  }

  renderCurrentConcursos();
  loadStats();
  showToast(isFav ? "Adicionado aos favoritos ⭐" : "Removido dos favoritos");
}

/* -------------------------------------------------------------
 * 13. CONFIGURAÇÕES & NOTIFICAÇÕES
 * ------------------------------------------------------------- */
async function loadConfig() {
  try {
    const res = await fetch("/api/config");
    if (!res.ok) return;
    const cfg = await res.json();

    const tg = cfg.notifications?.telegram || {};
    document.getElementById("cfg-tg-token").value = tg.bot_token || "";
    document.getElementById("cfg-tg-chat").value = tg.chat_id || "";

    const dc = cfg.notifications?.discord || {};
    document.getElementById("cfg-dc-webhook").value = dc.webhook_url || "";

    const filters = cfg.filters || {};
    document.getElementById("cfg-keywords").value = (filters.keywords || []).join(", ");
    document.getElementById("cfg-min-salary").value = filters.min_salary || "";
  } catch (err) {
    console.error("Erro ao carregar config:", err);
  }
}

async function saveSettings() {
  const tgToken = document.getElementById("cfg-tg-token").value.trim();
  const tgChat = document.getElementById("cfg-tg-chat").value.trim();
  const dcWebhook = document.getElementById("cfg-dc-webhook").value.trim();
  const kwStr = document.getElementById("cfg-keywords").value.trim();
  const minSal = parseFloat(document.getElementById("cfg-min-salary").value) || 0.0;

  const keywords = kwStr ? kwStr.split(",").map(k => k.trim().toLowerCase()).filter(Boolean) : [];

  const payload = {
    filters: { keywords, min_salary: minSal },
    notifications: {
      telegram: { enabled: Boolean(tgToken && tgChat), bot_token: tgToken, chat_id: tgChat },
      discord: { enabled: Boolean(dcWebhook), webhook_url: dcWebhook }
    }
  };

  try {
    const res = await fetch("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      showToast("Configurações salvas com sucesso! ✅");
    }
  } catch (err) {
    showToast("Erro ao salvar configurações.");
  }
}

async function testTelegram() {
  const token = document.getElementById("cfg-tg-token").value.trim();
  const chatId = document.getElementById("cfg-tg-chat").value.trim();

  if (!token || !chatId) {
    alert("Preencha o Token do Bot e o Chat ID primeiro.");
    return;
  }

  showToast("Enviando teste para Telegram...");
  try {
    const res = await fetch("/api/test-telegram", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token, chat_id: chatId })
    });
    const data = await res.json();
    alert(data.success ? "Sucesso! Mensagem enviada para o Telegram." : "Falha ao enviar para o Telegram.");
  } catch (err) {
    alert("Erro na requisição.");
  }
}

async function testDiscord() {
  const webhook = document.getElementById("cfg-dc-webhook").value.trim();
  if (!webhook) {
    alert("Preencha a URL do Webhook do Discord primeiro.");
    return;
  }

  showToast("Enviando teste para Discord...");
  try {
    const res = await fetch("/api/test-discord", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ webhook_url: webhook })
    });
    const data = await res.json();
    alert(data.success ? "Sucesso! Card enviado para o Discord." : "Falha ao enviar para o Discord.");
  } catch (err) {
    alert("Erro na requisição.");
  }
}

/* -------------------------------------------------------------
 * 14. SCAN E UTILITÁRIOS
 * ------------------------------------------------------------- */
async function runScan() {
  const btn = document.getElementById("btn-scan");
  if (!btn) return;
  const icon = btn.querySelector(".scan-icon");
  const text = btn.querySelector(".scan-text");

  btn.disabled = true;
  if (icon) icon.innerHTML = '<span class="spinner"></span>';
  if (text) text.innerText = "Varrendo...";

  try {
    const res = await fetch("/api/scan", { method: "POST" });
    const data = await res.json();
    if (data.status === "success") {
      showToast(`Varredura concluída! ${data.summary.total_scanned} editais processados.`);
      await loadStats();
      await loadConcursos();
    }
  } catch (err) {
    showToast("Erro ao executar varredura.");
  } finally {
    btn.disabled = false;
    if (icon) icon.innerHTML = `<path d="M21.5 2v6h-6"/><path d="M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/>`;
    if (text) text.innerText = "Verificar Editais";
  }
}

function showToast(msg) {
  const toast = document.getElementById("toast");
  if (!toast) return;
  toast.innerText = msg;
  toast.style.display = "flex";
  setTimeout(() => {
    toast.style.display = "none";
  }, 3000);
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
