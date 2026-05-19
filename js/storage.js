// ============================================
// AIRA Storage v2 — IndexedDB bilan (cheksiz hajm)
// ============================================

const DB_NAME = 'aira_db';
const DB_VERSION = 1;
const STORE_NAME = 'aira_data';

let _dbPromise = null;
function openDB() {
  if (_dbPromise) return _dbPromise;
  _dbPromise = new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onerror = () => reject(req.error);
    req.onsuccess = () => resolve(req.result);
    req.onupgradeneeded = (e) => {
      const db = e.target.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME);
      }
    };
  });
  return _dbPromise;
}

const _cache = {};
const _pendingWrites = new Set();

async function dbGet(key) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readonly');
    const req = tx.objectStore(STORE_NAME).get(key);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function dbSet(key, value) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite');
    const req = tx.objectStore(STORE_NAME).put(value, key);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
  });
}

async function dbDelete(key) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite');
    const req = tx.objectStore(STORE_NAME).delete(key);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
  });
}

async function initStorage() {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readonly');
    const store = tx.objectStore(STORE_NAME);
    const req = store.getAllKeys();
    req.onsuccess = async () => {
      const keys = req.result;
      for (const key of keys) {
        try {
          const val = await dbGet(key);
          _cache[key] = val;
        } catch (e) {}
      }
      resolve();
    };
    req.onerror = () => reject(req.error);
  });
}

