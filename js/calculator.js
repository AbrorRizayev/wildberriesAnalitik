// ============================================
// AIRA Calculator — Cache va optimallashtirish
// ============================================
// Bazani BIR MARTA hisoblab, IndexedDB'ga saqlaydi
// Settings yoki ma'lumotlar o'zgarsa, qayta hisoblanadi
// ============================================

const Calculator = {

  // Cache versiyasi — settings yoki tannarx o'zgarsa yangilanishi kerak
  getCacheVersion() {
    const settings = Storage.getSettings();
    const costs = Storage.getCosts();
    const baseLen = Storage.getBase().length;

    // Versiya: settings hash + costs hash + base length
    const settingsKey = `${settings.tax_type}_${settings.tax_rate}`;
    const costsKey = costs.map(c => `${c.code}:${c.cost}`).join(',');
    const costsHash = this.simpleHash(costsKey);

    return `v3_${settingsKey}_${costsHash}_${baseLen}`;
  },

  simpleHash(str) {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      hash = ((hash << 5) - hash) + str.charCodeAt(i);
      hash = hash & hash;
    }
    return hash.toString(36);
  },

  // Cache mavjudligini tekshirish
  isCacheValid() {
    const cached = Storage.get(Storage.KEYS.CALC_VERSION);
    const current = this.getCacheVersion();
    return cached === current;
  },

  // Asosiy funksiya — hisoblash yoki cache'dan olish
  async getCalculated(onProgress) {
    // Cache valid bo'lsa, undan olish (TEZ)
    if (this.isCacheValid()) {
      const cached = Storage.get(Storage.KEYS.BASE_CALCULATED);
      if (cached && cached.length > 0) {
        return cached;
      }
    }

    // Cache yo'q yoki eski - qayta hisoblash
    return await this.recalculateAll(onProgress);
  },

  // Hammasini qayta hisoblash
  async recalculateAll(onProgress) {
    const base = Storage.getBase();
    if (base.length === 0) return [];

    const ctx = {
      costs: Storage.getCosts(),
      settings: Storage.getSettings(),
      samovikupy: Storage.getSelfPurchases(),
      extExpenses: Storage.getExtExpenses(),
      listReports: Storage.getListReports()
    };

    const total = base.length;
    const result = new Array(total);
    const BATCH_SIZE = 1000;

    // Batchma-batch hisoblash (UI freeze bo'lmasin)
    for (let i = 0; i < total; i += BATCH_SIZE) {
      const end = Math.min(i + BATCH_SIZE, total);

      for (let j = i; j < end; j++) {
        const r = base[j];
        const calc = BazaFormulas.calculateRow(r, { ...ctx, reportNum: r.report_num });
        result[j] = { ...r, ...calc };
      }

      // Progress callback
      if (onProgress) {
        onProgress(end, total, Math.round(end / total * 100));
      }

      // Brauzer'ga nafas olish bering (UI freeze bo'lmasin)
      if (end < total) {
        await new Promise(resolve => setTimeout(resolve, 0));
      }
    }

    // Cache'ga saqlash
    Storage.set(Storage.KEYS.BASE_CALCULATED, result);
    Storage.set(Storage.KEYS.CALC_VERSION, this.getCacheVersion());

    // KPI'ni ham cache qilamiz
    const kpi = BazaFormulas.calculateKPI(result, ctx);
    Storage.set(Storage.KEYS.KPI_CACHE, kpi);

    return result;
  },

  // KPI olish (cache bilan)
  async getKPI(onProgress) {
    if (this.isCacheValid()) {
      const cached = Storage.get(Storage.KEYS.KPI_CACHE);
      if (cached) return cached;
    }
    const calculated = await this.getCalculated(onProgress);
    const ctx = {
      costs: Storage.getCosts(),
      settings: Storage.getSettings(),
      samovikupy: Storage.getSelfPurchases(),
      extExpenses: Storage.getExtExpenses(),
      listReports: Storage.getListReports()
    };
    return BazaFormulas.calculateKPI(calculated, ctx);
  },

  // Cache'ni o'chirish (foydalanuvchi tugmasi bilan)
  invalidate() {
    Storage.remove(Storage.KEYS.BASE_CALCULATED);
    Storage.remove(Storage.KEYS.KPI_CACHE);
    Storage.remove(Storage.KEYS.CALC_VERSION);
  },

  // Progress modal ko'rsatish
  showProgress() {
    const existing = document.getElementById('calc-progress');
    if (existing) return existing;

    const modal = document.createElement('div');
    modal.id = 'calc-progress';
    modal.style.cssText = `
      position: fixed; top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(4, 44, 83, 0.85);
      display: flex; align-items: center; justify-content: center;
      z-index: 9999;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    `;
    modal.innerHTML = `
      <div style="background: white; padding: 24px 32px; border-radius: 12px; max-width: 400px; text-align: center; box-shadow: 0 20px 60px rgba(0,0,0,0.3);">
        <div style="width: 60px; height: 60px; margin: 0 auto 16px; background: linear-gradient(135deg, #185FA5, #042C53); border-radius: 14px; display: flex; align-items: center; justify-content: center; color: white; font-weight: 700; font-size: 14px;">AIRA</div>
        <h3 style="font-size: 16px; font-weight: 600; color: #042C53; margin-bottom: 8px;">Hisoblanmoqda...</h3>
        <div id="calc-progress-text" style="font-size: 13px; color: #4A5568; margin-bottom: 14px;">Boshlanyapti...</div>
        <div style="height: 8px; background: #EDF2F7; border-radius: 4px; overflow: hidden; margin-bottom: 10px;">
          <div id="calc-progress-bar" style="height: 100%; background: linear-gradient(90deg, #185FA5, #0F6E56); width: 0%; transition: width 0.3s;"></div>
        </div>
        <div id="calc-progress-pct" style="font-size: 11px; color: #718096;">0%</div>
      </div>
    `;
    document.body.appendChild(modal);
    return modal;
  },

  hideProgress() {
    const modal = document.getElementById('calc-progress');
    if (modal) {
      modal.style.opacity = '0';
      modal.style.transition = 'opacity 0.3s';
      setTimeout(() => modal.remove(), 300);
    }
  },

  updateProgress(current, total, pct) {
    const txt = document.getElementById('calc-progress-text');
    const bar = document.getElementById('calc-progress-bar');
    const pctEl = document.getElementById('calc-progress-pct');
    if (txt) txt.textContent = `${fmt(current)} / ${fmt(total)} qator hisoblandi`;
    if (bar) bar.style.width = pct + '%';
    if (pctEl) pctEl.textContent = pct + '%';
  }
};

// Helper agar fmt yo'q bo'lsa
if (typeof fmt === 'undefined') {
  window.fmt = function(n) {
    return new Intl.NumberFormat('ru-RU').format(Math.round(n));
  };
}
