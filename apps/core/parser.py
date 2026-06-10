"""Exact Python port of js/parser.js — WB Excel/ZIP/CSV reading + column detection.

Like formulas.py, this mirrors the original JavaScript faithfully: the WB column
auto-detection patterns, the meaningful-row filter and the value cleaning all match
parser.js exactly, because that logic was verified against real WB reports.

Reading uses python-calamine (fast, low memory). Files are read from a path or a
file-like object; the caller is responsible for deleting any temp file afterwards
(uploaded Excel files are never stored permanently).
"""
import datetime
import io
import re
import zipfile

from python_calamine import CalamineWorkbook

NUMERIC_FIELDS = {
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
    'penalty_amount',
}

DATE_FIELDS = {'date', 'order_date', 'sale_date', 'fixation_start', 'fixation_end'}


# ============ Value cleaning ============
def clean_value(value, field_type):
    if value is None:
        return None
    if isinstance(value, (datetime.date, datetime.datetime)) and field_type in DATE_FIELDS:
        return parse_date(value)
    s = str(value).strip()
    if s == '':
        return None

    if field_type in NUMERIC_FIELDS:
        cleaned = re.sub(r'\s+', '', s).replace(' ', '').replace(',', '.')
        if cleaned.startswith('(') and cleaned.endswith(')'):
            cleaned = '-' + cleaned[1:-1]
        try:
            return float(cleaned)
        except (ValueError, TypeError):
            return 0

    if field_type in DATE_FIELDS:
        return parse_date(value)

    return s


def parse_date(value):
    if not value and value != 0:
        return None
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.strftime('%Y-%m-%d')
    s = str(value).strip()
    if not s:
        return None

    m = re.match(r'^(\d{4})-(\d{1,2})-(\d{1,2})', s)
    if m:
        return f'{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}'

    m = re.match(r'^(\d{1,2})[./](\d{1,2})[./](\d{2,4})', s)
    if m:
        d, mo, y = m.group(1), m.group(2), m.group(3)
        if len(y) == 2:
            y = '20' + y
        return f'{y}-{int(mo):02d}-{int(d):02d}'
    return s


# ============ Column detection (Подробный отчёт) ============
DETECT_PATTERNS = {
    'srid': ['srid'],
    'supply_num': ['номер поставки'],
    'barcode': ['баркод', 'шк'],
    'subject': ['предмет'],
    'brand': ['бренд'],
    'article': ['артикул поставщика', 'артикул продавца'],
    'wb_article': ['код номенклатуры', 'артикул wb', 'nmid'],
    'product_name': ['название'],
    'size': ['__exact:размер'],
    'operation_type': ['тип документа'],
    'operation_reason': ['обоснование для оплаты'],
    'order_date': ['дата заказа покупателем', 'дата заказа'],
    'sale_date': ['дата продажи', 'дата операции'],
    'qty': ['кол-во', '__exact:количество'],
    'qty_deliveries': ['количество доставок'],
    'qty_returns': ['количество возврата'],
    'price': ['__exact:цена розничная'],
    'revenue_wb': ['вайлдберриз реализовал товар', 'реализовал товар'],
    'product_discount': ['согласованный продуктовый дисконт'],
    'promo_discount': ['__exact:промокод, %', 'промокод %'],
    'total_discount': ['итоговая согласованная скидка', 'согласованная скидка, %'],
    'price_with_discount': ['с учетом согласованной скидки'],
    'kvv_decrease_rating': ['снижения квв из-за рейтинга'],
    'kvv_decrease_promo': ['снижения квв из-за акции', 'изменения квв из-за акции'],
    'spp_percent': ['скидка постоянного покупателя', 'спп'],
    'kvv_percent': ['__exact:размер квв, %'],
    'kvv_no_nds_basic': ['размер квв без ндс', 'размер  квв без ндс'],
    'kvv_no_nds_final': ['итоговый квв без ндс', 'итоговый квв'],
    'commission_before_nds': ['вознаграждение с продаж до вычета'],
    'pvz_compensation': ['возмещение за выдачу и возврат'],
    'acquiring': ['эквайринг/комиссии', 'эквайринг/комиссия', 'компенсация платёжных услуг', 'компенсация платежных услуг'],
    'acquiring_percent': ['размер комиссии за эквайринг', 'размер компенсации платёжных услуг', 'размер компенсации платежных услуг'],
    'payment_type': ['тип платежа за эквайринг', 'тип платежа: компенсация'],
    'commission': ['вознаграждение вайлдберриз (вв), без ндс', 'вайлдберриз (вв), без ндс'],
    'commission_nds': ['ндс с вознаграждения'],
    'to_pay': ['продавцу за реализованный', 'к перечислению продавцу'],
    'logistics': ['услуги по доставке товара покупателю'],
    'fixation_start': ['дата начала действия фиксации'],
    'fixation_end': ['дата конца действия фиксации'],
    'paid_delivery': ['признак услуги платной доставки'],
    'fine': ['общая сумма штрафов'],
    'wb_correction': ['корректировка вознаграждения вайлдберриз', 'корректировка вв'],
    'penalty_type': ['виды логистики, штрафов'],
    'bank_name': ['наименование банка-эквайера'],
    'office_num': ['__exact:номер офиса'],
    'office_name': ['наименование офиса доставки'],
    'inn': ['инн партнера'],
    'partner': ['__exact:партнер'],
    'warehouse': ['__exact:склад'],
    'country': ['__exact:страна'],
    'box_type': ['тип коробов'],
    'storage_fee': ['__exact:хранение', 'стоимость хранения'],
    'deductions': ['__exact:удержания'],
    'paid_reception': ['платная приемка', 'платная приёмка'],
    'cart_id': ['id корзины заказа'],
    'loyalty_compensation': ['компенсация скидки по программе лояльности'],
    'loyalty_participation': ['стоимость участия в программе лояльности'],
    'loyalty_points': ['сумма удержанная за начисленные баллы'],
    'legal_entity': ['юридическое лицо', '__exact:продавец'],
}


