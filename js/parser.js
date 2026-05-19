// ============================================
// AIRA Parser — WB Excel/ZIP fayllarini o'qish
// Sizning Excel formulalaringizni JavaScript'da
// ============================================

const Parser = {

  // ============ KIRISH NUQTASI ============
  async parseFile(file) {
    const name = file.name.toLowerCase();
    if (name.endsWith('.zip')) return await this.parseZip(file);
    if (name.endsWith('.xlsx') || name.endsWith('.xls')) return await this.parseExcel(file);
    if (name.endsWith('.csv')) return await this.parseCsv(file);
    throw new Error('Qo\'llab-quvvatlanmagan fayl turi: ' + name);
  },

  // Список отчётов uchun alohida
  async parseListFile(file) {
    const name = file.name.toLowerCase();
    if (name.endsWith('.xlsx') || name.endsWith('.xls')) {
      const buf = await file.arrayBuffer();
      return this.parseListExcelBuffer(buf, file.name);
    }
    throw new Error('Список отчётов uchun Excel kerak');
  },

  // ============ ZIP ============
  async parseZip(file) {
    const zip = await JSZip.loadAsync(file);
    const results = [];
    const errors = [];

    for (const filename in zip.files) {
      const f = zip.files[filename];
      if (f.dir) continue;
      if (filename.startsWith('__MACOSX/') || filename.includes('/.DS_Store')) continue;

      const lower = filename.toLowerCase();
      try {
        if (lower.endsWith('.xlsx') || lower.endsWith('.xls')) {
          const buf = await f.async('arraybuffer');
          results.push(this.parseExcelBuffer(buf, filename));
        } else if (lower.endsWith('.csv')) {
          const text = await f.async('text');
          results.push(this.parseCsvText(text, filename));
        }
      } catch (e) {
        errors.push(filename + ': ' + e.message);
      }
    }

    if (results.length === 0) {
      throw new Error('ZIP ichida Excel topilmadi' + (errors.length ? '. Xatolar: ' + errors.join('; ') : ''));
    }

    const merged = this.mergeResults(results);
    if (errors.length) merged.info.warnings = errors;
    return merged;
  },

  // ============ Excel (Подробный отчёт) ============
  async parseExcel(file) {
    const buf = await file.arrayBuffer();
    return this.parseExcelBuffer(buf, file.name);
  },

  parseExcelBuffer(buffer, filename) {
    const wb = XLSX.read(buffer, { type: 'array', cellDates: true });
    const allRows = [];

    for (const sheetName of wb.SheetNames) {
      const sheet = wb.Sheets[sheetName];
      const rows = XLSX.utils.sheet_to_json(sheet, { header: 1, defval: '', raw: false, blankrows: false });

      const headerIdx = this.findHeaderRow(rows);
      if (headerIdx === -1) continue;

      const headers = rows[headerIdx].map(h => String(h || '').trim());
      const dataRows = rows.slice(headerIdx + 1);

      for (const row of dataRows) {
        if (!row || row.length === 0) continue;
        if (row.every(c => !c || String(c).trim() === '')) continue;

        const obj = {};
        for (let i = 0; i < headers.length; i++) {
          if (headers[i]) obj[headers[i]] = row[i];
        }
        if (Object.keys(obj).length) allRows.push(obj);
      }
    }

    return this.normalizeRows(allRows, filename);
  },

  // ============ CSV ============
  async parseCsv(file) {
    const text = await file.text();
    return this.parseCsvText(text, file.name);
  },

  parseCsvText(text, filename) {
    const firstLine = text.split('\n')[0] || '';
    const sep = firstLine.includes(';') ? ';' : ',';
    const lines = text.split(/\r?\n/).filter(l => l.trim());
    if (lines.length === 0) return { sales: [], info: { filename, rowCount: 0 } };

    const headers = this.parseCsvLine(lines[0], sep).map(h => h.trim());
    const rows = [];
    for (let i = 1; i < lines.length; i++) {
      const values = this.parseCsvLine(lines[i], sep);
      const obj = {};
      for (let j = 0; j < headers.length; j++) obj[headers[j]] = values[j] || '';
      rows.push(obj);
    }
    return this.normalizeRows(rows, filename);
  },

  parseCsvLine(line, sep) {
    const result = [];
    let cur = '', q = false;
    for (let i = 0; i < line.length; i++) {
      const c = line[i];
      if (c === '"') q = !q;
      else if (c === sep && !q) { result.push(cur); cur = ''; }
      else cur += c;
    }
    result.push(cur);
    return result;
  },

  findHeaderRow(rows) {
    const wbKeys = ['srid', 'артикул', 'тип документа', 'обоснование', 'дата продажи',
                    'кол-во', 'цена розничная', 'вайлдберриз', 'квв', 'продавцу',
                    'хранение', 'удержания', 'штраф', 'номер поставки'];
    let bestIdx = -1, bestScore = 0;
    for (let i = 0; i < Math.min(20, rows.length); i++) {
      const row = rows[i];
      if (!row || row.length < 3) continue;
      const text = row.join(' ').toLowerCase();
      const score = wbKeys.filter(k => text.includes(k)).length;
      if (score > bestScore) { bestScore = score; bestIdx = i; }
    }
    if (bestScore >= 2) return bestIdx;
    for (let i = 0; i < rows.length; i++) {
      if (rows[i] && rows[i].filter(c => c && String(c).trim()).length >= 3) return i;
    }
    return -1;
  },

  // ============ Подробный отчёт normalizatsiyasi ============
  // Sizning Excel'ingiz BA dan boshlanadigan WB ustunlariga moslashtirilgan
  normalizeRows(rows, filename) {
    if (!rows || rows.length === 0) {
      return { sales: [], info: { filename, rowCount: 0 } };
    }

    const allHeaders = new Set();
    for (let i = 0; i < Math.min(10, rows.length); i++) {
      Object.keys(rows[i]).forEach(h => allHeaders.add(h));
    }
    const headerMap = this.detectColumns(Array.from(allHeaders));

    const sales = [];
    for (const row of rows) {
      const sale = this.normalizeRow(row, headerMap);
      // Faqat mazmunli qatorlar
      if (sale && (sale.article || sale.srid || sale.commission || sale.logistics ||
                   sale.fine || sale.storage_fee || sale.price_with_discount)) {
        sales.push(sale);
      }
    }

    const dates = sales.map(s => s.sale_date || s.order_date).filter(d => d).sort();
    const dateFrom = dates[0] || '';
    const dateTo = dates[dates.length - 1] || '';

    // № отчёта ni fayl nomidan ajratib olish
    // Misol: "Еженедельный_детализированный_отчет__692179585_250016980_-_1.xlsx"
    let reportNum = '';
    const fnMatch = String(filename).match(/(\d{9,10})/);
    if (fnMatch) reportNum = fnMatch[1];

    const legalEntity = sales.find(s => s.legal_entity)?.legal_entity || '';

    return {
      sales,
      info: { filename, rowCount: sales.length, reportNum: reportNum || 'unknown', dateFrom, dateTo, legalEntity }
    };
  },

  normalizeRow(row, headerMap) {
    const sale = {};
    for (const [field, cols] of Object.entries(headerMap)) {
      for (const col of cols) {
        if (row[col] !== undefined && row[col] !== '' && row[col] !== null) {
          sale[field] = this.cleanValue(row[col], field);
          break;
        }
      }
    }
    return sale;
  },

  cleanValue(value, fieldType) {
    if (value === undefined || value === null) return null;
    const str = String(value).trim();
    if (str === '') return null;

    const numericFields = [
      'qty', 'qty_returns', 'qty_deliveries',
      'price', 'price_with_discount', 'revenue_wb',
      'discount', 'spp_percent', 'kvv_percent',
      'commission', 'commission_nds', 'commission_total',
      'logistics', 'logistics_returns', 'storage_fee',
      'acquiring', 'acquiring_percent',
      'deductions', 'reception_ops',
      'fine', 'wb_correction',
      'to_pay', 'comp_logistics',
      'cost', 'tax', 'rrc',
      'penalty_amount'
    ];

    if (numericFields.includes(fieldType)) {
      let cleaned = str.replace(/\s+/g, '').replace(/\u00a0/g, '').replace(',', '.');
      if (cleaned.startsWith('(') && cleaned.endsWith(')')) cleaned = '-' + cleaned.slice(1, -1);
      const num = parseFloat(cleaned);
      return isNaN(num) ? 0 : num;
    }

    if (['date', 'order_date', 'sale_date', 'fixation_start', 'fixation_end'].includes(fieldType)) {
      return this.parseDate(value);
    }

    return str;
  },

  parseDate(value) {
    if (!value) return null;
    if (value instanceof Date) return value.toISOString().substring(0, 10);
    const str = String(value).trim();
    if (!str) return null;

    let m = str.match(/^(\d{4})-(\d{1,2})-(\d{1,2})/);
    if (m) return `${m[1]}-${m[2].padStart(2,'0')}-${m[3].padStart(2,'0')}`;

    m = str.match(/^(\d{1,2})[.\/](\d{1,2})[.\/](\d{2,4})/);
    if (m) {
      let [_, d, mo, y] = m;
      if (y.length === 2) y = '20' + y;
      return `${y}-${mo.padStart(2,'0')}-${d.padStart(2,'0')}`;
    }
    return str;
  },

  // ============ WB Ustun nomlari aniqlash ============
  // Sizning Excel BA-CZ ustunlariga aynan moslashtirilgan
  detectColumns(headers) {
    const map = {
      // Identifikatorlar
      srid: [],                     // Srid
      supply_num: [],               // Номер поставки (Tovar partiyasi - WB ustun B)
      barcode: [],                  // Баркод (BI)

      // Tovar (BC-BI)
      subject: [],                  // BC
      brand: [],                    // BE
      article: [],                  // BF — Артикул поставщика
      wb_article: [],               // BD — Код номенклатуры
      product_name: [],             // BG
      size: [],                     // BH

      // Operatsiya (BJ-BK)
      operation_type: [],           // BJ
      operation_reason: [],         // BK

      // Sanalar (BL-BM)
      order_date: [],               // BL
      sale_date: [],                // BM

      // Soni va narx (BN-BT)
      qty: [],                      // BN
      price: [],                    // BO
      revenue_wb: [],               // BP
      product_discount: [],         // BQ
      promo_discount: [],           // BR
      total_discount: [],           // BS
      price_with_discount: [],      // BT

      // kVV (BU-BZ)
      kvv_decrease_rating: [],      // BU
      kvv_decrease_promo: [],       // BV
      spp_percent: [],              // BW
      kvv_percent: [],              // BX
      kvv_no_nds_basic: [],         // BY
      kvv_no_nds_final: [],         // BZ

      // Komissiya (CA-CH)
      commission_before_nds: [],    // CA
      pvz_compensation: [],         // CB
      acquiring: [],                // CC
      acquiring_percent: [],        // CD
      payment_type: [],             // CE
      commission: [],               // CF — Вознаграждение ВВ без НДС
      commission_nds: [],           // CG — НДС с Вознаграждения
      to_pay: [],                   // CH — Продавцу за реализованный

      // Logistika (CI-CN)
      qty_deliveries: [],           // CI
      qty_returns: [],              // CJ
      logistics: [],                // CK — Услуги по доставке
      fixation_start: [],           // CL
      fixation_end: [],             // CM
      paid_delivery: [],            // CN

      // Shtraflar (CO-CQ)
      fine: [],                     // CO — Общая сумма штрафов
      wb_correction: [],            // CP
      penalty_type: [],             // CQ — Виды логистики штрафов

      // Bank/Sklad
      bank_name: [],                // CS
      office_num: [],               // CT
      office_name: [],              // CU
      inn: [],                      // CV
      partner: [],                  // CW
      warehouse: [],                // CX
      country: [],                  // CY
      box_type: [],                 // CZ

      // Qo'shimcha (col105+)
      storage_fee: [],              // col112 — Хранение
      deductions: [],               // col113 — Удержания
      paid_reception: [],           // col114 — Платная приемка
      cart_id: [],                  // col123 — Id корзины
      loyalty_compensation: [],     // col120
      loyalty_participation: [],    // col121
      loyalty_points: [],           // col122

      // Yur. shaxs
      legal_entity: []
    };

    // WB Подробный отчёт aynan ustun nomlari
    const patterns = {
      srid: ['srid'],
      supply_num: ['номер поставки'],
      barcode: ['баркод', 'шк'],
      subject: ['предмет'],
      brand: ['бренд'],
      article: ['артикул поставщика', 'артикул продавца'],
      wb_article: ['код номенклатуры', 'артикул wb', 'nmid'],
      product_name: ['название'],
      size: ['__exact:размер'],
      operation_type: ['тип документа'],
      operation_reason: ['обоснование для оплаты'],
      order_date: ['дата заказа покупателем', 'дата заказа'],
      sale_date: ['дата продажи', 'дата операции'],
      qty: ['кол-во', '__exact:количество'],
      qty_deliveries: ['количество доставок'],
      qty_returns: ['количество возврата'],
      price: ['__exact:цена розничная'],
      revenue_wb: ['вайлдберриз реализовал товар', 'реализовал товар'],
      product_discount: ['согласованный продуктовый дисконт'],
      promo_discount: ['__exact:промокод, %', 'промокод %'],
      total_discount: ['итоговая согласованная скидка', 'согласованная скидка, %'],
      price_with_discount: ['с учетом согласованной скидки'],
      kvv_decrease_rating: ['снижения квв из-за рейтинга'],
      kvv_decrease_promo: ['снижения квв из-за акции', 'изменения квв из-за акции'],
      spp_percent: ['скидка постоянного покупателя', 'спп'],
      kvv_percent: ['__exact:размер квв, %'],
      kvv_no_nds_basic: ['размер квв без ндс', 'размер  квв без ндс'],
      kvv_no_nds_final: ['итоговый квв без ндс', 'итоговый квв'],
      commission_before_nds: ['вознаграждение с продаж до вычета'],
      pvz_compensation: ['возмещение за выдачу и возврат'],
      acquiring: ['эквайринг/комиссии', 'эквайринг/комиссия', 'компенсация платёжных услуг', 'компенсация платежных услуг'],
      acquiring_percent: ['размер комиссии за эквайринг', 'размер компенсации платёжных услуг', 'размер компенсации платежных услуг'],
      payment_type: ['тип платежа за эквайринг', 'тип платежа: компенсация'],
      commission: ['вознаграждение вайлдберриз (вв), без ндс', 'вайлдберриз (вв), без ндс'],
      commission_nds: ['ндс с вознаграждения'],
      to_pay: ['продавцу за реализованный', 'к перечислению продавцу'],
      logistics: ['услуги по доставке товара покупателю'],
      fixation_start: ['дата начала действия фиксации'],
      fixation_end: ['дата конца действия фиксации'],
      paid_delivery: ['признак услуги платной доставки'],
      fine: ['общая сумма штрафов'],
      wb_correction: ['корректировка вознаграждения вайлдберриз', 'корректировка вв'],
      penalty_type: ['виды логистики, штрафов'],
      bank_name: ['наименование банка-эквайера'],
      office_num: ['__exact:номер офиса'],
      office_name: ['наименование офиса доставки'],
      inn: ['инн партнера'],
      partner: ['__exact:партнер'],
      warehouse: ['__exact:склад'],
      country: ['__exact:страна'],
      box_type: ['тип коробов'],
      storage_fee: ['__exact:хранение', 'стоимость хранения'],
      deductions: ['__exact:удержания'],
      paid_reception: ['платная приемка', 'платная приёмка'],
      cart_id: ['id корзины заказа'],
      loyalty_compensation: ['компенсация скидки по программе лояльности'],
      loyalty_participation: ['стоимость участия в программе лояльности'],
      loyalty_points: ['сумма удержанная за начисленные баллы'],
      legal_entity: ['юридическое лицо', '__exact:продавец']
    };

    for (const header of headers) {
      const lower = String(header).toLowerCase().trim();
      if (!lower) continue;

      for (const [field, kws] of Object.entries(patterns)) {
        for (const kw of kws) {
          let matched = false;
          if (kw.startsWith('__exact:')) {
            if (lower === kw.slice(8)) matched = true;
          } else if (lower.includes(kw)) {
            matched = true;
          }
          if (matched) {
            if (!map[field].includes(header)) map[field].push(header);
            break;
          }
        }
      }
    }

    return map;
  },

  // ============ Список отчётов parser ============
  parseListExcelBuffer(buffer, filename) {
    const wb = XLSX.read(buffer, { type: 'array', cellDates: true });
    const allRows = [];

    for (const sheetName of wb.SheetNames) {
      const sheet = wb.Sheets[sheetName];
      const rows = XLSX.utils.sheet_to_json(sheet, { header: 1, defval: '', raw: false, blankrows: false });

      const headerIdx = this.findListHeaderRow(rows);
      if (headerIdx === -1) continue;

      const headers = rows[headerIdx].map(h => String(h || '').trim());
      const dataRows = rows.slice(headerIdx + 1);

      for (const row of dataRows) {
        if (!row || row.length === 0) continue;
        if (row.every(c => !c || String(c).trim() === '')) continue;

        const obj = {};
        for (let i = 0; i < headers.length; i++) {
          if (headers[i]) obj[headers[i]] = row[i];
        }
        if (Object.keys(obj).length) allRows.push(obj);
      }
    }

    return this.normalizeListRows(allRows, filename);
  },

  findListHeaderRow(rows) {
    const keys = ['№ отчёта', '№ отчета', 'номер отчёта', 'юридическое лицо',
                  'дата начала', 'дата формирования', 'тип отчёта', 'тип отчета',
                  'продажа', 'к перечислению', 'стоимость логистики'];
    let bestIdx = -1, bestScore = 0;
    for (let i = 0; i < Math.min(15, rows.length); i++) {
      const row = rows[i];
      if (!row || row.length < 3) continue;
      const text = row.join(' ').toLowerCase();
      const score = keys.filter(k => text.includes(k)).length;
      if (score > bestScore) { bestScore = score; bestIdx = i; }
    }
    if (bestScore >= 2) return bestIdx;
    for (let i = 0; i < rows.length; i++) {
      if (rows[i] && rows[i].filter(c => c && String(c).trim()).length >= 3) return i;
    }
    return -1;
  },

  normalizeListRows(rows, filename) {
    if (!rows || rows.length === 0) return { reports: [], info: { filename, count: 0 } };
    const reports = [];
    for (const row of rows) {
      const r = this.normalizeListRow(row);
      if (r && r.report_num) reports.push(r);
    }
    return { reports, info: { filename, count: reports.length } };
  },

  normalizeListRow(row) {
    const r = {};
    const num = (v) => {
      if (v === undefined || v === null || v === '') return 0;
      const str = String(v).replace(/\s+/g, '').replace(/\u00a0/g, '').replace(',', '.');
      const n = parseFloat(str);
      return isNaN(n) ? 0 : n;
    };
    const clean = (v) => v === undefined || v === null || v === '' ? null : String(v).trim();

    for (const [key, value] of Object.entries(row)) {
      const lower = String(key).toLowerCase().trim();

      if (lower.includes('№ отчёта') || lower.includes('№ отчета') || lower === '№') {
        r.report_num = String(clean(value) || '').replace(/\s+/g, '');
      } else if (lower.includes('юридическое лицо')) {
        r.legal_entity = clean(value);
      } else if (lower.includes('дата начала')) {
        r.date_from = this.parseDate(value);
      } else if (lower.includes('дата конца')) {
        r.date_to = this.parseDate(value);
      } else if (lower === 'период' || lower.includes('период')) {
        const m = String(value || '').match(/(\d{1,2}[.\/-]\d{1,2}[.\/-]\d{2,4}|\d{4}[.\/-]\d{1,2}[.\/-]\d{1,2}).*?(\d{1,2}[.\/-]\d{1,2}[.\/-]\d{2,4}|\d{4}[.\/-]\d{1,2}[.\/-]\d{1,2})/);
        if (m) {
          if (!r.date_from) r.date_from = this.parseDate(m[1]);
          if (!r.date_to) r.date_to = this.parseDate(m[2]);
        }
      } else if (lower.includes('дата формирования')) {
        r.created_at = this.parseDate(value);
      } else if (lower.includes('тип отчёта') || lower.includes('тип отчета')) {
        r.report_type = clean(value);
      } else if (lower === 'продажа' || (lower.startsWith('продажа') && !lower.includes('сумма'))) {
        r.sale_total = num(value);
      } else if (lower.includes('компенсация скидки')) {
        r.loyalty_compensation = num(value);
      } else if (lower.includes('к перечислению за товар') || lower.includes('к перечислению')) {
        r.to_pay = num(value);
      } else if (lower.includes('согласованная скидка')) {
        r.discount_percent = num(value);
      } else if (lower.includes('стоимость логистики')) {
        r.logistics_cost = num(value);
      } else if (lower.includes('стоимость хранения')) {
        r.storage_cost = num(value);
      } else if (lower.includes('стоимость платной приемки') || lower.includes('стоимость платной приёмки')) {
        r.paid_reception = num(value);
      } else if (lower.includes('прочие удержания') || lower.includes('удержания/выплаты')) {
        r.other_deductions = num(value);
      } else if (lower.includes('общая сумма штрафов') || (lower.includes('сумма штрафов') && !lower.includes('всего'))) {
        r.fines_total = num(value);
      } else if (lower.includes('корректировка вознаграждения') || lower.includes('корректировка вв')) {
        r.wb_correction = num(value);
      } else if (lower.includes('стоимость участия') || lower.includes('участия в программе лояльности')) {
        r.loyalty_participation = num(value);
      } else if (lower.includes('сумма удержанная за начисленные баллы') || lower.includes('сумма баллов')) {
        r.loyalty_points = num(value);
      } else if (lower.includes('итого к оплате') || lower.includes('итого к выплате')) {
        r.total_to_pay = num(value);
      }
    }
    return r;
  },

  // ============ Birlashtirish ============
  mergeResults(results) {
    const allSales = [];
    const filenames = [];
    let reportNum = '', legalEntity = '', dateFrom = '', dateTo = '';

    for (const r of results) {
      allSales.push(...r.sales);
      filenames.push(r.info.filename);
      if (r.info.reportNum && r.info.reportNum !== 'unknown') reportNum = r.info.reportNum;
      if (r.info.legalEntity) legalEntity = r.info.legalEntity;
      if (r.info.dateFrom && (!dateFrom || r.info.dateFrom < dateFrom)) dateFrom = r.info.dateFrom;
      if (r.info.dateTo && (!dateTo || r.info.dateTo > dateTo)) dateTo = r.info.dateTo;
    }

    return {
      sales: allSales,
      info: { filename: filenames.join(', '), rowCount: allSales.length,
              reportNum: reportNum || 'unknown', dateFrom, dateTo, legalEntity }
    };
  }
};
