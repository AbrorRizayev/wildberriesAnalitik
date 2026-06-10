"""Exact Python port of js/baza-formulas.js — calculate_row().

IMPORTANT: this mirrors the original JavaScript line-by-line on purpose. The JS
calculations were verified correct against the user's Excel, so every condition,
operator and edge case here is kept identical. Do NOT "improve" the logic —
changing behaviour means diverging from the proven Excel results.

Each block keeps the original Excel column letter (A..AZ) and the WB raw column
codes (BJ, BK, BN, ...) as comments, matching baza-formulas.js exactly.
"""


def num(v):
    """Port of the num() helper in baza-formulas.js."""
    if v is None or v == '':
        return 0
    if isinstance(v, bool):
        return 0  # JS treats booleans oddly; raw data never has booleans here
    if isinstance(v, (int, float)):
        try:
            if v != v:  # NaN
                return 0
        except Exception:
            return 0
        return v
    s = str(v).replace(' ', '').replace(' ', '').replace(',', '.')
    try:
        return float(s)
    except (ValueError, TypeError):
        return 0


def _month_from_iso(date_str):
    """Return (month_index 0-11, year) from an ISO-ish date string, or (None, None)."""
    if not date_str:
        return None, None
    s = str(date_str)
    # Expect YYYY-MM-DD (parser.parse_date normalises to this).
    parts = s[:10].split('-')
    if len(parts) >= 3:
        try:
            return int(parts[1]) - 1, int(parts[0])
        except ValueError:
            return None, None
    return None, None


MONTH_NAMES = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
               'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']