def detect_columns(headers):
    col_map = {field: [] for field in DETECT_PATTERNS}
    for header in headers:
        lower = str(header).lower().strip()
        if not lower:
            continue
        for field, kws in DETECT_PATTERNS.items():
            for kw in kws:
                matched = False
                if kw.startswith('__exact:'):
                    if lower == kw[8:]:
                        matched = True
                elif kw in lower:
                    matched = True
                if matched:
                    if header not in col_map[field]:
                        col_map[field].append(header)
                    break
    return col_map


def normalize_row(row, header_map):
    sale = {}
    for field, cols in header_map.items():
        for col in cols:
            v = row.get(col)
            if v is not None and v != '':
                sale[field] = clean_value(v, field)
                break
    return sale


def find_header_row(rows):
    wb_keys = ['srid', 'артикул', 'тип документа', 'обоснование', 'дата продажи',
               'кол-во', 'цена розничная', 'вайлдберриз', 'квв', 'продавцу',
               'хранение', 'удержания', 'штраф', 'номер поставки']
    best_idx, best_score = -1, 0
    for i in range(min(20, len(rows))):
        row = rows[i]
        if not row or len(row) < 3:
            continue
        text = ' '.join(str(c) for c in row).lower()
        score = sum(1 for k in wb_keys if k in text)
        if score > best_score:
            best_score, best_idx = score, i
    if best_score >= 2:
        return best_idx
    for i in range(len(rows)):
        if rows[i] and len([c for c in rows[i] if c is not None and str(c).strip()]) >= 3:
            return i
    return -1


def _rows_to_dicts(rows):
    """Replicate parseExcelBuffer: find header, build list of header->value dicts."""
    header_idx = find_header_row(rows)
    if header_idx == -1:
        return []
    headers = [str(h or '').strip() for h in rows[header_idx]]
    out = []
    for row in rows[header_idx + 1:]:
        if not row:
            continue
        if all(c is None or str(c).strip() == '' for c in row):
            continue
        obj = {}
        for i, h in enumerate(headers):
            if h:
                obj[h] = row[i] if i < len(row) else ''
        if obj:
            out.append(obj)
    return out