const Storage = {
  KEYS: {
    LIST_REPORTS: 'aira_list_reports',
    BASE: 'aira_base',
    BASE_CALCULATED: 'aira_base_calculated',
    KPI_CACHE: 'aira_kpi_cache',
    CALC_VERSION: 'aira_calc_version',
    COSTS: 'aira_costs',
    STORAGE: 'aira_storage',
    SELF_PURCHASES: 'aira_self_purchases',
    EXT_EXPENSES: 'aira_ext_expenses',
    SETTINGS: 'aira_settings',
    LANG: 'aira_lang',
    UPLOAD_HISTORY: 'aira_uploads',
    // Kapitalizatsiya
    CAP_STOCK: 'aira_cap_stock',
    CAP_SALES: 'aira_cap_sales',
    CAP_NOMENCLATURE: 'aira_cap_nomenclature',
    CAP_PARAMS: 'aira_cap_params',
    // Ko'p profil
    PROFILES: 'aira_profiles',         // [{id, name, inn, brand, country, currency, tax_type, tax_rate}]
    ACTIVE_PROFILE: 'aira_active'       // active profile id
  },

  // ============ PROFILES (Ko'p IP) ============
  getProfiles() {
    let profiles = this.get(this.KEYS.PROFILES, null);
    if (!profiles || profiles.length === 0) {
      // Default profil yaratamiz (mavjud sozlamalardan)
      const settings = this.get(this.KEYS.SETTINGS, null) || {};
      const defaultProfile = {
        id: 'default',
        name: settings.ip_name || 'ИП Олимова Сарвинохон О К',
        inn: settings.inn || '',
        wb_id: settings.wb_id || '',
        brand: settings.brand || 'Piccino',
        country: settings.country || '🇰🇬 KG',
        currency: settings.currency || '₽',
        tax_type: settings.tax_type || 1,
        tax_type_name: settings.tax_type_name || 'УСН-доходы',
        tax_rate: settings.tax_rate || 2,
        created_at: new Date().toISOString()
      };
      profiles = [defaultProfile];
      this.set(this.KEYS.PROFILES, profiles);
      this.set(this.KEYS.ACTIVE_PROFILE, 'default');
    }
    return profiles;
  },

  getActiveProfileId() {
    let id = this.get(this.KEYS.ACTIVE_PROFILE, null);
    if (!id) {
      const profiles = this.getProfiles();
      id = profiles[0]?.id || 'default';
      this.set(this.KEYS.ACTIVE_PROFILE, id);
    }
    return id;
  },

  getActiveProfile() {
    const id = this.getActiveProfileId();
    const profiles = this.getProfiles();
    return profiles.find(p => p.id === id) || profiles[0];
  },

  setActiveProfile(profileId) {
    this.set(this.KEYS.ACTIVE_PROFILE, profileId);
    // Settings'ni profil sozlamalariga sinxronlash
    const profile = this.getProfiles().find(p => p.id === profileId);
    if (profile) {
      this.set(this.KEYS.SETTINGS, {
        ip_name: profile.name,
        inn: profile.inn,
        wb_id: profile.wb_id,
        brand: profile.brand,
        country: profile.country,
        currency: profile.currency,
        tax_type: profile.tax_type,
        tax_type_name: profile.tax_type_name,
        tax_rate: profile.tax_rate
      });
    }
    // Eslatma: cache invalidate kerak emas — har profilning o'z cache'i bor
  },

  addProfile(profile) {
    const profiles = this.getProfiles();
    const newProfile = {
      id: 'p_' + Date.now(),
      created_at: new Date().toISOString(),
      ...profile
    };
    profiles.push(newProfile);
    this.set(this.KEYS.PROFILES, profiles);
    return newProfile;
  },

  updateProfile(profileId, updates) {
    const profiles = this.getProfiles();
    const idx = profiles.findIndex(p => p.id === profileId);
    if (idx >= 0) {
      profiles[idx] = { ...profiles[idx], ...updates };
      this.set(this.KEYS.PROFILES, profiles);
      // Agar aktiv bo'lsa, settings ham yangilash
      if (profileId === this.getActiveProfileId()) {
        const profile = profiles[idx];
        this.set(this.KEYS.SETTINGS, {
          ip_name: profile.name, inn: profile.inn, wb_id: profile.wb_id,
          brand: profile.brand, country: profile.country, currency: profile.currency,
          tax_type: profile.tax_type, tax_type_name: profile.tax_type_name, tax_rate: profile.tax_rate
        });
      }
    }
  },

  removeProfile(profileId) {
    if (profileId === 'default') {
      throw new Error('Default profil o\'chirilmaydi');
    }
    let profiles = this.getProfiles().filter(p => p.id !== profileId);
    this.set(this.KEYS.PROFILES, profiles);

    // Profil ma'lumotlarini ham o'chirish (raw key bilan)
    const suffix = profileId === 'default' ? '' : `_${profileId}`;
    if (suffix) {
      this.remove(this.KEYS.BASE + suffix);
      this.remove(this.KEYS.LIST_REPORTS + suffix);
      this.remove(this.KEYS.COSTS + suffix);
      this.remove(this.KEYS.BASE_CALCULATED + suffix);
      this.remove(this.KEYS.KPI_CACHE + suffix);
      this.remove(this.KEYS.CALC_VERSION + suffix);
      this.remove(this.KEYS.UPLOAD_HISTORY + suffix);
    }

    // Agar aktiv profil o'chirilgan bo'lsa, default'ga o'tish
    if (this.getActiveProfileId() === profileId) {
      this.setActiveProfile('default');
    }
  },

  // ============ Profil-specific key helper ============
  // Ma'lumotlar har bir profil uchun alohida saqlanadi
  _profileKey(baseKey) {
    const profileId = this.getActiveProfileId();
    if (profileId === 'default') return baseKey;  // default: eski format saqlanadi (compatibility)
    return `${baseKey}_${profileId}`;
  },

  ready: false,
  async init() {
    try {
      await initStorage();
      this.ready = true;

      // Eski localStorage'dan migratsiya
      if (!_cache['_migrated_from_ls'] && typeof localStorage !== 'undefined') {
        let migrated = 0;
        for (const key of Object.values(this.KEYS)) {
          const lsVal = localStorage.getItem(key);
          if (lsVal !== null && _cache[key] === undefined) {
            try {
              _cache[key] = JSON.parse(lsVal);
              await dbSet(key, _cache[key]);
              migrated++;
            } catch (e) {}
          }
        }
        if (migrated > 0) {
          _cache['_migrated_from_ls'] = true;
          await dbSet('_migrated_from_ls', true);
          try {
            localStorage.removeItem(this.KEYS.BASE);
            console.log(`Migratsiya: ${migrated} kalit IndexedDB'ga ko'chirildi`);
          } catch (e) {}
        }
      }
    } catch (e) {
      console.error('Storage init xatosi:', e);
      this.ready = true;
    }
  },

  set(key, value) {
    _cache[key] = value;
    // Asinx yozish (xato bo'lmaydi)
    const writePromise = dbSet(key, value).catch(e => console.error('Set xatosi:', key, e));
    _pendingWrites.add(writePromise);
    writePromise.finally(() => _pendingWrites.delete(writePromise));
    return true;
  },

  get(key, defaultValue = null) {
    return _cache[key] !== undefined ? _cache[key] : defaultValue;
  },

  remove(key) {
    delete _cache[key];
    dbDelete(key).catch(e => console.error('Delete xatosi:', e));
  },

  // ============ Список отчётов ============
  getListReports() { return this.get(this._profileKey(this.KEYS.LIST_REPORTS), []); },

  addListReports(newList) {
    const existing = this.getListReports();
    const existingNums = new Set(existing.map(r => String(r.report_num)));
    const filtered = newList.filter(r => r.report_num && !existingNums.has(String(r.report_num)));
    const combined = [...existing, ...filtered];
    this.set(this._profileKey(this.KEYS.LIST_REPORTS), combined);
    return { added: filtered.length, skipped: newList.length - filtered.length, total: combined.length };
  },

  clearListReports() { this.set(this._profileKey(this.KEYS.LIST_REPORTS), []); },
  removeListReport(reportNum) {
    const arr = this.getListReports().filter(r => String(r.report_num) !== String(reportNum));
    this.set(this._profileKey(this.KEYS.LIST_REPORTS), arr);
  },
  getReport(reportNum) {
    return this.getListReports().find(r => String(r.report_num) === String(reportNum));
  },

  // ============ БАЗА ============
  getBase() { return this.get(this._profileKey(this.KEYS.BASE), []); },

  addBaseRows(rows, reportNum) {
    const existing = this.getBase();
    const existingSrids = new Set(
      existing.filter(r => String(r.report_num) === String(reportNum))
              .map(r => r.srid).filter(s => s)
    );
    const newRows = rows
      .filter(r => !r.srid || !existingSrids.has(r.srid))
      .map(r => ({ ...r, report_num: reportNum }));
    const combined = [...existing, ...newRows];
    this.set(this._profileKey(this.KEYS.BASE), combined);
    return { added: newRows.length, skipped: rows.length - newRows.length, total: combined.length };
  },

  getBaseByReport(reportNum) {
    return this.getBase().filter(r => String(r.report_num) === String(reportNum));
  },

  clearBase() { this.set(this._profileKey(this.KEYS.BASE), []); },

  removeBaseByReport(reportNum) {
    const arr = this.getBase().filter(r => String(r.report_num) !== String(reportNum));
    this.set(this._profileKey(this.KEYS.BASE), arr);
    this.invalidateCache(); // Cache yangilash kerak
  },

  // ============ CACHE ============
  // Hisoblangan qatorlarni saqlash (tez render uchun)
  getCalculatedBase() {
    return this.get(this._profileKey(this.KEYS.BASE_CALCULATED), null);
  },

  setCalculatedBase(rows) {
    this.set(this._profileKey(this.KEYS.BASE_CALCULATED), rows);
    // Cache versiyasini yangilash
    const settings = this.getSettings();
    const costsHash = JSON.stringify(this.getCosts().map(c => [c.code, c.cost]));
    this.set(this._profileKey(this.KEYS.CALC_VERSION), {
      timestamp: Date.now(),
      rowCount: rows.length,
      tax_type: settings.tax_type,
      tax_rate: settings.tax_rate,
      costsHash
    });
  },

  // Cache aktualligini tekshirish
  isCacheValid() {
    const version = this.get(this._profileKey(this.KEYS.CALC_VERSION));
    if (!version) return false;

    const settings = this.getSettings();
    if (version.tax_type !== settings.tax_type) return false;
    if (version.tax_rate !== settings.tax_rate) return false;

    // Tannarx o'zgargan bo'lsa qayta hisoblash
    const costsHash = JSON.stringify(this.getCosts().map(c => [c.code, c.cost]));
    if (version.costsHash !== costsHash) return false;

    // Baza qatorlari soni o'zgargan bo'lsa
    if (version.rowCount !== this.getBase().length) return false;

    return true;
  },

  invalidateCache() {
    this.remove(this._profileKey(this.KEYS.BASE_CALCULATED));
    this.remove(this._profileKey(this.KEYS.KPI_CACHE));
    this.remove(this._profileKey(this.KEYS.CALC_VERSION));
  },

  getKPICache() { return this.get(this._profileKey(this.KEYS.KPI_CACHE), null); },
  setKPICache(kpi) { this.set(this._profileKey(this.KEYS.KPI_CACHE), kpi); },

  // ============ Себестоимость ============
  getCosts() {
    let costs = this.get(this._profileKey(this.KEYS.COSTS), null);
    if (costs === null) {
      // Yangi profil — bo'sh boshlanadi. Foydalanuvchi o'z tovarlarini qo'shadi.
      costs = [];
      this.set(this._profileKey(this.KEYS.COSTS), costs);
    }
    return costs;
  },

  setCosts(costs) { this.set(this._profileKey(this.KEYS.COSTS), costs); },
  addCost(cost) { const arr = this.getCosts(); arr.push({ ...cost, id: Date.now() }); this.setCosts(arr); },
  updateCost(index, updates) { const arr = this.getCosts(); arr[index] = { ...arr[index], ...updates }; this.setCosts(arr); },
  removeCost(index) { const arr = this.getCosts(); arr.splice(index, 1); this.setCosts(arr); },

  findCost(reportNum, code) {
    const costs = this.getCosts();
    const primaryKey = String(reportNum) + String(code);
    let found = costs.find(c => (c.kluch || (c.supply_num + c.code)) === primaryKey);
    if (found) return found.cost || 0;
    found = costs.find(c => String(c.code) === String(code));
    return found ? (found.cost || 0) : 0;
  },

  // YANGI: barkod birinchi, kod fallback
  // row = { barcode, wb_article (code), ... }
  // qaytaradi: { cost, cost_future } yoki null
  findCostForRow(barcode, code) {
    const costs = this.getCosts();
    // 1. Barkod bo'yicha aniq qidirish (eng yaxshi)
    if (barcode) {
      const exact = costs.find(c => c.barcode && String(c.barcode) === String(barcode));
      if (exact) return { cost: exact.cost || 0, cost_future: exact.cost_future || exact.cost || 0, source: 'barcode' };
    }
    // 2. Kod bo'yicha fallback (eski tartib)
    if (code) {
      const byCode = costs.find(c => String(c.code) === String(code));
      if (byCode) return { cost: byCode.cost || 0, cost_future: byCode.cost_future || byCode.cost || 0, source: 'code' };
    }
    return null;
  },

  // ============ Boshqalar ============
  getStorageData() { return this.get(this._profileKey(this.KEYS.STORAGE), []); },
  setStorageData(arr) { this.set(this._profileKey(this.KEYS.STORAGE), arr); },
  addStorageData(rows) { const existing = this.getStorageData(); const combined = [...existing, ...rows]; this.setStorageData(combined); return combined.length; },
  clearStorage() { this.set(this._profileKey(this.KEYS.STORAGE), []); },

  getSelfPurchases() { return this.get(this._profileKey(this.KEYS.SELF_PURCHASES), []); },
  setSelfPurchases(arr) { this.set(this._profileKey(this.KEYS.SELF_PURCHASES), arr); },
  addSelfPurchase(sp) { const arr = this.getSelfPurchases(); arr.push({ ...sp, id: Date.now() }); this.set(this._profileKey(this.KEYS.SELF_PURCHASES), arr); },
  removeSelfPurchase(id) { const arr = this.getSelfPurchases().filter(s => s.id !== id); this.set(this._profileKey(this.KEYS.SELF_PURCHASES), arr); },

  getExtExpenses() { return this.get(this._profileKey(this.KEYS.EXT_EXPENSES), []); },
  setExtExpenses(arr) { this.set(this._profileKey(this.KEYS.EXT_EXPENSES), arr); },
  addExtExpense(e) { const arr = this.getExtExpenses(); arr.push({ ...e, id: Date.now() }); this.set(this._profileKey(this.KEYS.EXT_EXPENSES), arr); },
  removeExtExpense(id) { const arr = this.getExtExpenses().filter(s => s.id !== id); this.set(this._profileKey(this.KEYS.EXT_EXPENSES), arr); },

  getSettings() {
    return this.get(this.KEYS.SETTINGS, {
      ip_name: 'ИП Олимова Сарвинохон О К',
      brand: 'Piccino',
      country: '🇰🇬 KG',
      currency: '₽',
      tax_type: 1,
      tax_type_name: 'УСН-доходы',
      tax_rate: 2,
      inn: '',
      wb_id: ''
    });
  },
  setSettings(s) { this.set(this.KEYS.SETTINGS, s); },

  // ============ Kapitalizatsiya ma'lumotlari ============
  getCapStock() { return this.get(this._profileKey(this.KEYS.CAP_STOCK), []); },
  setCapStock(arr) { this.set(this._profileKey(this.KEYS.CAP_STOCK), arr); },
  clearCapStock() { this.set(this._profileKey(this.KEYS.CAP_STOCK), []); },

  getCapSales() { return this.get(this._profileKey(this.KEYS.CAP_SALES), []); },
  setCapSales(arr) { this.set(this._profileKey(this.KEYS.CAP_SALES), arr); },
  clearCapSales() { this.set(this._profileKey(this.KEYS.CAP_SALES), []); },

  getCapNomenclature() { return this.get(this._profileKey(this.KEYS.CAP_NOMENCLATURE), []); },
  setCapNomenclature(arr) { this.set(this._profileKey(this.KEYS.CAP_NOMENCLATURE), arr); },
  clearCapNomenclature() { this.set(this._profileKey(this.KEYS.CAP_NOMENCLATURE), []); },

  getCapParams() {
    return this.get(this._profileKey(this.KEYS.CAP_PARAMS), {
      days_of_sales: 7,
      delivery_days: 7,
      reserve_days: 7,
      delivery_cost: 0,
      selected_warehouse: 'Все склады',
      stock_uploaded_at: null,
      sales_uploaded_at: null,
      nomenclature_uploaded_at: null
    });
  },
  setCapParams(p) { this.set(this._profileKey(this.KEYS.CAP_PARAMS), p); },

  // ============ Yuklash tarixi ============
  getUploads() { return this.get(this._profileKey(this.KEYS.UPLOAD_HISTORY), []); },

  addUploadHistory(type, info) {
    const arr = this.getUploads();
    arr.unshift({
      id: Date.now() + Math.random(),
      type, // 'list' yoki 'detail'
      filename: info.filename || 'Noma\'lum fayl',
      reportNum: info.reportNum || null,
      dateFrom: info.dateFrom || null,
      dateTo: info.dateTo || null,
      rowCount: info.rowCount || 0,
      totalSum: info.totalSum || 0,
      uploadedAt: new Date().toISOString()
    });
    this.set(this._profileKey(this.KEYS.UPLOAD_HISTORY), arr);
    return arr[0];
  },

  removeUploadHistory(id) {
    const arr = this.getUploads().filter(u => u.id !== id);
    this.set(this._profileKey(this.KEYS.UPLOAD_HISTORY), arr);
  },

  clearUploadHistory() { this.set(this._profileKey(this.KEYS.UPLOAD_HISTORY), []); },

  getLang() { return this.get(this.KEYS.LANG, 'uz'); },
  setLang(l) { this.set(this.KEYS.LANG, l); },

  exportAll() {
    const data = {};
    for (const key of Object.values(this.KEYS)) data[key] = this.get(key);
    return data;
  },
  importAll(data) {
    for (const [key, value] of Object.entries(data)) {
      if (Object.values(this.KEYS).includes(key)) this.set(key, value);
    }
  },
  clearAll() {
    for (const key of Object.values(this.KEYS)) this.remove(key);
  },

  // Hajm hisobi
  async getStorageSize() {
    if ('storage' in navigator && 'estimate' in navigator.storage) {
      const est = await navigator.storage.estimate();
      return {
        used: est.usage,
        quota: est.quota,
        usedMB: (est.usage / 1024 / 1024).toFixed(2),
        quotaMB: (est.quota / 1024 / 1024).toFixed(0),
        percent: est.quota > 0 ? (est.usage / est.quota * 100).toFixed(2) : 0
      };
    }
    return null;
  }
};