def calculate_row(r, ctx):
    """Exact port of BazaFormulas.calculateRow(r, ctx).

    r: normalized WB row dict (parser output).
    ctx: dict with keys reportNum, costs, settings, samovikupy, extExpenses, listReports.
    Returns a dict keyed by the Excel column letters (A..AZ).
    """
    result = {}

    # Asosiy raw ma'lumotlar (BA-CZ dan)
    BJ = r.get('operation_type') or ''       # Тип документа
    BK = r.get('operation_reason') or ''     # Обоснование для оплаты
    BN = num(r.get('qty'))                    # Кол-во
    BT = num(r.get('price_with_discount'))    # Цена с учетом скидки
    BP = num(r.get('revenue_wb'))             # Вайлдберриз реализовал
    CC = num(r.get('acquiring'))              # Эквайринг
    CD = num(r.get('acquiring_percent'))      # Эквайринг %
    CF = num(r.get('commission'))             # Вознаграждение ВВ без НДС
    CG = num(r.get('commission_nds'))         # НДС с Вознаграждения
    CH = num(r.get('to_pay'))                 # Продавцу за реализованный
    CI = num(r.get('qty_deliveries'))         # Количество доставок
    CJ = num(r.get('qty_returns'))            # Количество возврата
    CK = num(r.get('logistics'))              # Услуги по доставке
    CO = num(r.get('fine'))                   # Общая сумма штрафов
    CP = num(r.get('wb_correction'))          # Корректировка ВВ
    CQ = r.get('penalty_type') or ''          # Виды логистики, штрафов
    BD = r.get('wb_article') or ''            # Код номенклатуры
    BF = r.get('article') or ''               # Артикул поставщика
    BE = r.get('brand') or ''                 # Бренд
    BG = r.get('product_name') or ''          # Название
    BH = r.get('size') or ''                  # Размер
    BM = r.get('sale_date') or ''             # Дата продажи
    BB = r.get('supply_num') or ''            # Номер поставки
    reportNum = ctx.get('reportNum') or r.get('report_num') or ''
    cartId = r.get('cart_id') or ''

    # ============ A: koef GENERAL ============
    A = 1 if BJ == 'Продажа' else (-1 if BJ == 'Возврат' else 0)
    result['A'] = A

    # ============ B: koef LOG ============
    B = -1 if BK == 'Логистика сторно' else 1
    result['B'] = B

    # ============ C: koef SALES ============
    salesTypes = ['Продажа', 'Корректная продажа', 'коррекция продаж']
    returnTypes = ['Возврат', 'Корректный возврат']
    if BK in salesTypes:
        C = 1
    elif BK in returnTypes:
        C = -1
    else:
        C = 0
    result['C'] = C

    # ============ D: Продано шт. ============
    D = 0 if BK == 'коррекция продаж' else (BN if C == 1 else 0)
    result['D'] = D

    # ============ E: Возвращено шт. ============
    E = 0 if BK == 'коррекция продаж' else (BN if C == -1 else 0)
    result['E'] = E

    # ============ F: Продано руб. ============
    F = BT if D > 0 else 0
    result['F'] = F

    # ============ G: Возвращено руб. ============
    G = abs(BT) if E > 0 else 0
    result['G'] = G

    # ============ H: Продаж шт. ============
    H = D - E
    result['H'] = H

    # ============ I: Выручка руб. ============
    I = F - G
    result['I'] = I

    # ============ O: Компенсация брака ============
    compBrakReasons = ['Оплата брака', 'Компенсация брака', 'Добровольная компенсация при возврате']
    O = CH * A if BK in compBrakReasons else 0
    result['O'] = O

    # ============ P: Компенсация ущерба ============
    compUscherbReasons = ['Компенсация ущерба', 'Компенсация подмен', 'Компенсация подмененного товара',
                          'Компенсация потерянных товаров', 'Авансовая оплата за товар без движения',
                          'Оплата потерянного товара', 'Компенсация потерянного товара']
    P = CH * A if BK in compUscherbReasons else 0
    result['P'] = P

    # ============ M: Корректировка эквайринга ============
    M = CH if BK == 'Корректировка эквайринга' else 0
    result['M'] = M

    # ============ J: К перечислению ============
    J = CH * A - O - P
    result['J'] = J

    # ============ L: Эквайринг ============
    if CD > 0 and A != 0:
        L = CC * A + M
    elif CC != 0:
        L = CC + M
    else:
        L = M
    result['L'] = L

    # ============ K: Комиссия ============
    K = I - J - L + M
    result['K'] = K

    # ============ Z: WB реализовал ============
    Z = A * abs(BP)
    result['Z'] = Z

    # ============ N: СПП ============
    N = I - Z
    result['N'] = N

    # ============ Q: Количество брака ============
    Q = BN if O > 0 else (-BN if O < 0 else 0)
    result['Q'] = Q

    # ============ R: Кол-во ущерба ============
    R = BN if P > 0 else (-BN if P < 0 else 0)
    result['R'] = R

    # ============ T: Обратная логистика ============
    T = 0
    if CJ > 0:
        T += CK * B
    if CJ == 0 and CQ == 'От клиента при отмене':
        T += CK
    if CJ == 0 and CQ == 'Возврат своего товара (К продавцу)':
        T += CK
    if CJ == 0 and CQ == 'От клиента при возврате':
        T += CK
    result['T'] = T

    # ============ S: Прямая логистика ============
    if T != 0:
        S = 0
    elif B == -1 and CK < 0:
        S = CK
    elif CI == 1 or (CI + CJ) == 0:
        S = CK * B
    else:
        S = 0
    result['S'] = S

    # ============ U: Отмены и невыкупы ============
    U = 1 if CQ == 'От клиента при отмене' else 0
    result['U'] = U

    # ============ V: Плат.Пр. ============
    V = num(r.get('paid_reception'))
    result['V'] = V

    # ============ W: Удержания за ПЛ ============
    W = 0
    result['W'] = W

    # ============ X: CashBack ============
    X = num(r.get('loyalty_compensation'))
    result['X'] = X

    # ============ AE: ВБ.Продвижение ============
    DI = num(r.get('deductions'))
    AE = DI if (DI != 0 and CQ and 'продвижение' in CQ.lower()) else 0
    result['AE'] = AE

    # ============ AF: Транзит ============
    AF = DI if (DI != 0 and CQ and 'транзит' in CQ.lower()) else 0
    result['AF'] = AF

    # ============ AG: Изменение условий поставки ============
    AG = DI if (CQ and 'причина штрафа: поставка' in CQ.lower()) else 0
    result['AG'] = AG

    # ============ AH: Подписка "Джем" ============
    AH = DI if (CQ and 'джем' in CQ.lower()) else 0
    result['AH'] = AH

    # ============ AI: Утилизация ============
    AI = DI if (CQ and 'утилизации' in CQ.lower()) else 0
    result['AI'] = AI

    # ============ AJ: Списание за отзыв ============
    AJ = DI if (DI != 0 and CQ and 'отзыв' in CQ.lower()) else 0
    result['AJ'] = AJ

    # ============ AK: Другие удержания ============
    AK = DI - (AE + AF + AG + AH + AI + AJ)
    result['AK'] = AK

    # ============ AC: Себестоимость (AL/AM/AO avval) ============
    AC = 0

    samovikupy = ctx.get('samovikupy') or []
    samovikup = None
    for s in samovikupy:
        if s.get('srid') == cartId or s.get('srid') == r.get('srid'):
            samovikup = s
            break
    AL_samovikup_cost = (samovikup.get('total') or 0) if (I > 0 and samovikup) else 0
    AM_samovikup_filter = 'Самовыкуп' if samovikup else 'Не выкуп'
    result['AL'] = AL_samovikup_cost
    result['AM'] = AM_samovikup_filter

    cs_no_need = (D + E + Q + R == 0) or (AM_samovikup_filter == 'Самовыкуп') or (BK == 'коррекция продаж')
    AO = 'Не нужна СС' if cs_no_need else 'Проставить СС'
    result['AO'] = AO

    if AO != 'Не нужна СС':
        costs = ctx.get('costs') or []
        BC_barcode = r.get('barcode')
        primaryKey = str(BB) + str(BD)
        costRow = None
        for c in costs:
            key = c.get('kluch') or (str(c.get('supply_num') or '') + str(c.get('code') or ''))
            if key == primaryKey:
                costRow = c
                break
        if costRow and costRow.get('cost'):
            AC = costRow['cost'] * (Q + R) + costRow['cost'] * C
        elif AL_samovikup_cost == 0:
            costRow = None
            if BC_barcode:
                for c in costs:
                    if c.get('barcode') and str(c['barcode']) == str(BC_barcode):
                        costRow = c
                        break
            if (not costRow or not costRow.get('cost')) and BD:
                for c in costs:
                    if str(c.get('code')) == str(BD):
                        costRow = c
                        break
            if costRow and costRow.get('cost'):
                AC = costRow['cost'] * (Q + R) + costRow['cost'] * C
    result['AC'] = AC

    # ============ AD: Хранение ============
    AD = num(r.get('storage_fee'))
    result['AD'] = AD

    # ============ AN: Внешние расходы ============
    AN = 0
    result['AN'] = AN

    # ============ Y: Оплата на РС ============
    DR_loyalty_pts = num(r.get('loyalty_points'))
    sumAE_AK = AE + AF + AG + AH + AI + AJ + AK
    Y = (I - K - L + M + O + P - CO
         - (CP if (A == 1 or A == 0) else -CP)
         - V - sumAE_AK - AD - S - T - W
         - (DR_loyalty_pts if (A == 1 or A == 0) else -DR_loyalty_pts))
    result['Y'] = Y

    # ============ AA: Налоговая база ============
    s_settings = ctx.get('settings') or {'tax_type': 1, 'tax_rate': 2}
    tax_type = s_settings.get('tax_type', 1)
    if tax_type == 1:
        AA = Z
    elif tax_type == 2:
        AA = Y - AC - AN
    elif tax_type == 3:
        AA = 0
    elif tax_type == 4:
        AA = Y
    else:
        AA = Z
    result['AA'] = AA

    # ============ AB: Налог ============
    AB = AA * (s_settings.get('tax_rate', 2) / 100)
    result['AB'] = AB

    # ============ AP: Неделя (ПН) ============
    AP = None
    listReports = ctx.get('listReports')
    if reportNum and listReports:
        for lr in listReports:
            if str(lr.get('report_num')) == str(reportNum):
                if lr.get('date_from'):
                    AP = lr['date_from']
                break
    result['AP'] = AP

    # ============ AQ: Месяц ============
    AQ = ''
    dateForMonth = BM or AP
    mi, yr = _month_from_iso(dateForMonth)
    if mi is not None:
        AQ = MONTH_NAMES[mi]
    result['AQ'] = AQ

    # ============ AR: Год ============
    AR = ''
    if yr is not None:
        AR = yr
    result['AR'] = AR

    # ============ AS-AY: Tovar info ============
    AT = BF
    if AJ != 0 and CQ:
        # Original: tries to extract ТОВАР id then no-op. Kept faithful (no-op).
        pass
    if (not BD) or BD == '0' or BD == 0:
        AT = 'Удержания WB'
    result['AT'] = AT

    result['AS'] = 'Удержания WB' if AT == 'Удержания WB' else BE
    result['AU'] = 'Удержания WB' if AT == 'Удержания WB' else BG
    result['AV'] = BH if AT else 'Удержания WB'
    result['AW'] = 'Нет' if (CO + CP == 0) else 'Да'

    # AX: Группа (barkod birinchi, kod fallback)
    costs = ctx.get('costs') or []
    costRowForGroup = None
    if r.get('barcode'):
        for c in costs:
            if c.get('barcode') and str(c['barcode']) == str(r['barcode']):
                costRowForGroup = c
                break
    if not costRowForGroup:
        for c in costs:
            if str(c.get('code')) == str(BD):
                costRowForGroup = c
                break
    result['AX'] = (costRowForGroup.get('group') or 'Нет группы') if costRowForGroup else 'Нет группы'

    # AY: Юридическое лицо
    AY_legal = r.get('legal_entity') or ''
    if reportNum and listReports:
        for lr in listReports:
            if str(lr.get('report_num')) == str(reportNum):
                if lr.get('legal_entity'):
                    AY_legal = lr['legal_entity']
                break
    result['AY'] = AY_legal

    # AZ: NOMER OTCHOTA
    result['AZ'] = reportNum

    return result