def normalize_rows(all_rows, filename):
    if not all_rows:
        return {'sales': [], 'info': {'filename': filename, 'rowCount': 0}}

    all_headers = set()
    for i in range(min(10, len(all_rows))):
        all_headers.update(all_rows[i].keys())
    header_map = detect_columns(list(all_headers))

    sales = []
    for row in all_rows:
        sale = normalize_row(row, header_map)
        if sale and (sale.get('article') or sale.get('srid') or sale.get('commission')
                     or sale.get('logistics') or sale.get('fine') or sale.get('storage_fee')
                     or sale.get('price_with_discount')):
            sales.append(sale)

    dates = sorted(s.get('sale_date') or s.get('order_date') for s in sales
                   if (s.get('sale_date') or s.get('order_date')))
    date_from = dates[0] if dates else ''
    date_to = dates[-1] if dates else ''

    report_num = ''
    m = re.search(r'(\d{9,10})', str(filename))
    if m:
        report_num = m.group(1)

    legal_entity = ''
    for s in sales:
        if s.get('legal_entity'):
            legal_entity = s['legal_entity']
            break

    return {
        'sales': sales,
        'info': {'filename': filename, 'rowCount': len(sales),
                 'reportNum': report_num or 'unknown', 'dateFrom': date_from,
                 'dateTo': date_to, 'legalEntity': legal_entity},
    }


# ============ Список отчётов ============
def find_list_header_row(rows):
    keys = ['№ отчёта', '№ отчета', 'номер отчёта', 'юридическое лицо',
            'дата начала', 'дата формирования', 'тип отчёта', 'тип отчета',
            'продажа', 'к перечислению', 'стоимость логистики']
    best_idx, best_score = -1, 0
    for i in range(min(15, len(rows))):
        row = rows[i]
        if not row or len(row) < 3:
            continue
        text = ' '.join(str(c) for c in row).lower()
        score = sum(1 for k in keys if k in text)
        if score > best_score:
            best_score, best_idx = score, i
    if best_score >= 2:
        return best_idx
    for i in range(len(rows)):
        if rows[i] and len([c for c in rows[i] if c is not None and str(c).strip()]) >= 3:
            return i
    return -1


def _list_rows_to_dicts(rows):
    header_idx = find_list_header_row(rows)
    if header_idx == -1:
        return []
    headers = [str(h or '').strip() for h in rows[header_idx]]
    out = []
    for row in rows[header_idx + 1:]:
        if not row:
            continue
        if all(c is None or str(c).strip() == '' for c in row):
            continue
        obj = {}
        for i, h in enumerate(headers):
            if h:
                obj[h] = row[i] if i < len(row) else ''
        if obj:
            out.append(obj)
    return out


def _list_num(v):
    if v is None or v == '':
        return 0
    s = re.sub(r'\s+', '', str(v)).replace(' ', '').replace(',', '.')
    try:
        return float(s)
    except (ValueError, TypeError):
        return 0


def _clean(v):
    if v is None or v == '':
        return None
    return str(v).strip()


def normalize_list_row(row):
    r = {}
    for key, value in row.items():
        lower = str(key).lower().strip()
        if '№ отчёта' in lower or '№ отчета' in lower or lower == '№':
            r['report_num'] = re.sub(r'\s+', '', str(_clean(value) or ''))
        elif 'юридическое лицо' in lower:
            r['legal_entity'] = _clean(value)
        elif 'дата начала' in lower:
            r['date_from'] = parse_date(value)
        elif 'дата конца' in lower:
            r['date_to'] = parse_date(value)
        elif lower == 'период' or 'период' in lower:
            m = re.search(r'(\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|\d{4}[./-]\d{1,2}[./-]\d{1,2}).*?(\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|\d{4}[./-]\d{1,2}[./-]\d{1,2})', str(value or ''))
            if m:
                if not r.get('date_from'):
                    r['date_from'] = parse_date(m.group(1))
                if not r.get('date_to'):
                    r['date_to'] = parse_date(m.group(2))
        elif 'дата формирования' in lower:
            r['created_at'] = parse_date(value)
        elif 'тип отчёта' in lower or 'тип отчета' in lower:
            r['report_type'] = _clean(value)
        elif lower == 'продажа' or (lower.startswith('продажа') and 'сумма' not in lower):
            r['sale_total'] = _list_num(value)
        elif 'компенсация скидки' in lower:
            r['loyalty_compensation'] = _list_num(value)
        elif 'к перечислению за товар' in lower or 'к перечислению' in lower:
            r['to_pay'] = _list_num(value)
        elif 'согласованная скидка' in lower:
            r['discount_percent'] = _list_num(value)
        elif 'стоимость логистики' in lower:
            r['logistics_cost'] = _list_num(value)
        elif 'стоимость хранения' in lower:
            r['storage_cost'] = _list_num(value)
        elif 'стоимость платной приемки' in lower or 'стоимость платной приёмки' in lower:
            r['paid_reception'] = _list_num(value)
        elif 'прочие удержания' in lower or 'удержания/выплаты' in lower:
            r['other_deductions'] = _list_num(value)
        elif 'общая сумма штрафов' in lower or ('сумма штрафов' in lower and 'всего' not in lower):
            r['fines_total'] = _list_num(value)
        elif 'корректировка вознаграждения' in lower or 'корректировка вв' in lower:
            r['wb_correction'] = _list_num(value)
        elif 'стоимость участия' in lower or 'участия в программе лояльности' in lower:
            r['loyalty_participation'] = _list_num(value)
        elif 'сумма удержанная за начисленные баллы' in lower or 'сумма баллов' in lower:
            r['loyalty_points'] = _list_num(value)
        elif 'итого к оплате' in lower or 'итого к выплате' in lower:
            r['total_to_pay'] = _list_num(value)
    return r


