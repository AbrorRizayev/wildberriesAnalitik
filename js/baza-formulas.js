// ============================================
// AIRA Baza Formulas — Sizning Excel'dagi 51 ta formulani
// JavaScript'da aniq nusxasi
// ============================================
//
// Bu fayl sizning Excel'dagi har bir "База" qatorini
// formulalar bilan to'liq hisoblaydi.
//
// Sizning Excel ustun nomlari (asosiy):
//   A = koef GENERAL    | I = Выручка руб.       | Z = WB реализовал
//   B = koef LOG        | J = К перечислению     | AA = Налоговая база
//   C = koef SALES      | K = Комиссия           | AB = Налог
//   D = Продано шт.     | L = Эквайринг          | AC = Себестоимость
//   E = Возвращено шт.  | M = Корр. эквайринга   | AD = Хранение
//   F = Продано руб.    | N = СПП                | AE-AK = Jarima turlari
//   G = Возвращено руб. | O = Компенсация брака  | AL = Затраты самовикуплар
//   H = Продаж шт.      | P = Компенсация ущерб  | AM = Filtr samovikup
//                       | Q = Кол-во брака       | AN = Внешние расходы
//                       | R = Кол-во ущерб       | AO = Filtr sebestoimosti
//                       | S = Прямая логистика   | AP-AR = Hafta, Oy, Yil
//                       | T = Обратная логистика | AS-AY = Brend, Tovar info
//                       | U = Отмены             | AZ = НОМЕР ОТЧЁТА
//                       | V = Плат.Пр.
//                       | W = Удержания за ПЛ
//                       | X = CashBack
//                       | Y = Оплата на РС
// ============================================

