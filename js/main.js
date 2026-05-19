// ============================================
// AIRA Main — Layout, helperlar, til
// ============================================

const translations = {
  uz: {
    dashboard: "Dashboard",
    upload: "Achot yuklash",
    list_reports: "Список отчётов",
    base: "База",
    costs: "Себестоимость",
    storage: "Хранение",
    self_purchase: "Самовыкупы",
    ext_expenses: "Внешние расходы",
    pnl: "P&L",
    abc: "ABC tahlil",
    products: "Отчёт по товарам",
    monthly: "Отчёт по месяцам",
    charts: "Графики",
    fines: "Штрафы",
    calculator: "Калькулятор",
    capitalization: "Капитализация",
    analytics: "Smart Аналитика",
    settings: "Sozlamalar",
    section_data: "MA'LUMOTLAR",
    section_reports: "HISOBOTLAR",
    section_tools: "VOSITALAR",
    section_other: "BOSHQA"
  },
  ru: {
    dashboard: "Главная",
    upload: "Загрузка",
    list_reports: "Список отчётов",
    base: "База",
    costs: "Себестоимость",
    storage: "Хранение",
    self_purchase: "Самовыкупы",
    ext_expenses: "Внешние расходы",
    pnl: "P&L",
    abc: "ABC анализ",
    products: "Отчёт по товарам",
    monthly: "Отчёт по месяцам",
    charts: "Графики",
    fines: "Штрафы",
    calculator: "Калькулятор",
    capitalization: "Капитализация",
    analytics: "Smart Аналитика",
    settings: "Настройки",
    section_data: "ДАННЫЕ",
    section_reports: "ОТЧЁТЫ",
    section_tools: "ИНСТРУМЕНТЫ",
    section_other: "ДРУГОЕ"
  }
};

let currentLang = Storage.getLang();

function t(key) { return translations[currentLang]?.[key] || key; }
function setLanguage(lang) { currentLang = lang; Storage.setLang(lang); applyTranslations(); }
function applyTranslations() {
  document.querySelectorAll('[data-i18n]').forEach(el => { el.textContent = t(el.getAttribute('data-i18n')); });
  document.querySelectorAll('.lang-btn').forEach(btn => {
    btn.classList.toggle('active', btn.getAttribute('data-lang') === currentLang);
  });
}

// ============ Format ============
function fmt(num) {
  if (typeof num !== 'number' || isNaN(num)) return '—';
  return new Intl.NumberFormat('ru-RU').format(Math.round(num));
}

function fmtMoney(num, currency = '₽') {
  if (typeof num !== 'number' || isNaN(num)) return '—';
  return fmt(num) + ' ' + currency;
}

function fmtMoneyShort(num, currency = '₽') {
  if (typeof num !== 'number' || isNaN(num)) return '—';
  if (Math.abs(num) >= 1000000) return (num / 1000000).toFixed(2) + 'M ' + currency;
  if (Math.abs(num) >= 1000) return (num / 1000).toFixed(1) + 'K ' + currency;
  return fmt(num) + ' ' + currency;
}

function fmtPercent(num) {
  if (typeof num !== 'number' || isNaN(num)) return '—';
  return num.toFixed(1) + '%';
}

function fmtDate(str) {
  if (!str) return '—';
  const d = new Date(str);
  if (isNaN(d)) return str;
  return d.toLocaleDateString('ru-RU');
}

function fmtNumWithSign(num, currency = '₽') {
  if (typeof num !== 'number' || isNaN(num)) return '—';
  const sign = num > 0 ? '+' : '';
  return sign + fmtMoney(num, currency);
}