def normalize_list_rows(rows, filename):
    if not rows:
        return {'reports': [], 'info': {'filename': filename, 'count': 0}}
    reports = []
    for row in rows:
        r = normalize_list_row(row)
        if r and r.get('report_num'):
            reports.append(r)
    return {'reports': reports, 'info': {'filename': filename, 'count': len(reports)}}


# ============ Reading layer (calamine / csv / zip) ============
def _read_sheets(source):
    """source: path str or bytes/file-like. Returns list of sheets, each list[list]."""
    if isinstance(source, (bytes, bytearray)):
        wb = CalamineWorkbook.from_filelike(io.BytesIO(source))
    elif hasattr(source, 'read'):
        wb = CalamineWorkbook.from_filelike(source)
    else:
        wb = CalamineWorkbook.from_path(source)
    sheets = []
    for name in wb.sheet_names:
        sheet = wb.get_sheet_by_name(name)
        sheets.append(sheet.to_python(skip_empty_area=True))
    return sheets


def parse_excel(source, filename):
    """Parse a Подробный отчёт (detail report) Excel into normalized rows."""
    all_rows = []
    for rows in _read_sheets(source):
        all_rows.extend(_rows_to_dicts(rows))
    return normalize_rows(all_rows, filename)


def parse_list_excel(source, filename):
    """Parse a Список отчётов (report list) Excel."""
    all_rows = []
    for rows in _read_sheets(source):
        all_rows.extend(_list_rows_to_dicts(rows))
    return normalize_list_rows(all_rows, filename)


def parse_csv_text(text, filename):
    first_line = text.split('\n')[0] if text else ''
    sep = ';' if ';' in first_line else ','
    lines = [l for l in re.split(r'\r?\n', text) if l.strip()]
    if not lines:
        return {'sales': [], 'info': {'filename': filename, 'rowCount': 0}}
    headers = [h.strip() for h in _parse_csv_line(lines[0], sep)]
    rows = []
    for line in lines[1:]:
        values = _parse_csv_line(line, sep)
        obj = {headers[j]: (values[j] if j < len(values) else '') for j in range(len(headers))}
        rows.append(obj)
    return normalize_rows(rows, filename)


def _parse_csv_line(line, sep):
    result, cur, q = [], '', False
    for ch in line:
        if ch == '"':
            q = not q
        elif ch == sep and not q:
            result.append(cur)
            cur = ''
        else:
            cur += ch
    result.append(cur)
    return result


def parse_zip(source, filename):
    """Parse a ZIP of detail-report Excel/CSV files and merge the results."""
    if isinstance(source, (bytes, bytearray)):
        zf = zipfile.ZipFile(io.BytesIO(source))
    else:
        zf = zipfile.ZipFile(source)
    results, errors = [], []
    for info in zf.infolist():
        if info.is_dir():
            continue
        name = info.filename
        if name.startswith('__MACOSX/') or '/.DS_Store' in name:
            continue
        lower = name.lower()
        try:
            if lower.endswith('.xlsx') or lower.endswith('.xls'):
                results.append(parse_excel(zf.read(info), name))
            elif lower.endswith('.csv'):
                results.append(parse_csv_text(zf.read(info).decode('utf-8', 'replace'), name))
        except Exception as e:  # noqa: BLE001 — mirror JS: collect per-file errors
            errors.append(f'{name}: {e}')
    if not results:
        raise ValueError('ZIP ichida Excel topilmadi'
                         + ('. Xatolar: ' + '; '.join(errors) if errors else ''))
    merged = merge_results(results)
    if errors:
        merged['info']['warnings'] = errors
    return merged