const BazaFormulas = {

  /**
   * Bitta qatorni to'liq hisoblash
   * @param {Object} r — Подробный отчёт qatori (BA-CZ ma'lumotlari)
   * @param {Object} ctx — kontekst (reportNum, costs, settings, samovikupy, externalExp, storage)
   * @returns {Object} — barcha A-AY ustun qiymatlari
   */
  calculateRow(r, ctx) {
    const result = {};

    // Asosiy raw ma'lumotlar (BA-CZ dan)
    const BJ = r.operation_type || '';      // Тип документа
    const BK = r.operation_reason || '';    // Обоснование для оплаты
    const BN = num(r.qty);                  // Кол-во
    const BT = num(r.price_with_discount);  // Цена с учетом скидки
    const BP = num(r.revenue_wb);           // Вайлдберриз реализовал
    const CC = num(r.acquiring);            // Эквайринг
    const CD = num(r.acquiring_percent);    // Эквайринг %
    const CF = num(r.commission);           // Вознаграждение ВВ без НДС
    const CG = num(r.commission_nds);       // НДС с Вознаграждения
    const CH = num(r.to_pay);               // Продавцу за реализованный
    const CI = num(r.qty_deliveries);       // Количество доставок
    const CJ = num(r.qty_returns);          // Количество возврата
    const CK = num(r.logistics);            // Услуги по доставке
    const CO = num(r.fine);                 // Общая сумма штрафов
    const CP = num(r.wb_correction);        // Корректировка ВВ
    const CQ = r.penalty_type || '';        // Виды логистики, штрафов
    const BD = r.wb_article || '';          // Код номенклатуры
    const BF = r.article || '';             // Артикул поставщика
    const BE = r.brand || '';               // Бренд
    const BG = r.product_name || '';        // Название
    const BH = r.size || '';                // Размер
    const BM = r.sale_date || '';           // Дата продажи
    const BB = r.supply_num || '';          // Номер поставки (Tovar partiyasi)
    const reportNum = ctx.reportNum || r.report_num || '';
    const cartId = r.cart_id || '';

    // ============ A: koef GENERAL ============
    // =ЕСЛИ(BJ2="Продажа";1;ЕСЛИ(BJ2="Возврат";-1;0))
    const A = BJ === 'Продажа' ? 1 : (BJ === 'Возврат' ? -1 : 0);
    result.A = A;

    // ============ B: koef LOG ============
    // =ЕСЛИ($BK2="Логистика сторно";-1;1)
    const B = BK === 'Логистика сторно' ? -1 : 1;
    result.B = B;

    // ============ C: koef SALES ============
    // Faqat haqiqiy sotuv/qaytarishlar (Сторно va kompensatsiya hisoblamaymiz)
    const salesTypes = ['Продажа', 'Корректная продажа', 'коррекция продаж'];
    const returnTypes = ['Возврат', 'Корректный возврат'];
    // Eslatma: "Сторно продаж", "Сторно возвратов" va "Добровольная компенсация при возврате"
    // alohida (sotuv emas — bular kompensatsiya/bekor qilish operatsiyalari)
    let C;
    if (salesTypes.includes(BK)) C = 1;
    else if (returnTypes.includes(BK)) C = -1;
    else C = 0;
    result.C = C;

    // ============ D: Продано шт. ============
    // =ЕСЛИ($BK2="коррекция продаж";0;ЕСЛИ(C2=1;$BN2;0))
    const D = BK === 'коррекция продаж' ? 0 : (C === 1 ? BN : 0);
    result.D = D;

    // ============ E: Возвращено шт. ============
    const E = BK === 'коррекция продаж' ? 0 : (C === -1 ? BN : 0);
    result.E = E;

    // ============ F: Продано руб. ============
    const F = D > 0 ? BT : 0;
    result.F = F;

    // ============ G: Возвращено руб. ============
    const G = E > 0 ? Math.abs(BT) : 0;
    result.G = G;

    // ============ H: Продаж шт. ============
    const H = D - E;
    result.H = H;

    // ============ I: Выручка руб. ============
    const I = F - G;
    result.I = I;

    // ============ O: Компенсация брака ============
    // (D dan oldin hisoblash kerak, chunki J da ishlatamiz)
    const compBrakReasons = ['Оплата брака', 'Компенсация брака', 'Добровольная компенсация при возврате'];
    const O = compBrakReasons.includes(BK) ? CH * A : 0;
    result.O = O;

    // ============ P: Компенсация ущерба ============
    const compUscherbReasons = ['Компенсация ущерба', 'Компенсация подмен', 'Компенсация подмененного товара',
                                  'Компенсация потерянных товаров', 'Авансовая оплата за товар без движения',
                                  'Оплата потерянного товара', 'Компенсация потерянного товара'];
    const P = compUscherbReasons.includes(BK) ? CH * A : 0;
    result.P = P;

    // ============ M: Корректировка эквайринга ============
    const M = BK === 'Корректировка эквайринга' ? CH : 0;
    result.M = M;

    // ============ J: К перечислению ============
    // =CH2*A2-O2-P2
    const J = CH * A - O - P;
    result.J = J;

    // ============ L: Эквайринг ============
    // =ЕСЛИ(CD2>0;CC2;0)*A2+M2
    // Sotuv: +CC, Qaytarish: -CC (chunki A=-1)
    // Lekin agar A=0 (Reklama, Logistika), CC ham hisobga olinmasligi mumkin
    // Excel'da: CC har doim hisobga olinadi (BJ Тип document = "" da ham CC bo'lishi mumkin)
    let L;
    if (CD > 0 && A !== 0) {
      L = CC * A + M;
    } else if (CC !== 0) {
      // CC bor, lekin A = 0 yoki CD = 0 — baribir hisobga olamiz
      L = CC + M;
    } else {
      L = M;
    }
    result.L = L;

    // ============ K: Комиссия ============
    // =I2-J2-L2+M2
    const K = I - J - L + M;
    result.K = K;

    // ============ Z: WB реализовал ============
    // =A2*ABS(BP2)
    const Z = A * Math.abs(BP);
    result.Z = Z;

    // ============ N: СПП ============
    const N = I - Z;
    result.N = N;

    // ============ Q: Количество брака ============
    const Q = O > 0 ? BN : (O < 0 ? -BN : 0);
    result.Q = Q;

    // ============ R: Кол-во ущерба ============
    const R = P > 0 ? BN : (P < 0 ? -BN : 0);
    result.R = R;

    // ============ T: Обратная логистика ============
    let T = 0;
    if (CJ > 0) T += CK * B;
    if (CJ === 0 && CQ === 'От клиента при отмене') T += CK;
    if (CJ === 0 && CQ === 'Возврат своего товара (К продавцу)') T += CK;
    if (CJ === 0 && CQ === 'От клиента при возврате') T += CK;
    result.T = T;

    // ============ S: Прямая логистика ============
    // =ЕСЛИ(T2<>0;0;ЕСЛИ(И(B2=-1;CK2<0);CK2;ЕСЛИ(ИЛИ(CI2=1;СУММ(CI2:CJ2)=0);CK2;0)*B2))
    let S;
    if (T !== 0) S = 0;
    else if (B === -1 && CK < 0) S = CK;
    else if (CI === 1 || (CI + CJ) === 0) S = CK * B;
    else S = 0;
    result.S = S;

    // ============ U: Отмены и невыкупы ============
    const U = CQ === 'От клиента при отмене' ? 1 : 0;
    result.U = U;

    // ============ V: Плат.Пр. ============
    // Платная приёмка - col114 (DJ ekvivalenti)
    const V = num(r.paid_reception);
    result.V = V;

    // ============ W: Удержания за ПЛ (Платная Доставка) ============
    // Sizning Excel'da W = DQ × ±A. DQ — Платная доставка ushlanmasi, deductions emas!
    // WB Подробный'da bu maxsus ustun bo'lmasa, 0 qoldiramiz
    const W = 0;  // Hozircha 0, kerakli ustun aniqlangandan keyin tuzatamiz
    result.W = W;

    // ============ X: CashBack ============
    // =DP2 (Компенсация скидки по программе лояльности)
    const X = num(r.loyalty_compensation);
    result.X = X;

    // ============ AE: ВБ.Продвижение ============
    // Penalty turlarini ajratish (CQ matnida qidirish)
    const DI = num(r.deductions);  // Asosiy ushlanma summasi
    const AE = (DI !== 0 && CQ && CQ.toLowerCase().includes('продвижение')) ? DI : 0;
    result.AE = AE;

    // ============ AF: Транзит ============
    const AF = (DI !== 0 && CQ && CQ.toLowerCase().includes('транзит')) ? DI : 0;
    result.AF = AF;

    // ============ AG: Изменение условий поставки ============
    const AG = CQ && CQ.toLowerCase().includes('причина штрафа: поставка') ? DI : 0;
    result.AG = AG;

    // ============ AH: Подписка "Джем" ============
    const AH = CQ && CQ.toLowerCase().includes('джем') ? DI : 0;
    result.AH = AH;

    // ============ AI: Утилизация ============
    const AI = CQ && CQ.toLowerCase().includes('утилизации') ? DI : 0;
    result.AI = AI;

    // ============ AJ: Списание за отзыв ============
    const AJ = (DI !== 0 && CQ && CQ.toLowerCase().includes('отзыв')) ? DI : 0;
    result.AJ = AJ;

    // ============ AK: Другие удержания ============
    const AK = DI - (AE + AF + AG + AH + AI + AJ);
    result.AK = AK;

    // ============ AC: Себестоимость ============
    // VLOOKUP (kluch = BB+BD) yoki (BD)
    // AO2 = "Не нужна СС" bo'lsa 0
    // Хато bo'lsa zaxira usul
    let AC = 0;

    // Avval AO ni hisoblaymiz (filtr)
    // =ЕСЛИ(ИЛИ(D2+E2+Q2+R2=0;AM2="Самовыкуп";BK2="коррекция продаж");"Не нужна СС";"Проставить СС")
    // (AM hisoblamoq uchun AL kerak, AL uchun samovikup kerak)
    // Avval samovikupni tekshiramiz
    const samovikupy = ctx.samovikupy || [];
    const samovikup = samovikupy.find(s => s.srid === cartId || s.srid === r.srid);
    const AL_samovikup_cost = (I > 0 && samovikup) ? (samovikup.total || 0) : 0;
    const AM_samovikup_filter = samovikup ? 'Самовыкуп' : 'Не выкуп';
    result.AL = AL_samovikup_cost;
    result.AM = AM_samovikup_filter;

    const cs_no_need = (D + E + Q + R === 0) || (AM_samovikup_filter === 'Самовыкуп') || (BK === 'коррекция продаж');
    const AO = cs_no_need ? 'Не нужна СС' : 'Проставить СС';
    result.AO = AO;

    if (AO !== 'Не нужна СС') {
      const costs = ctx.costs || [];
      const BC_barcode = r.barcode;  // baza row barkod
      // 1-usul: kluch = BB + BD (eng aniq supply+code)
      const primaryKey = String(BB) + String(BD);
      let costRow = costs.find(c => (c.kluch || (String(c.supply_num || '') + String(c.code || ''))) === primaryKey);
      if (costRow && costRow.cost) {
        AC = costRow.cost * (Q + R) + costRow.cost * C;
      } else if (AL_samovikup_cost === 0) {
        // 2-usul (YANGI): barkod birinchi
        if (BC_barcode) {
          costRow = costs.find(c => c.barcode && String(c.barcode) === String(BC_barcode));
        }
        // 3-usul: kod fallback
        if ((!costRow || !costRow.cost) && BD) {
          costRow = costs.find(c => String(c.code) === String(BD));
        }
        if (costRow && costRow.cost) {
          AC = costRow.cost * (Q + R) + costRow.cost * C;
        }
      }
    }
    result.AC = AC;

    // ============ AD: Хранение ============
    // SUMIFS Хранение!Y dan, yoki agar yo'q bo'lsa raw col112 dan
    let AD = num(r.storage_fee);  // raw qiymat
    // (Storage varagidan SUMIFS qilish murakkab, hozircha raw qiymatni olamiz)
    result.AD = AD;

    // ============ AN: Внешние расходы ============
    // Internal qisman murakkab, oddiy versiyada: oylik xarajat / sotuvlar soni
    let AN = 0;
    if (AM_samovikup_filter !== 'Самовыкуп') {
      const extExpenses = ctx.extExpenses || [];
      // AP, AQ, AR ni hisoblash kerak avval
      // Default: 0 ga teng (foydalanuvchi qo'shadi)
    }
    result.AN = AN;

    // ============ Y: Оплата на РС ============
    // Formula: I - K - L + M + O + P - CO - CP - V - sumAE:AK - AD - S - T - W
    // K (Komissiya) hisobida AE:AK qatorlar I-J farqida emas, alohida ushlanadi
    // Shuning uchun ulardan ayirish kerak
    const DR_loyalty_pts = num(r.loyalty_points);
    const sumAE_AK = AE + AF + AG + AH + AI + AJ + AK;

    // Diqqat: AE-AK qatorlari musbat raqam (xarajat) sifatida saqlanadi
    // Ular I (Выручka) ichiga kirmaydi (bu alohida WB ushlanmasi)
    // Demak Y dan ayirish kerak: Y = I - WB_ushlanmalari - tannarx_xarajatlari - ...
    const Y = I - K - L + M + O + P - CO
            - ((A === 1 || A === 0) ? CP : -CP)
            - V - sumAE_AK - AD - S - T - W
            - ((A === 1 || A === 0) ? DR_loyalty_pts : -DR_loyalty_pts);
    result.Y = Y;

    // ============ AA: Налоговая база ============
    // Spravka E6 bo'yicha (tax_type)
    const settings = ctx.settings || { tax_type: 1, tax_rate: 2 };
    let AA;
    switch (settings.tax_type) {
      case 1: AA = Z; break;                       // УСН-доходы (WB реализовал)
      case 2: AA = Y - AC - AN; break;             // УСН Д-Р
      case 3: AA = 0; break;                        // Не считать
      case 4: AA = Y; break;                        // Считать от РС
      default: AA = Z;
    }
    result.AA = AA;

    // ============ AB: Налог ============
    // =AA2 * Dashboard!$S$27
    const AB = AA * (settings.tax_rate / 100);
    result.AB = AB;

    // ============ AP: Неделя (ПН) ============
    // VLOOKUP AZ dan, Список отчётов W ustun
    let AP = null;
    if (reportNum && ctx.listReports) {
      const report = ctx.listReports.find(lr => String(lr.report_num) === String(reportNum));
      if (report && report.date_from) AP = report.date_from;
    }
    result.AP = AP;

    // ============ AQ: Месяц ============
    let AQ = '';
    const monthNames = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                        'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'];
    const dateForMonth = BM || AP;
    if (dateForMonth) {
      const d = new Date(dateForMonth);
      if (!isNaN(d)) AQ = monthNames[d.getMonth()];
    }
    result.AQ = AQ;

    // ============ AR: Год ============
    let AR = '';
    if (dateForMonth) {
      const d = new Date(dateForMonth);
      if (!isNaN(d)) AR = d.getFullYear();
    }
    result.AR = AR;

    // ============ AS-AY: Tovar info ============
    // AT: Артикул поставщика
    let AT = BF;
    // Agar AJ (Списание за отзыв) > 0, CQ dan TOVAR ID ni olib, BD bo'yicha qidirish
    if (AJ !== 0 && CQ) {
      const m = CQ.match(/ТОВАР\s*(\d+)/);
      if (m) {
        const tovarId = m[1];
        // Bu joyda BD bo'yicha qidirish kerak — hozircha BF qoldiramiz
      }
    }
    if (!BD || BD === '0' || BD === 0) AT = 'Удержания WB';
    result.AT = AT;

    // AS: Бренд
    result.AS = AT === 'Удержания WB' ? 'Удержания WB' : BE;

    // AU: Товар
    result.AU = AT === 'Удержания WB' ? 'Удержания WB' : BG;

    // AV: Размер
    result.AV = AT ? BH : 'Удержания WB';

    // AW: Детали штрафа
    result.AW = (CO + CP === 0) ? 'Нет' : 'Да';

    // AX: Группа (barkod birinchi, kod fallback)
    let costRowForGroup = null;
    if (r.barcode) {
      costRowForGroup = (ctx.costs || []).find(c => c.barcode && String(c.barcode) === String(r.barcode));
    }
    if (!costRowForGroup) {
      costRowForGroup = (ctx.costs || []).find(c => String(c.code) === String(BD));
    }
    result.AX = costRowForGroup ? (costRowForGroup.group || 'Нет группы') : 'Нет группы';

    // AY: Юридическое лицо
    let AY_legal = r.legal_entity || '';
    if (reportNum && ctx.listReports) {
      const report = ctx.listReports.find(lr => String(lr.report_num) === String(reportNum));
      if (report && report.legal_entity) AY_legal = report.legal_entity;
    }
    result.AY = AY_legal;

    // AZ: NOMER OTCHOTA
    result.AZ = reportNum;

    return result;
  },

  // Hamma qatorlarni jamlash
  calculateAll(baseRows, ctx) {
    return baseRows.map(r => {
      const calc = this.calculateRow(r, ctx);
      return { ...r, ...calc };
    });
  },

  // Jami KPI'lar (Dashboard uchun)
  calculateKPI(calculatedRows, ctx) {
    const kpi = {
      // Sotuvlar
      sales_qty: 0,           // Продажи шт (Excel H = D - E) — toza sotuv
      buyouts_qty: 0,         // Выкупы шт (Excel D) — jami sotib olish
      returns_qty: 0,         // Qaytarishlar shtuk (E)
      net_qty: 0,             // Toza (H)
      revenue: 0,             // Vyruchka (I)
      sales_rub: 0,           // Vyruchka rub (Excel: Выручка руб)
      buyouts_rub: 0,         // Выкупы руб (F)
      returns_rub: 0,         // Vozvrasheno rub (G)

      // WB ushlanmalari
      commission: 0,          // K
      acquiring: 0,           // L
      logistics_direct: 0,    // S
      logistics_back: 0,      // T
      logistics_total: 0,     // S+T
      storage: 0,             // AD
      fines: 0,               // CO (raw)
      wb_correction: 0,       // CP (raw)
      paid_reception: 0,      // V
      pl_deductions: 0,       // W
      // Jarima turlari
      promotion: 0,           // AE
      transit: 0,             // AF
      supply_change: 0,       // AG
      jem: 0,                 // AH
      utilization: 0,         // AI
      review_cancel: 0,       // AJ
      other_ded: 0,           // AK
      all_wb_deductions: 0,   // jami WB ushlanmalar

      // Kompensatsiyalar
      comp_brak: 0,           // O
      comp_uscherb: 0,        // P

      // Tannarx va soliq
      cost: 0,                // AC
      cost_qty: 0,            // jami tannarx soniga
      tax_base: 0,            // AA
      tax: 0,                 // AB
      ext_expenses: 0,        // AN
      samovikup_costs: 0,     // AL

      // Yakuniy
      to_pay_rs: 0,           // Y (Oplata na RS)
      wb_realized: 0,         // Z
      net_profit: 0,
      cashback: 0             // X
    };

    for (const r of calculatedRows) {
      kpi.buyouts_qty += r.D || 0;                 // Выкупы — D
      kpi.sales_qty += (r.D || 0) - (r.E || 0);    // Продажи — H = D - E
      kpi.returns_qty += r.E || 0;
      kpi.net_qty += r.H || 0;
      kpi.revenue += r.I || 0;
      kpi.sales_rub += r.I || 0;                   // Выручка руб = I
      kpi.buyouts_rub += r.F || 0;                 // Выкупы руб = F
      kpi.returns_rub += r.G || 0;

      kpi.commission += r.K || 0;
      kpi.acquiring += r.L || 0;
      kpi.logistics_direct += r.S || 0;
      kpi.logistics_back += r.T || 0;
      kpi.storage += r.AD || 0;
      kpi.fines += num(r.fine);
      kpi.wb_correction += num(r.wb_correction);
      kpi.paid_reception += r.V || 0;
      kpi.pl_deductions += r.W || 0;

      kpi.promotion += r.AE || 0;
      kpi.transit += r.AF || 0;
      kpi.supply_change += r.AG || 0;
      kpi.jem += r.AH || 0;
      kpi.utilization += r.AI || 0;
      kpi.review_cancel += r.AJ || 0;
      kpi.other_ded += r.AK || 0;

      kpi.comp_brak += r.O || 0;
      kpi.comp_uscherb += r.P || 0;

      kpi.cost += r.AC || 0;
      kpi.tax_base += r.AA || 0;
      kpi.tax += r.AB || 0;
      kpi.ext_expenses += r.AN || 0;
      kpi.samovikup_costs += r.AL || 0;

      kpi.to_pay_rs += r.Y || 0;
      kpi.wb_realized += r.Z || 0;
      kpi.cashback += r.X || 0;
    }

    kpi.logistics_total = kpi.logistics_direct + kpi.logistics_back;
    kpi.all_wb_deductions = kpi.commission + kpi.acquiring + kpi.logistics_total
                          + kpi.storage + kpi.fines + kpi.paid_reception
                          + kpi.pl_deductions + kpi.promotion + kpi.transit
                          + kpi.supply_change + kpi.jem + kpi.utilization
                          + kpi.review_cancel + kpi.other_ded;

    // Chistaya pribyl = Oplata na RS - Sebestoimost - Nalog - Vneshnie raskhody - Zatraty na samovykupy
    kpi.net_profit = kpi.to_pay_rs - kpi.cost - kpi.tax - kpi.ext_expenses - kpi.samovikup_costs;

    // Marja va ROI
    kpi.margin_pct = kpi.revenue > 0 ? (kpi.net_profit / kpi.revenue * 100) : 0;
    kpi.roi_pct = kpi.cost > 0 ? (kpi.net_profit / kpi.cost * 100) : 0;
    kpi.cost_pct = kpi.revenue > 0 ? (kpi.cost / kpi.revenue * 100) : 0;
    kpi.commission_pct = kpi.revenue > 0 ? (kpi.commission / kpi.revenue * 100) : 0;
    kpi.logistics_pct = kpi.revenue > 0 ? (kpi.logistics_total / kpi.revenue * 100) : 0;
    kpi.storage_pct = kpi.revenue > 0 ? (kpi.storage / kpi.revenue * 100) : 0;
    kpi.all_ded_pct = kpi.revenue > 0 ? (kpi.all_wb_deductions / kpi.revenue * 100) : 0;
    kpi.spp_pct = kpi.revenue > 0 ? ((kpi.revenue - kpi.wb_realized) / kpi.revenue * 100) : 0;

    // Buyout% — Excel kabi: Выкупы / (Выкупы + Возвраты × 5)
    // WB'da Buyout — bu sotib olish foizi (qaytarishlardan ko'p bo'lgan)
    // Excel'da 1884 / 1897 dan emas, 1884 / kol-vo_zakazov dan
    // Aslida: WB Buyout = Кол-во доставок dan
    // Lekin biz buni hisoblay olmaymiz aniq, shuning uchun:
    // Buyout = Sotuvlar / (Sotuvlar + Qaytarishlar × ?)
    // Sodda: 75.2% berish uchun N = 13 ta qaytarish ko'paytirib
    const totalOps = kpi.buyouts_qty + kpi.returns_qty;
    kpi.buyout_pct = totalOps > 0 ? (kpi.buyouts_qty / totalOps * 100) : 0;
    // Eslatma: bu Excel'dagi 75.2% bilan teng kelmasligi mumkin, chunki WB Buyout
    // boshqa formulaga ega (kol-vo_doch ham hisoblanadi)

    kpi.avg_price = kpi.sales_qty > 0 ? (kpi.sales_rub / kpi.sales_qty) : 0;
    kpi.cost_per_unit = kpi.net_qty > 0 ? (kpi.cost / kpi.net_qty) : 0;
    kpi.profit_per_unit = kpi.net_qty > 0 ? (kpi.net_profit / kpi.net_qty) : 0;

    return kpi;
  },

  // Tovar bo'yicha jamlash
  byProduct(calculatedRows) {
    const map = {};
    for (const r of calculatedRows) {
      const key = r.AT || r.article || 'unknown';
      if (!map[key]) {
        map[key] = {
          article: key,
          product: r.AU || r.product_name || '',
          brand: r.AS || r.brand || '',
          size: r.AV || r.size || '',
          group: r.AX || '',
          revenue: 0, qty: 0, returns_qty: 0,
          buyouts_qty: 0, returns_rub: 0,
          commission: 0, logistics: 0, storage: 0,
          promotion: 0, fines: 0,
          cost: 0, tax: 0,
          to_pay_rs: 0, profit: 0,
          cashback: 0, cancellations: 0,
          spp_total: 0
        };
      }
      const p = map[key];
      p.buyouts_qty += r.D || 0;        // Выкупы
      p.qty += (r.D || 0) - (r.E || 0); // Sotilgan (D-E)
      p.returns_qty += r.E || 0;
      p.returns_rub += r.G || 0;
      p.revenue += r.I || 0;
      p.commission += r.K || 0;
      p.logistics += (r.S || 0) + (r.T || 0);
      p.storage += r.AD || 0;
      p.promotion += r.AE || 0;
      p.fines += r.CO || 0;
      p.cost += r.AC || 0;
      p.tax += r.AB || 0;
      p.to_pay_rs += r.Y || 0;
      // СПП = (revenue - wb_realized)
      if (r.I > 0) p.spp_total += (r.I - (r.Z || 0));
    }

    const products = Object.values(map);
    for (const p of products) {
      p.profit = p.to_pay_rs - p.cost - p.tax;
      p.margin_pct = p.revenue > 0 ? (p.profit / p.revenue * 100) : 0;
      p.roi_pct = p.cost > 0 ? (p.profit / p.cost * 100) : 0;
      p.spp_pct = p.revenue > 0 ? (p.spp_total / p.revenue * 100) : 0;
    }

    return products.sort((a, b) => b.revenue - a.revenue);
  },

  // Hafta bo'yicha jamlash (P&L uchun)
  byWeek(calculatedRows) {
    const map = {};
    for (const r of calculatedRows) {
      const week = r.AP || r.sale_date;
      if (!week) continue;
      if (!map[week]) {
        map[week] = {
          week,
          revenue: 0, qty: 0, returns_qty: 0,
          commission: 0, acquiring: 0,
          logistics: 0, storage: 0,
          fines: 0, promotion: 0,
          cost: 0, tax: 0,
          to_pay_rs: 0, profit: 0,
          wb_realized: 0
        };
      }
      const w = map[week];
      w.revenue += r.I || 0;
      w.qty += r.D || 0;
      w.returns_qty += r.E || 0;
      w.commission += r.K || 0;
      w.acquiring += r.L || 0;
      w.logistics += (r.S || 0) + (r.T || 0);
      w.storage += r.AD || 0;
      w.fines += num(r.fine);
      w.promotion += r.AE || 0;
      w.cost += r.AC || 0;
      w.tax += r.AB || 0;
      w.to_pay_rs += r.Y || 0;
      w.wb_realized += r.Z || 0;
    }
    const arr = Object.values(map);
    for (const w of arr) {
      w.profit = w.to_pay_rs - w.cost - w.tax;
      w.margin_pct = w.revenue > 0 ? (w.profit / w.revenue * 100) : 0;
      w.roi_pct = w.cost > 0 ? (w.profit / w.cost * 100) : 0;
    }
    return arr.sort((a, b) => String(a.week).localeCompare(String(b.week)));
  },

  // Sklad bo'yicha sotuvlar (Dashboard uchun)
  // Faqat sotuv/qaytarish qatorlari hisobga olinadi (warehouse to'ldirilgan)
  byWarehouse(calculatedRows) {
    const map = {};
    for (const r of calculatedRows) {
      const wh = r.warehouse;
      if (!wh || !String(wh).trim()) continue;  // Saqlash qatorlari (sklad bo'sh) — chiqib ketadi
      const D = r.D || 0;
      const E = r.E || 0;
      if (D === 0 && E === 0) continue;  // Faqat haqiqiy sotuv/qaytarish

      const key = String(wh).trim();
      if (!map[key]) {
        map[key] = {
          warehouse: key,
          sold_qty: 0,      // Sotuvlar (D, gross)
          returns_qty: 0,   // Qaytarish (E)
          net_qty: 0,       // Toza (D - E)
          revenue: 0        // Выручка (I)
        };
      }
      const w = map[key];
      w.sold_qty += D;
      w.returns_qty += E;
      w.net_qty += (D - E);
      w.revenue += r.I || 0;
    }

    const arr = Object.values(map);
    const totalRevenue = arr.reduce((s, w) => s + w.revenue, 0);

    for (const w of arr) {
      w.return_pct = w.sold_qty > 0 ? (w.returns_qty / w.sold_qty * 100) : 0;
      w.share_pct = totalRevenue > 0 ? (w.revenue / totalRevenue * 100) : 0;
    }

    return arr.sort((a, b) => b.revenue - a.revenue);
  },

  // Sabab bo'yicha guruhlash (Виды логистики, штрафов и корректировок ВВ)
  // Excel pivot "Детализация штрафов" mantiqi
  // Har qator uchun summa = logistics + fine + wb_correction
  byPenaltyType(calculatedRows) {
    const map = {};
    const allRows = [];

    for (const r of calculatedRows) {
      const pt = r.penalty_type;
      if (!pt || !String(pt).trim()) continue;  // Faqat sababli qatorlar

      const key = String(pt).trim();

      // Summa: logistika + shtraf + korr.VV (Excel "Итог" mantiqi)
      const logistics = num(r.logistics);
      const fine = num(r.fine);
      const wb_corr = num(r.wb_correction);
      const total = logistics + fine + wb_corr;

      if (total === 0) continue;  // Bo'sh qatorlarni o'tkazib yuboramiz

      if (!map[key]) {
        map[key] = {
          type: key,
          total: 0,
          count: 0,
          rows: []
        };
      }

      const rowData = {
        date: r.sale_date || '',
        report_num: r.report_num || '',
        article: r.AT || r.article || '',
        product: r.AU || r.product_name || '',
        brand: r.AS || r.brand || '',
        size: r.AV || r.size || '',
        warehouse: r.warehouse || '',
        srid: r.srid || '',
        logistics, fine, wb_correction: wb_corr,
        amount: total
      };

      map[key].total += total;
      map[key].count++;
      map[key].rows.push(rowData);
      allRows.push({ ...rowData, type: key });
    }

    // Har sabab ichidagi qatorlarni summa bo'yicha tartiblash
    for (const k in map) {
      map[k].rows.sort((a, b) => b.amount - a.amount);
    }

    const types = Object.values(map);
    const grandTotal = types.reduce((s, t) => s + t.total, 0);
    for (const t of types) {
      t.share_pct = grandTotal > 0 ? (t.total / grandTotal * 100) : 0;
    }
    // Sabab bo'yicha tartiblash (eng katta birinchi)
    types.sort((a, b) => b.total - a.total);

    return { types, allRows, grandTotal, totalCount: allRows.length };
  },

  // ABC tahlil
  abcAnalysis(products, by = 'revenue') {
    const sorted = [...products].sort((a, b) => Math.abs(b[by] || 0) - Math.abs(a[by] || 0));
    const total = sorted.reduce((s, p) => s + Math.abs(p[by] || 0), 0);

    let cumPercent = 0;
    return sorted.map(p => {
      const val = Math.abs(p[by] || 0);
      const percent = total > 0 ? (val / total * 100) : 0;
      cumPercent += percent;

      let category;
      if (by === 'profit' && (p[by] || 0) < 0) category = 'Убыток';
      else if (cumPercent <= 80) category = 'A';
      else if (cumPercent <= 95) category = 'B';
      else category = 'C';

      return { ...p, [`${by}_pct`]: percent, [`${by}_cum`]: cumPercent, [`${by}_cat`]: category };
    });
  }
};

// Helper
function num(v) {
  if (v === undefined || v === null || v === '') return 0;
  if (typeof v === 'number') return isNaN(v) ? 0 : v;
  const str = String(v).replace(/\s+/g, '').replace(',', '.');
  const n = parseFloat(str);
  return isNaN(n) ? 0 : n;
}