// ============ Icons ============
const icons = {
  dashboard: '<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  upload: '<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  list: '<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  database: '<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M4 7v10c0 2 3 3 8 3s8-1 8-3V7M4 7c0 2 3 3 8 3s8-1 8-3M4 7c0-2 3-3 8-3s8 1 8 3m0 5c0 2-3 3-8 3s-8-1-8-3" stroke-linecap="round"/></svg>',
  cash: '<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M12 6v12m-3-2.818l.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-2.21 0-4-1.79-4-4s1.79-4 4-4 4 1.79 4 4" stroke-linecap="round"/></svg>',
  box: '<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  refresh: '<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  megaphone: '<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M11 5.882V19.24a1.76 1.76 0 01-3.417.592l-2.147-6.15M18 13a3 3 0 100-6M5.436 13.683A4.001 4.001 0 017 6h1.832c4.1 0 7.625-1.234 9.168-3v14c-1.543-1.766-5.067-3-9.168-3H7a3.988 3.988 0 01-1.564-.317z" stroke-linecap="round"/></svg>',
  receipt: '<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" stroke-linecap="round"/></svg>',
  chart: '<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" stroke-linecap="round"/></svg>',
  pie: '<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M11 3.055A9.001 9.001 0 1020.945 13H11V3.055z" stroke-linecap="round"/><path d="M20.488 9H15V3.512A9.025 9.025 0 0120.488 9z" stroke-linecap="round"/></svg>',
  calendar: '<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  trending: '<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  alert: '<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M12 9v2m0 4h.01M5.07 19h13.86c1.54 0 2.5-1.67 1.73-3L13.73 4a2 2 0 00-3.46 0L3.34 16c-.77 1.33.19 3 1.73 3z" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  calc: '<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><rect x="4" y="3" width="16" height="18" rx="2" stroke-linejoin="round"/><line x1="8" y1="7" x2="16" y2="7" stroke-linecap="round"/><line x1="8" y1="11" x2="8" y2="11" stroke-linecap="round"/><line x1="12" y1="11" x2="12" y2="11" stroke-linecap="round"/><line x1="16" y1="11" x2="16" y2="11" stroke-linecap="round"/><line x1="8" y1="15" x2="8" y2="15" stroke-linecap="round"/><line x1="12" y1="15" x2="12" y2="15" stroke-linecap="round"/><line x1="16" y1="15" x2="16" y2="17" stroke-linecap="round"/><line x1="8" y1="18" x2="14" y2="18" stroke-linecap="round"/></svg>',
  cube: '<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z" stroke-linecap="round" stroke-linejoin="round"/><polyline points="3.27 6.96 12 12.01 20.73 6.96" stroke-linecap="round" stroke-linejoin="round"/><line x1="12" y1="22.08" x2="12" y2="12" stroke-linecap="round"/></svg>',
  brain: '<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 1.98-3A2.5 2.5 0 0 1 9.5 2Z" stroke-linecap="round" stroke-linejoin="round"/><path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-1.98-3A2.5 2.5 0 0 0 14.5 2Z" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  settings: '<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" stroke-linecap="round"/><path d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" stroke-linecap="round"/></svg>',
  search: '<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" stroke-linecap="round"/></svg>'
};