def merge_results(results):
    all_sales, filenames = [], []
    report_num = legal_entity = date_from = date_to = ''
    for r in results:
        all_sales.extend(r['sales'])
        filenames.append(r['info']['filename'])
        if r['info'].get('reportNum') and r['info']['reportNum'] != 'unknown':
            report_num = r['info']['reportNum']
        if r['info'].get('legalEntity'):
            legal_entity = r['info']['legalEntity']
        if r['info'].get('dateFrom') and (not date_from or r['info']['dateFrom'] < date_from):
            date_from = r['info']['dateFrom']
        if r['info'].get('dateTo') and (not date_to or r['info']['dateTo'] > date_to):
            date_to = r['info']['dateTo']
    return {
        'sales': all_sales,
        'info': {'filename': ', '.join(filenames), 'rowCount': len(all_sales),
                 'reportNum': report_num or 'unknown', 'dateFrom': date_from,
                 'dateTo': date_to, 'legalEntity': legal_entity},
    }


def parse_detail_file(source, filename):
    """Entry point for a detail report: dispatch by extension (mirrors parseFile)."""
    name = str(filename).lower()
    if name.endswith('.zip'):
        return parse_zip(source, filename)
    if name.endswith('.xlsx') or name.endswith('.xls'):
        return parse_excel(source, filename)
    if name.endswith('.csv'):
        text = source.decode('utf-8', 'replace') if isinstance(source, (bytes, bytearray)) else source.read().decode('utf-8', 'replace')
        return parse_csv_text(text, filename)
    raise ValueError(f"Qo'llab-quvvatlanmagan fayl turi: {filename}")

# ============================================================
# Капитализация parsers (stock / sales / nomenclature)
# Ports of parseStockFile / parseSalesFile / parseNomenclatureFile (capitalization.html)
# ============================================================
def _cap_first_sheet(source, filename):
    """Return the first sheet's rows (list[list]) from xlsx/zip bytes.

    For a .zip, picks the largest inner .xlsx (mirrors readExcelFile)."""
    name = str(filename or '').lower()
    if name.endswith('.zip'):
        zf = zipfile.ZipFile(io.BytesIO(source) if isinstance(source, (bytes, bytearray)) else source)
        candidates = [(i.filename, i.file_size) for i in zf.infolist()
                      if not i.is_dir() and re.search(r'\.xlsx?$', i.filename, re.I)
                      and not i.filename.startswith('__MACOSX/')]
        if not candidates:
            raise ValueError('ZIP ichida xlsx fayl topilmadi')
        target = max(candidates, key=lambda c: c[1])[0]
        source = zf.read(target)
    sheets = _read_sheets(source)
    return sheets[0] if sheets else []


def _cap_str(v):
    return '' if v is None else str(v).strip()


def _cap_num(v):
    try:
        if v in (None, ''):
            return 0
        return float(str(v).replace(',', '.').replace(' ', ''))
    except (ValueError, TypeError):
        return 0


def _find_col(header, *patterns):
    for i, h in enumerate(header):
        for pat in patterns:
            if re.search(pat, h, re.I):
                return i
    return -1


def parse_cap_stock(source, filename=''):
    """Отчёт по остаткам: brand|product|article|code|barcode|size|in_route|returns|total|+warehouses."""
    rows = _cap_first_sheet(source, filename)
    if len(rows) < 2:
        return []
    header = [_cap_str(h) for h in rows[0]]
    idx = {
        'brand': _find_col(header, r'^Бренд$'),
        'product': _find_col(header, r'^Предмет$'),
        'article': _find_col(header, r'Артикул продавца'),
        'code': _find_col(header, r'Артикул WB'),
        'barcode': _find_col(header, r'^Баркод$'),
        'size': _find_col(header, r'Размер'),
        'in_route': _find_col(header, r'В пути до получ'),
        'returns': _find_col(header, r'В пути возвраты'),
        'total': _find_col(header, r'Всего находится'),
    }
    sklad_cols = [(i, header[i]) for i in range(idx['total'] + 1, len(header)) if header[i]]

    def cell(r, i):
        return r[i] if 0 <= i < len(r) else ''

    out = []
    for r in rows[1:]:
        barcode = _cap_str(cell(r, idx['barcode']))
        if not barcode:
            continue
        warehouses = {}
        for i, nm in sklad_cols:
            v = _cap_num(cell(r, i))
            if v > 0:
                warehouses[nm] = v
        out.append({
            'brand': _cap_str(cell(r, idx['brand'])),
            'product': _cap_str(cell(r, idx['product'])),
            'article': _cap_str(cell(r, idx['article'])),
            'code': _cap_str(cell(r, idx['code'])),
            'barcode': barcode,
            'size': _cap_str(cell(r, idx['size'])),
            'in_route': _cap_num(cell(r, idx['in_route'])),
            'returns_en_route': _cap_num(cell(r, idx['returns'])),
            'total_in_warehouses': _cap_num(cell(r, idx['total'])),
            'warehouses': warehouses,
        })
    return out