// ============ Sidebar ============
function generateSidebar(activePage) {
  return `
    <div class="sidebar-logo">
      <div class="sidebar-logo-icon">AIRA</div>
      <div>
        <div class="sidebar-logo-text">AIRA</div>
        <div style="font-size: 9px; color: rgba(255,255,255,0.5); margin-top: 1px;">WB Analytics</div>
      </div>
    </div>
    <nav class="sidebar-nav">
      <a href="dashboard.html" class="sidebar-link ${activePage === 'dashboard' ? 'active' : ''}">
        ${icons.dashboard}<span data-i18n="dashboard">Dashboard</span>
      </a>
      <a href="upload.html" class="sidebar-link ${activePage === 'upload' ? 'active' : ''}">
        ${icons.upload}<span data-i18n="upload">Achot yuklash</span>
      </a>

      <div class="sidebar-section" data-i18n="section_data">MA'LUMOTLAR</div>
      <a href="list-reports.html" class="sidebar-link ${activePage === 'list-reports' ? 'active' : ''}">
        ${icons.list}<span data-i18n="list_reports">Список отчётов</span>
      </a>
      <a href="base.html" class="sidebar-link ${activePage === 'base' ? 'active' : ''}">
        ${icons.database}<span data-i18n="base">База</span>
      </a>
      <a href="costs.html" class="sidebar-link ${activePage === 'costs' ? 'active' : ''}">
        ${icons.cash}<span data-i18n="costs">Себестоимость</span>
      </a>
      <a href="storage-page.html" class="sidebar-link ${activePage === 'storage' ? 'active' : ''}">
        ${icons.box}<span data-i18n="storage">Хранение</span>
      </a>
      <a href="self-purchase.html" class="sidebar-link ${activePage === 'self_purchase' ? 'active' : ''}">
        ${icons.refresh}<span data-i18n="self_purchase">Самовыкупы</span>
      </a>
      <a href="ext-expenses.html" class="sidebar-link ${activePage === 'ext_expenses' ? 'active' : ''}">
        ${icons.megaphone}<span data-i18n="ext_expenses">Внешние расходы</span>
      </a>

      <div class="sidebar-section" data-i18n="section_reports">HISOBOTLAR</div>
      <a href="charts.html" class="sidebar-link ${activePage === 'charts' ? 'active' : ''}">
        ${icons.trending}<span data-i18n="charts">Графики</span>
      </a>
      <a href="fines.html" class="sidebar-link ${activePage === 'fines' ? 'active' : ''}">
        ${icons.alert}<span data-i18n="fines">Штрафы</span>
      </a>
      <a href="pnl.html" class="sidebar-link ${activePage === 'pnl' ? 'active' : ''}">
        ${icons.receipt}<span data-i18n="pnl">P&L</span>
      </a>
      <a href="monthly.html" class="sidebar-link ${activePage === 'monthly' ? 'active' : ''}">
        ${icons.calendar}<span data-i18n="monthly">Отчёт по месяцам</span>
      </a>
      <a href="abc.html" class="sidebar-link ${activePage === 'abc' ? 'active' : ''}">
        ${icons.pie}<span data-i18n="abc">ABC tahlil</span>
      </a>
      <a href="products.html" class="sidebar-link ${activePage === 'products' ? 'active' : ''}">
        ${icons.chart}<span data-i18n="products">Отчёт по товарам</span>
      </a>

      <div class="sidebar-section" data-i18n="section_tools">VOSITALAR</div>
      <a href="calculator.html" class="sidebar-link ${activePage === 'calculator' ? 'active' : ''}">
        ${icons.calc}<span data-i18n="calculator">Калькулятор</span>
      </a>
      <a href="capitalization.html" class="sidebar-link ${activePage === 'capitalization' ? 'active' : ''}">
        ${icons.cube}<span data-i18n="capitalization">Капитализация</span>
      </a>
      <a href="analytics.html" class="sidebar-link ${activePage === 'analytics' ? 'active' : ''}">
        ${icons.brain}<span data-i18n="analytics">Smart Аналитика</span>
      </a>

      <div class="sidebar-section" data-i18n="section_other">BOSHQA</div>
      <a href="settings.html" class="sidebar-link ${activePage === 'settings' ? 'active' : ''}">
        ${icons.settings}<span data-i18n="settings">Sozlamalar</span>
      </a>
    </nav>
  `;
}