def parse_cap_sales(source, filename=''):
    """Отчёт по продажам: header may be in row 0 or 1."""
    rows = _cap_first_sheet(source, filename)
    if len(rows) < 3:
        return []
    header_idx = 0
    header = [_cap_str(h) for h in rows[0]]
    if not any(re.search(r'^Бренд$', h, re.I) for h in header):
        header_idx = 1
        header = [_cap_str(h) for h in rows[1]]
    idx = {
        'brand': _find_col(header, r'^Бренд$'),
        'product': _find_col(header, r'^Предмет$'),
        'article': _find_col(header, r'Артикул продавца'),
        'code': _find_col(header, r'Артикул WB'),
        'barcode': _find_col(header, r'^Баркод$'),
        'size': _find_col(header, r'^Размер$'),
        'sklad': _find_col(header, r'^Склад$'),
        'ordered': _find_col(header, r'^шт\.?$', r'Заказано'),
        'revenue': _find_col(header, r'Сумма заказов'),
        'purchased': _find_col(header, r'Выкупили'),
        'payout': _find_col(header, r'К перечислению'),
        'current_stock': _find_col(header, r'Текущий остаток'),
    }

    def cell(r, i):
        return r[i] if 0 <= i < len(r) else ''

    out = []
    for r in rows[header_idx + 1:]:
        barcode = _cap_str(cell(r, idx['barcode']))
        if not barcode:
            continue
        out.append({
            'brand': _cap_str(cell(r, idx['brand'])),
            'product': _cap_str(cell(r, idx['product'])),
            'article': _cap_str(cell(r, idx['article'])),
            'code': _cap_str(cell(r, idx['code'])),
            'barcode': barcode,
            'size': _cap_str(cell(r, idx['size'])),
            'sklad': _cap_str(cell(r, idx['sklad'])),
            'ordered': _cap_num(cell(r, idx['ordered'])),
            'revenue': _cap_num(cell(r, idx['revenue'])),
            'purchased': _cap_num(cell(r, idx['purchased'])),
            'payout': _cap_num(cell(r, idx['payout'])),
            'current_stock': _cap_num(cell(r, idx['current_stock'])),
        })
    return out


def parse_cap_nomenclature(source, filename=''):
    """Перечень номенклатур."""
    rows = _cap_first_sheet(source, filename)
    if len(rows) < 2:
        return []
    header = [_cap_str(h) for h in rows[0]]
    idx = {
        'brand': _find_col(header, r'^Бренд$'),
        'product': _find_col(header, r'^Предмет$'),
        'chrt_id': _find_col(header, r'Код размера', r'chrt_id'),
        'article': _find_col(header, r'Артикул продавца'),
        'code': _find_col(header, r'Артикул WB'),
        'size': _find_col(header, r'^Размер$'),
        'barcode': _find_col(header, r'^Баркод$'),
        'volume': _find_col(header, r'Объем'),
        'composition': _find_col(header, r'Состав'),
    }

    def cell(r, i):
        return r[i] if 0 <= i < len(r) else ''

    out = []
    for r in rows[1:]:
        barcode = _cap_str(cell(r, idx['barcode']))
        if not barcode:
            continue
        out.append({
            'brand': _cap_str(cell(r, idx['brand'])),
            'product': _cap_str(cell(r, idx['product'])),
            'chrt_id': _cap_str(cell(r, idx['chrt_id'])),
            'article': _cap_str(cell(r, idx['article'])),
            'code': _cap_str(cell(r, idx['code'])),
            'size': _cap_str(cell(r, idx['size'])),
            'barcode': barcode,
            'volume': _cap_str(cell(r, idx['volume'])),
            'composition': _cap_str(cell(r, idx['composition'])),
        })
    return out