// ============ Topbar ============
function generateTopbar() {
  const settings = Storage.getSettings();
  const base = Storage.getBase();
  const profiles = Storage.getProfiles();
  const activeProfile = Storage.getActiveProfile();
  const initials = (activeProfile.name || 'IP').split(' ').slice(-2).map(w => w[0]).join('').toUpperCase().substring(0,2);

  return `
    <div class="profile-selector" onclick="toggleProfileDropdown(event)" id="profileSelector" style="position: relative;">
      <div class="profile-avatar">${initials}</div>
      <div class="profile-info">
        <div class="profile-name">${activeProfile.name || 'IP'}</div>
        <div class="profile-meta">${activeProfile.country || '🇰🇬'} · ${activeProfile.brand || 'Brend'} ${activeProfile.inn ? ' · ИНН ' + activeProfile.inn.substring(0, 6) + '..' : ''}</div>
      </div>
      <svg style="width: 14px; height: 14px; color: var(--text-tertiary); margin-left: 4px;" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M19 9l-7 7-7-7" stroke-linecap="round"/></svg>

      <!-- DROPDOWN -->
      <div id="profileDropdown" style="display: none; position: absolute; left: 0; top: calc(100% + 8px); background: white; border: 1px solid var(--border); border-radius: 12px; box-shadow: 0 8px 30px rgba(0,0,0,0.15); min-width: 360px; max-width: 440px; z-index: 200; overflow: hidden;">
        <div style="padding: 14px 16px; border-bottom: 1px solid var(--border-light);">
          <div style="font-size: 14px; font-weight: 600; color: var(--navy); margin-bottom: 8px;">Профиль</div>
          <input type="text" id="profileSearch" placeholder="Поиск по ИНН, наименованию и ID..." style="width: 100%; padding: 8px 12px; font-size: 12px; border: 1px solid var(--border); border-radius: 8px;" oninput="filterProfiles(this.value)">
        </div>
        <div id="profileList" style="max-height: 380px; overflow-y: auto;">
          ${profiles.map(p => {
            const isActive = p.id === activeProfile.id;
            const pInitials = (p.name || 'IP').split(' ').slice(-2).map(w => w[0]).join('').toUpperCase().substring(0,2);
            return `
              <div class="profile-item" data-profile-id="${p.id}" data-search="${(p.name + ' ' + (p.inn || '') + ' ' + (p.wb_id || '')).toLowerCase()}" onclick="event.stopPropagation(); switchProfile('${p.id}')" style="display: flex; align-items: center; gap: 10px; padding: 10px 16px; cursor: pointer; border-bottom: 1px solid var(--border-light); transition: background 0.15s; ${isActive ? 'background: var(--blue-bg);' : ''}">
                <div class="profile-avatar" style="background: ${isActive ? 'linear-gradient(135deg, #185FA5, #042C53)' : 'var(--gray-100)'}; color: ${isActive ? 'white' : 'var(--text-secondary)'};">${pInitials}</div>
                <div style="flex: 1; min-width: 0;">
                  <div style="font-size: 13px; font-weight: 600; color: var(--navy); display: flex; align-items: center; gap: 6px;">
                    ${p.name}
                    ${isActive ? '<span style="font-size: 9px; padding: 2px 6px; background: var(--blue); color: white; border-radius: 10px;">АКТИВНЫЙ</span>' : ''}
                  </div>
                  <div style="font-size: 10px; color: var(--text-tertiary); margin-top: 2px;">
                    ${p.brand || ''} ${p.inn ? '· ИНН ' + p.inn : ''} ${p.wb_id ? '· ID ' + p.wb_id : ''}
                  </div>
                </div>
                ${!isActive ? `<span style="font-size: 11px; color: var(--blue); font-weight: 600;">Открыть →</span>` : ''}
                ${p.id !== 'default' && !isActive ? `<button onclick="event.stopPropagation(); deleteProfile('${p.id}')" title="O'chirish" style="background: none; border: none; cursor: pointer; color: var(--red); font-size: 16px; padding: 2px 6px; border-radius: 4px;">×</button>` : ''}
              </div>
            `;
          }).join('')}
        </div>
        <div style="padding: 10px 16px; border-top: 1px solid var(--border-light);">
          <button onclick="event.stopPropagation(); openAddProfileModal()" style="width: 100%; padding: 8px; background: var(--blue-bg); color: var(--blue); border: none; border-radius: 8px; font-size: 12px; font-weight: 600; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 6px;">
            <span style="font-size: 16px;">+</span> Добавить компанию
          </button>
        </div>
      </div>
    </div>
    <div class="topbar-right">
      <div class="data-status">
        ${base.length > 0
          ? `<span class="badge badge-success">✓ ${fmt(base.length)} qator</span>`
          : `<a href="upload.html" class="badge badge-warning" style="text-decoration: none;">⚠ База bo'sh</a>`}
      </div>
      <div class="lang-switch">
        <button class="lang-btn ${currentLang === 'uz' ? 'active' : ''}" data-lang="uz">UZ</button>
        <button class="lang-btn ${currentLang === 'ru' ? 'active' : ''}" data-lang="ru">RU</button>
      </div>
    </div>
  `;
}

function setupLayout(activePage) {
  const sidebar = document.getElementById('sidebar');
  const topbar = document.getElementById('topbar');
  if (sidebar) sidebar.innerHTML = generateSidebar(activePage);
  if (topbar) topbar.innerHTML = generateTopbar();
  document.querySelectorAll('.lang-btn').forEach(btn => {
    btn.addEventListener('click', () => setLanguage(btn.getAttribute('data-lang')));
  });
  applyTranslations();
}

// ============ Notification ============
function notify(message, type = 'info') {
  const colors = {
    info: { bg: 'var(--blue-bg)', fg: 'var(--navy)' },
    success: { bg: 'var(--green-light)', fg: 'var(--green-dark)' },
    warning: { bg: 'var(--amber-light)', fg: 'var(--amber-dark)' },
    error: { bg: 'var(--red-light)', fg: 'var(--red-dark)' }
  };
  const c = colors[type] || colors.info;
  const toast = document.createElement('div');
  toast.style.cssText = `position: fixed; top: 20px; right: 20px; z-index: 1000;
    background: ${c.bg}; color: ${c.fg}; padding: 12px 16px;
    border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    font-size: 13px; font-weight: 500; max-width: 320px;
    animation: slideIn 0.3s ease-out;`;
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.3s';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// ============ Empty state ============
function renderEmpty(container, opts = {}) {
  const target = typeof container === 'string' ? document.querySelector(container) : container;
  if (!target) return;
  target.innerHTML = `
    <div class="empty-state" style="padding: 60px 20px;">
      <div class="empty-state-icon">${opts.icon || '📊'}</div>
      <h3 style="font-size: 16px; margin-bottom: 8px; color: var(--text);">${opts.title || 'Ma\'lumot yo\'q'}</h3>
      <p style="font-size: 13px; margin-bottom: 20px; color: var(--text-secondary);">${opts.message || 'Birinchi achotni yuklang'}</p>
      ${opts.link ? `<a href="${opts.link}" class="btn btn-primary">${opts.linkText || 'Yuklash'}</a>` : ''}
    </div>
  `;
}

// Global
window.t = t;
window.fmt = fmt;
window.fmtMoney = fmtMoney;
window.fmtMoneyShort = fmtMoneyShort;
window.fmtPercent = fmtPercent;
window.fmtDate = fmtDate;
window.fmtNumWithSign = fmtNumWithSign;
window.icons = icons;
window.setupLayout = setupLayout;
window.applyTranslations = applyTranslations;
window.setLanguage = setLanguage;
window.notify = notify;
window.renderEmpty = renderEmpty;

// ============ PROFILE FUNCTIONS ============
window.toggleProfileDropdown = function(e) {
  if (e) e.stopPropagation();
  const d = document.getElementById('profileDropdown');
  if (!d) return;
  d.style.display = d.style.display === 'none' ? 'block' : 'none';
};

// Tashqarini bossa yopish
document.addEventListener('click', function(e) {
  const d = document.getElementById('profileDropdown');
  const s = document.getElementById('profileSelector');
  if (d && d.style.display !== 'none' && s && !s.contains(e.target)) {
    d.style.display = 'none';
  }
});

window.filterProfiles = function(query) {
  const q = (query || '').toLowerCase().trim();
  document.querySelectorAll('.profile-item').forEach(item => {
    const text = item.getAttribute('data-search') || '';
    item.style.display = !q || text.includes(q) ? 'flex' : 'none';
  });
};

window.switchProfile = function(profileId) {
  const current = Storage.getActiveProfileId();
  if (profileId === current) {
    document.getElementById('profileDropdown').style.display = 'none';
    return;
  }
  const profile = Storage.getProfiles().find(p => p.id === profileId);
  if (!profile) return;

  if (confirm(`"${profile.name}" profiliga o'tasizmi?\n\nBarcha ma'lumotlar shu profilga moslashadi.`)) {
    Storage.setActiveProfile(profileId);
    notify(`✓ ${profile.name} faollashtirildi`, 'success');
    setTimeout(() => window.location.reload(), 600);
  }
};

window.deleteProfile = function(profileId) {
  const profile = Storage.getProfiles().find(p => p.id === profileId);
  if (!profile) return;

  if (!confirm(`"${profile.name}" profilini o'chirasizmi?\n\nBu profilning HAMMA ma'lumotlari (База, Tannarx, Sozlamalar) o'chadi va qaytarib bo'lmaydi.`)) return;
  if (!confirm(`ROSTAKAMMI?\n\n${profile.name}\nИНН: ${profile.inn || '—'}\nBrend: ${profile.brand || '—'}\n\nBarcha ma'lumotlar o'chadi!`)) return;

  try {
    Storage.removeProfile(profileId);
    notify('Profil o\'chirildi', 'warning');
    setTimeout(() => window.location.reload(), 600);
  } catch (err) {
    notify('Xato: ' + err.message, 'error');
  }
};

window.openAddProfileModal = function() {
  // Modal yaratish
  const modal = document.createElement('div');
  modal.id = 'addProfileModal';
  modal.style.cssText = `
    position: fixed; top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(4, 44, 83, 0.5); display: flex; align-items: center; justify-content: center;
    z-index: 999;
  `;
  modal.innerHTML = `
    <div style="background: white; padding: 24px; border-radius: 12px; max-width: 460px; width: 90%; max-height: 90vh; overflow-y: auto;">
      <h3 style="margin: 0 0 6px 0; color: var(--navy); font-size: 16px;">Добавить компанию</h3>
      <p style="margin: 0 0 16px 0; color: var(--text-tertiary); font-size: 12px;">Yangi IP/kompaniya qo'shing — har biriga alohida ma'lumotlar saqlanadi</p>

      <div style="margin-bottom: 10px;">
        <label class="form-label">Nomi *</label>
        <input type="text" id="newProfileName" class="form-input" placeholder="ИП Иванов И И" style="width: 100%;">
      </div>
      <div style="margin-bottom: 10px;">
        <label class="form-label">Brend *</label>
        <input type="text" id="newProfileBrand" class="form-input" placeholder="MyBrand" style="width: 100%;">
      </div>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px;">
        <div>
          <label class="form-label">ИНН</label>
          <input type="text" id="newProfileInn" class="form-input" placeholder="22701200..." style="width: 100%;">
        </div>
        <div>
          <label class="form-label">WB ID</label>
          <input type="text" id="newProfileWbId" class="form-input" placeholder="4068332" style="width: 100%;">
        </div>
      </div>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px;">
        <div>
          <label class="form-label">Mamlakat</label>
          <select id="newProfileCountry" class="form-input" style="width: 100%;">
            <option value="🇷🇺 RU">🇷🇺 RU</option>
            <option value="🇰🇬 KG">🇰🇬 KG</option>
            <option value="🇰🇿 KZ">🇰🇿 KZ</option>
            <option value="🇺🇿 UZ">🇺🇿 UZ</option>
            <option value="🇧🇾 BY">🇧🇾 BY</option>
          </select>
        </div>
        <div>
          <label class="form-label">Valyuta</label>
          <select id="newProfileCurrency" class="form-input" style="width: 100%;">
            <option value="₽">₽ rubl</option>
            <option value="KGS">KGS som</option>
            <option value="UZS">UZS sum</option>
            <option value="USD">USD $</option>
          </select>
        </div>
      </div>
      <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 10px; margin-bottom: 16px;">
        <div>
          <label class="form-label">Soliq turi</label>
          <select id="newProfileTaxType" class="form-input" style="width: 100%;">
            <option value="1">УСН-доходы (RU)</option>
            <option value="2">УСН Д-Р (RU)</option>
            <option value="3">Не считать</option>
            <option value="4">Считать от РС (KG)</option>
          </select>
        </div>
        <div>
          <label class="form-label">Stavka %</label>
          <input type="number" id="newProfileTaxRate" class="form-input" value="2" step="0.1" style="width: 100%;">
        </div>
      </div>

      <div style="display: flex; gap: 8px;">
        <button class="btn btn-primary" onclick="saveNewProfile()" style="flex: 1; padding: 10px;">💾 Yaratish</button>
        <button class="btn btn-outline" onclick="closeAddProfileModal()" style="flex: 1; padding: 10px;">Bekor</button>
      </div>
    </div>
  `;
  document.body.appendChild(modal);

  modal.addEventListener('click', e => {
    if (e.target === modal) closeAddProfileModal();
  });

  setTimeout(() => document.getElementById('newProfileName').focus(), 50);
};

window.closeAddProfileModal = function() {
  const m = document.getElementById('addProfileModal');
  if (m) m.remove();
};

window.saveNewProfile = function() {
  const name = document.getElementById('newProfileName').value.trim();
  const brand = document.getElementById('newProfileBrand').value.trim();
  if (!name || !brand) {
    alert('Nomi va Brend majburiy');
    return;
  }

  const taxTypeNames = { 1: 'УСН-доходы', 2: 'УСН Д-Р', 3: 'Не считать', 4: 'Считать от РС' };
  const taxType = parseInt(document.getElementById('newProfileTaxType').value);

  const newProfile = Storage.addProfile({
    name,
    brand,
    inn: document.getElementById('newProfileInn').value.trim(),
    wb_id: document.getElementById('newProfileWbId').value.trim(),
    country: document.getElementById('newProfileCountry').value,
    currency: document.getElementById('newProfileCurrency').value,
    tax_type: taxType,
    tax_type_name: taxTypeNames[taxType],
    tax_rate: parseFloat(document.getElementById('newProfileTaxRate').value) || 0
  });

  notify(`✓ "${name}" yaratildi`, 'success');
  closeAddProfileModal();

  if (confirm(`Yangi "${name}" profiliga darhol o'tasizmi?`)) {
    Storage.setActiveProfile(newProfile.id);
    setTimeout(() => window.location.reload(), 600);
  } else {
    setTimeout(() => window.location.reload(), 600);
  }
};
