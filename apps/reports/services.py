"""Ingest pipeline: parser output -> formula engine -> BaseRow columns -> DB.

Excel files are parsed in-memory and never written to permanent storage. Per-row
formula results are stored as columns so reports run as SQL aggregations.
"""
import datetime

from django.db import transaction
from django.db.models import F

from apps.core import parser
from apps.core.formulas import calculate_row, num

from .models import (
    BaseRow, CapNomenclature, CapParams, CapSales, CapStock, Cost, ListReport,
    SelfPurchase, UploadHistory,
)

# calculate_row letter key -> BaseRow field name
LETTER_TO_FIELD = {
    'D': 'sold_qty', 'E': 'returned_qty', 'F': 'sold_rub', 'G': 'returned_rub',
    'H': 'net_qty', 'I': 'revenue', 'J': 'to_transfer', 'K': 'commission',
    'L': 'acquiring', 'N': 'spp', 'O': 'comp_brak', 'P': 'comp_uscherb',
    'S': 'logistics_direct', 'T': 'logistics_back', 'V': 'paid_acceptance',
    'W': 'pl_deduction', 'X': 'cashback', 'Y': 'to_pay_rs', 'Z': 'wb_realized',
    'AA': 'tax_base', 'AB': 'tax', 'AC': 'cost', 'AD': 'storage',
    'AE': 'promotion', 'AF': 'transit', 'AG': 'supply_change', 'AH': 'jem',
    'AI': 'utilization', 'AJ': 'review_cancel', 'AK': 'other_deduction',
    'AL': 'samovikup_cost', 'AN': 'ext_expenses',
}

# CharField max lengths (truncate WB values that exceed them)
_MAXLEN = {
    'report_num': 32, 'srid': 128, 'month': 16, 'article': 128, 'brand': 255,
    'product_name': 512, 'size': 64, 'group': 128, 'warehouse': 128,
    'penalty_type': 255, 'legal_entity': 255,
    # Cost fields (costs import / inline barcode edit)
    'barcode': 64, 'code': 64, 'supply_num': 64, 'kluch': 128, 'name': 255,
}


def _trunc(field, value):
    s = '' if value is None else str(value)
    n = _MAXLEN.get(field)
    return s[:n] if n else s


def _to_date(val):
    if not val:
        return None
    if isinstance(val, datetime.date):
        return val
    try:
        return datetime.date.fromisoformat(str(val)[:10])
    except (ValueError, TypeError):
        return None


def _to_int(val):
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def build_ctx(profile, report_num=''):
    """Build the calculation context for a profile (costs/settings/samovikupy/list)."""
    costs = list(Cost.objects.filter(profile=profile).values(
        'kluch', 'supply_num', 'code', 'barcode', 'cost', 'group'))
    samovikupy = list(SelfPurchase.objects.filter(profile=profile).values('srid', 'total'))
    list_reports = [
        {'report_num': lr.report_num,
         'date_from': lr.date_from.isoformat() if lr.date_from else None,
         'legal_entity': lr.legal_entity}
        for lr in ListReport.objects.filter(profile=profile)
    ]
    return {
        'reportNum': report_num,
        'settings': {'tax_type': profile.tax_type, 'tax_rate': float(profile.tax_rate)},
        'costs': costs,
        'samovikupy': samovikupy,
        'listReports': list_reports,
    }


def _make_base_row(profile, sale, calc, report_num):
    row = BaseRow(
        profile=profile,
        report_num=_trunc('report_num', report_num),
        srid=_trunc('srid', sale.get('srid') or ''),
        raw=sale,
        sale_date=_to_date(sale.get('sale_date')),
        week=_to_date(calc.get('AP')),
        month=_trunc('month', calc.get('AQ') or ''),
        year=_to_int(calc.get('AR')) if calc.get('AR') != '' else None,
        article=_trunc('article', calc.get('AT') or ''),
        brand=_trunc('brand', calc.get('AS') or ''),
        product_name=_trunc('product_name', calc.get('AU') or ''),
        size=_trunc('size', calc.get('AV') or ''),
        group=_trunc('group', calc.get('AX') or ''),
        warehouse=_trunc('warehouse', sale.get('warehouse') or ''),
        penalty_type=_trunc('penalty_type', sale.get('penalty_type') or ''),
        legal_entity=_trunc('legal_entity', calc.get('AY') or ''),
        raw_logistics=num(sale.get('logistics')),
        fine=num(sale.get('fine')),
        wb_correction=num(sale.get('wb_correction')),
    )
    for letter, field in LETTER_TO_FIELD.items():
        setattr(row, field, num(calc.get(letter)))
    return row


@transaction.atomic
def ingest_detail(profile, parse_result, user=None, override_report_num=None):
    """Store a Подробный отчёт (detail) parse result as BaseRow rows.

    Dedup mirrors storage.addBaseRows: a row whose srid already exists for the same
    report_num is skipped; rows without srid are always added.

    report_num priority (mirrors the original upload.js): an explicit
    override_report_num (user picked one) wins, otherwise the number detected from
    the filename, otherwise 'unknown'.
    """
    info = parse_result['info']
    sales = parse_result['sales']
    report_num = (str(override_report_num).strip() if override_report_num else '') \
        or info.get('reportNum') or 'unknown'

    ctx = build_ctx(profile, report_num)

    existing_srids = set(
        BaseRow.objects.filter(profile=profile, report_num=report_num)
        .exclude(srid='').values_list('srid', flat=True)
    )

    # Dedup EXACTLY like storage.addBaseRows: skip a row only if its srid is already
    # stored for this report. Do NOT dedup within the batch — in a WB Подробный отчёт
    # one srid legitimately spans several rows (Продажа + Логистика + Хранение all
    # share the same srid), so in-batch dedup would drop the sale/logistics lines.
    rows, added, skipped = [], 0, 0
    for sale in sales:
        srid = sale.get('srid') or ''
        if srid and srid in existing_srids:
            skipped += 1
            continue
        calc = calculate_row(sale, {**ctx, 'reportNum': sale.get('report_num') or report_num})
        rows.append(_make_base_row(profile, sale, calc, report_num))
        added += 1

    if rows:
        BaseRow.objects.bulk_create(rows, batch_size=1000)

    total_sum = sum(r.revenue for r in rows)
    UploadHistory.objects.create(
        profile=profile, type='detail', filename=info.get('filename', ''),
        report_num=report_num if report_num != 'unknown' else '',
        date_from=_to_date(info.get('dateFrom')), date_to=_to_date(info.get('dateTo')),
        row_count=added, total_sum=total_sum, uploaded_by=user,
    )
    return {'added': added, 'skipped': skipped, 'report_num': report_num,
            'total': BaseRow.objects.filter(profile=profile).count()}


@transaction.atomic
def ingest_list(profile, parse_result, user=None):
    """Store a Список отчётов parse result. Dedup by report_num (update existing)."""
    info = parse_result['info']
    reports = parse_result['reports']

    added, updated = 0, 0
    fields = ['legal_entity', 'date_from', 'date_to', 'created_at', 'report_type',
              'sale_total', 'to_pay', 'discount_percent', 'logistics_cost',
              'storage_cost', 'paid_reception', 'other_deductions', 'fines_total',
              'wb_correction', 'loyalty_compensation', 'loyalty_participation',
              'loyalty_points', 'total_to_pay']

    for r in reports:
        report_num = (r.get('report_num') or '')[:32]
        if not report_num:
            continue
        defaults = {
            'legal_entity': (r.get('legal_entity') or '')[:255],
            'date_from': _to_date(r.get('date_from')),
            'date_to': _to_date(r.get('date_to')),
            'created_at': _to_date(r.get('created_at')),
            'report_type': (r.get('report_type') or '')[:128],
        }
        for key in ['sale_total', 'to_pay', 'discount_percent', 'logistics_cost',
                    'storage_cost', 'paid_reception', 'other_deductions', 'fines_total',
                    'wb_correction', 'loyalty_compensation', 'loyalty_participation',
                    'loyalty_points', 'total_to_pay']:
            defaults[key] = num(r.get(key))
        obj, created = ListReport.objects.update_or_create(
            profile=profile, report_num=report_num, defaults=defaults)
        added += 1 if created else 0
        updated += 0 if created else 1

    UploadHistory.objects.create(
        profile=profile, type='list', filename=info.get('filename', ''),
        row_count=added + updated, uploaded_by=user,
    )
    return {'added': added, 'updated': updated,
            'total': ListReport.objects.filter(profile=profile).count()}


@transaction.atomic
def recompute_tax(profile):
    """Fast recompute of just the tax columns (AA tax_base + AB tax).

    Changing the profile's tax_type / tax_rate only affects columns AA and AB of
    the formula (see calculate_row). Both depend exclusively on values already
    stored on BaseRow (Z=wb_realized, Y=to_pay_rs, AC=cost, AN=ext_expenses), so we
    update them with two bulk SQL statements instead of re-running the whole formula
    engine over every row. This is O(1) queries regardless of row count.

    Tax-base definition mirrors calculate_row exactly:
        type 1 (default): AA = Z
        type 2:           AA = Y - AC - AN
        type 3:           AA = 0
        type 4:           AA = Y
        AB = AA * tax_rate / 100
    """
    qs = BaseRow.objects.filter(profile=profile)
    tax_type = profile.tax_type
    if tax_type == 2:
        qs.update(tax_base=F('to_pay_rs') - F('cost') - F('ext_expenses'))
    elif tax_type == 3:
        qs.update(tax_base=0)
    elif tax_type == 4:
        qs.update(tax_base=F('to_pay_rs'))
    else:  # 1 and any unknown value -> Z
        qs.update(tax_base=F('wb_realized'))

    rate = float(profile.tax_rate) / 100.0
    qs.update(tax=F('tax_base') * rate)
    return {'recomputed': qs.count()}


def recompute_profile(profile, batch_size=1000):
    """Recompute every BaseRow for a profile from its stored `raw` data.

    Called when costs/settings/self-purchases/list-reports change (which alter the
    formula outputs). Updates only the computed columns + grouping keys.
    """
    ctx = build_ctx(profile)
    qs = BaseRow.objects.filter(profile=profile).iterator(chunk_size=batch_size)
    update_fields = list(LETTER_TO_FIELD.values()) + [
        'week', 'month', 'year', 'article', 'brand', 'product_name', 'size',
        'group', 'legal_entity', 'raw_logistics', 'fine', 'wb_correction']
    buffer, total = [], 0

    def flush(rows):
        if rows:
            BaseRow.objects.bulk_update(rows, update_fields, batch_size=batch_size)

    for row in qs:
        sale = row.raw or {}
        calc = calculate_row(sale, {**ctx, 'reportNum': sale.get('report_num') or row.report_num})
        for letter, field in LETTER_TO_FIELD.items():
            setattr(row, field, num(calc.get(letter)))
        row.week = _to_date(calc.get('AP'))
        row.month = _trunc('month', calc.get('AQ') or '')
        row.year = _to_int(calc.get('AR')) if calc.get('AR') != '' else None
        row.article = _trunc('article', calc.get('AT') or '')
        row.brand = _trunc('brand', calc.get('AS') or '')
        row.product_name = _trunc('product_name', calc.get('AU') or '')
        row.size = _trunc('size', calc.get('AV') or '')
        row.group = _trunc('group', calc.get('AX') or '')
        row.legal_entity = _trunc('legal_entity', calc.get('AY') or '')
        row.raw_logistics = num(sale.get('logistics'))
        row.fine = num(sale.get('fine'))
        row.wb_correction = num(sale.get('wb_correction'))
        buffer.append(row)
        total += 1
        if len(buffer) >= batch_size:
            flush(buffer)
            buffer = []
    flush(buffer)
    return {'recomputed': total}


def parse_costs_file(uploaded_file):
    """Parse a Себестоимость Excel/CSV (in-memory). Port of the costs page's
    importFromExcel: find the header row, map бренд/артикул/товар/код/себест/группа
    columns, return list of {brand, article, name, code, group, cost} dicts."""
    data = uploaded_file.read()
    name = (uploaded_file.name or '').lower()
    if name.endswith('.csv'):
        text = data.decode('utf-8-sig', errors='replace')
        sep = ';' if ';' in (text.split('\n', 1)[0]) else ','
        rows = [parser._parse_csv_line(l, sep) for l in text.splitlines() if l.strip()]
    else:
        sheets = parser._read_sheets(data)
        rows = sheets[0] if sheets else []
    rows = [[('' if c is None else c) for c in (r or [])] for r in rows]
    if len(rows) < 2:
        return []

    # find header row (артикул + код/себестоимость)
    header_idx = 0
    for i in range(min(10, len(rows))):
        text = ' '.join(str(c) for c in rows[i]).lower()
        if 'артикул' in text and ('код' in text or 'себестоимость' in text):
            header_idx = i
            break
    headers = [str(h).lower().strip() for h in rows[header_idx]]
    col = {'brand': -1, 'article': -1, 'name': -1, 'code': -1, 'cost': -1, 'group': -1}
    for i, h in enumerate(headers):
        if 'бренд' in h:
            col['brand'] = i
        elif 'артикул' in h:
            col['article'] = i
        elif 'товар' in h or 'название' in h:
            col['name'] = i
        elif 'код' in h:
            col['code'] = i
        elif 'себестоимость' in h or 'tannarx' in h:
            col['cost'] = i
        elif 'группа' in h or 'guruh' in h:
            col['group'] = i
    if col['code'] == -1 and col['article'] == -1:
        raise ValueError('Артикул yoki Код ustunlari topilmadi')

    def cell(row, key):
        i = col[key]
        return str(row[i]).strip() if 0 <= i < len(row) else ''

    out = []
    for r in rows[header_idx + 1:]:
        if not r:
            continue
        code = cell(r, 'code')
        article = cell(r, 'article')
        if not code and not article:
            continue
        out.append({
            'brand': cell(r, 'brand'), 'article': article, 'name': cell(r, 'name'),
            'code': code, 'group': cell(r, 'group'), 'cost': num(cell(r, 'cost')),
        })
    return out


def import_costs(profile, rows):
    """Upsert parsed cost rows by code (fallback article), then recompute."""
    existing = {}
    for c in Cost.objects.filter(profile=profile):
        existing[c.code or c.article] = c
    added = updated = 0
    to_create, to_update = [], []
    for nc in rows:
        key = nc['code'] or nc['article']
        brand = _trunc('brand', nc['brand'])
        article = _trunc('article', nc['article'])
        name = _trunc('name', nc['name'])
        code = _trunc('code', nc['code'])
        group = _trunc('group', nc['group'])
        cur = existing.get(key)
        if cur:
            cur.brand, cur.article, cur.name = brand, article, name
            cur.code, cur.group, cur.cost = code, group, nc['cost']
            cur.kluch = _trunc('kluch', (cur.supply_num or '') + (nc['code'] or ''))
            to_update.append(cur)
            updated += 1
        else:
            obj = Cost(profile=profile, brand=brand, article=article,
                       name=name, code=code, group=group,
                       cost=nc['cost'], kluch=_trunc('kluch', nc['code']))
            to_create.append(obj)
            existing[key] = obj
            added += 1
    if to_create:
        Cost.objects.bulk_create(to_create)
    if to_update:
        Cost.objects.bulk_update(to_update, ['brand', 'article', 'name', 'code',
                                             'group', 'cost', 'kluch'])
    recompute_profile(profile)
    return {'added': added, 'updated': updated}


def import_costs_fill_missing(profile, rows):
    """Fill costs from an uploaded tannarx file ONLY for products that have no
    cost yet (cost == 0). Products that already have a cost are left untouched.
    Matched by code (fallback article), same as import_costs."""
    existing = {}
    for c in Cost.objects.filter(profile=profile):
        existing[c.code or c.article] = c
    added = filled = skipped = 0
    to_create, to_update = [], []
    for nc in rows:
        new_cost = nc['cost']
        if not new_cost or new_cost <= 0:
            continue  # uploaded row has no usable cost
        key = nc['code'] or nc['article']
        cur = existing.get(key)
        if cur:
            if (cur.cost or 0) > 0:
                skipped += 1  # already priced — keep the existing cost
                continue
            cur.cost = new_cost
            cur.cost_future = cur.cost_future or new_cost
            # Backfill descriptive fields only when empty.
            cur.brand = cur.brand or _trunc('brand', nc['brand'])
            cur.article = cur.article or _trunc('article', nc['article'])
            cur.name = cur.name or _trunc('name', nc['name'])
            cur.group = cur.group or _trunc('group', nc['group'])
            to_update.append(cur)
            filled += 1
        else:
            obj = Cost(profile=profile, brand=_trunc('brand', nc['brand']),
                       article=_trunc('article', nc['article']), name=_trunc('name', nc['name']),
                       code=_trunc('code', nc['code']), group=_trunc('group', nc['group']),
                       cost=new_cost, cost_future=new_cost, kluch=_trunc('kluch', nc['code']))
            to_create.append(obj)
            existing[key] = obj
            added += 1
    if to_create:
        Cost.objects.bulk_create(to_create)
    if to_update:
        Cost.objects.bulk_update(to_update, ['brand', 'article', 'name',
                                             'group', 'cost', 'cost_future'])
    recompute_profile(profile)
    return {'added': added, 'filled': filled, 'skipped': skipped}


def base_code_info(profile):
    """Map код номенклатуры -> {brand, article, product, sizes[]} from БАЗА.

    Mirrors the codeInfo map the original costs page built from Storage.getBase():
    used to fill brand/article/product/size for missing-cost rows on the costs page
    (Excel export + the "yangi artikullar" prompt). Built from distinct rows so it
    stays small (≈ number of distinct products).
    """
    info = {}
    qs = (BaseRow.objects.filter(profile=profile)
          .values('raw__wb_article', 'brand', 'article', 'product_name', 'size')
          .distinct())
    for r in qs:
        code = str(r['raw__wb_article'] or '')
        if not code or code in ('0', 'undefined'):
            continue
        d = info.setdefault(code, {'code': code, 'brand': '', 'article': '',
                                   'product': '', 'sizes': []})
        if not d['brand'] and r['brand']:
            d['brand'] = r['brand']
        if not d['article'] and r['article']:
            d['article'] = r['article']
        if not d['product'] and r['product_name']:
            d['product'] = r['product_name']
        size = (r['size'] or '').strip()
        if size and size not in d['sizes']:
            d['sizes'].append(size)
    return info


def parse_uploaded(uploaded_file, kind):
    """Read an uploaded file fully into memory and parse it. The uploaded file is
    discarded at request end — nothing is persisted to disk.

    kind: 'detail' (Подробный отчёт, xlsx/zip/csv) or 'list' (Список отчётов xlsx).
    """
    data = uploaded_file.read()
    filename = uploaded_file.name
    if kind == 'list':
        return parser.parse_list_excel(data, filename)
    return parser.parse_detail_file(data, filename)


# ============================================================
# Капитализация (stock / sales / nomenclature uploads + params + costs)
# ============================================================
_CAP_MODEL = {'stock': CapStock, 'sales': CapSales, 'nomenclature': CapNomenclature}


def parse_cap_file(uploaded_file, kind):
    """Parse a Капитализация upload (in-memory) → list of dicts. kind ∈ stock/sales/nomenclature."""
    data = uploaded_file.read()
    name = uploaded_file.name
    if kind == 'stock':
        return parser.parse_cap_stock(data, name)
    if kind == 'sales':
        return parser.parse_cap_sales(data, name)
    return parser.parse_cap_nomenclature(data, name)


@transaction.atomic
def ingest_cap(profile, kind, rows):
    """Replace all Cap{kind} rows for a profile and stamp the upload time."""
    model = _CAP_MODEL[kind]
    model.objects.filter(profile=profile).delete()
    objs = []
    for r in rows:
        kwargs = {'profile': profile, 'raw': r,
                  'barcode': str(r.get('barcode') or '')[:64],
                  'article': str(r.get('article') or '')[:128]}
        if kind == 'stock':
            kwargs['warehouse'] = ''
            kwargs['qty'] = r.get('total_in_warehouses') or 0
        elif kind == 'sales':
            kwargs['qty'] = r.get('ordered') or 0
        else:
            kwargs['name'] = str(r.get('product') or '')[:512]
        objs.append(model(**kwargs))
    if objs:
        model.objects.bulk_create(objs, batch_size=1000)
    params, _ = CapParams.objects.get_or_create(profile=profile)
    setattr(params, f'{kind}_uploaded_at',
            datetime.datetime.now(datetime.timezone.utc))
    params.save()
    return {'count': len(objs)}


def clear_cap(profile, kind):
    model = _CAP_MODEL[kind]
    n, _ = model.objects.filter(profile=profile).delete()
    params, _ = CapParams.objects.get_or_create(profile=profile)
    setattr(params, f'{kind}_uploaded_at', None)
    params.save()
    return {'deleted': n}


def cap_params_dict(profile):
    p, _ = CapParams.objects.get_or_create(profile=profile)
    return {
        'days_of_sales': p.days_of_sales, 'delivery_days': p.delivery_days,
        'reserve_days': p.reserve_days, 'delivery_cost': p.delivery_cost,
        'selected_warehouse': p.selected_warehouse,
        'stock_uploaded_at': p.stock_uploaded_at.isoformat() if p.stock_uploaded_at else None,
        'sales_uploaded_at': p.sales_uploaded_at.isoformat() if p.sales_uploaded_at else None,
        'nomenclature_uploaded_at': p.nomenclature_uploaded_at.isoformat() if p.nomenclature_uploaded_at else None,
    }


def save_cap_params(profile, data):
    p, _ = CapParams.objects.get_or_create(profile=profile)
    if 'days_of_sales' in data:
        p.days_of_sales = int(num(data.get('days_of_sales')) or 7)
    if 'delivery_days' in data:
        p.delivery_days = int(num(data.get('delivery_days')) or 7)
    if 'reserve_days' in data:
        p.reserve_days = int(num(data.get('reserve_days')) or 7)
    if 'delivery_cost' in data:
        p.delivery_cost = num(data.get('delivery_cost'))
    if 'selected_warehouse' in data and data.get('selected_warehouse'):
        p.selected_warehouse = str(data['selected_warehouse'])[:128]
    p.save()
    return cap_params_dict(profile)


def cap_data(profile):
    """Everything the capitalization page embeds: stored rows + params + costs."""
    return {
        'stock': list(CapStock.objects.filter(profile=profile).values_list('raw', flat=True)),
        'sales': list(CapSales.objects.filter(profile=profile).values_list('raw', flat=True)),
        'nomenclature': list(CapNomenclature.objects.filter(profile=profile).values_list('raw', flat=True)),
        'params': cap_params_dict(profile),
        'costs': list(Cost.objects.filter(profile=profile).values(
            'barcode', 'code', 'article', 'brand', 'name', 'group', 'cost', 'cost_future')),
    }


def dashboard_warnings(profile, limit=8):
    """Dashboard ogohlantirishlari: kam qolgan tovarlar + tannarxsiz tovarlar.

    Kam qolgan (low stock): kapitalizatsiya sahifasidagi 'red' signalning aynan
    o'zi — ordered>0 va daysLeft<delivery_days (computeCapitalization bilan bir xil).
    Tannarxsiz: costs sahifasidagi "База da N ta tovar tannарxsiz" mantig'i —
    БАЗА da sotilgan, ammo Cost jadvalida tannarxi yo'q kодlar.
    """
    params = cap_params_dict(profile)
    days = params['days_of_sales'] or 7
    delivery_days = params['delivery_days'] or 7
    sklad = params['selected_warehouse'] or 'Все склады'

    # --- Kam qolgan tovarlar (kapitalizatsiya logikasi) ---
    sales_by_barcode = {}
    for s in CapSales.objects.filter(profile=profile).values_list('raw', flat=True):
        bc = str(s.get('barcode') or '')
        if not bc:
            continue
        d = sales_by_barcode.setdefault(bc, {'total': 0.0, 'per': {}})
        ordered = num(s.get('ordered'))
        d['total'] += ordered
        skl = s.get('sklad') or ''
        d['per'][skl] = d['per'].get(skl, 0.0) + ordered

    low = []
    stock_rows = list(CapStock.objects.filter(profile=profile).values_list('raw', flat=True))
    for s in stock_rows:
        bc = str(s.get('barcode') or '')
        if not bc:
            continue
        if sklad == 'Все склады':
            stock = num(s.get('returns_en_route')) + num(s.get('total_in_warehouses'))
        else:
            stock = num((s.get('warehouses') or {}).get(sklad))
        info = sales_by_barcode.get(bc) or {'total': 0.0, 'per': {}}
        ordered = info['total'] if sklad == 'Все склады' else info['per'].get(sklad, 0.0)
        if ordered <= 0:
            continue
        avg_per_day = ordered / days
        if avg_per_day <= 0:
            continue
        days_left = stock / avg_per_day
        if days_left < delivery_days:
            low.append({
                'article': s.get('article') or '',
                'size': s.get('size') or '',
                'days_left': int(round(days_left)),
                'stock': int(round(stock)),
            })
    low.sort(key=lambda x: x['days_left'])

    # --- Tannarxsiz tovarlar (costs sahifasi logikasi) ---
    code_info = base_code_info(profile)
    defined_codes = {str(c) for c in Cost.objects.filter(profile=profile)
                     .exclude(code='').values_list('code', flat=True)}
    missing = [code_info[c] for c in code_info if c not in defined_codes]
    missing.sort(key=lambda d: (d.get('article') or d.get('code') or ''))

    return {
        'low_stock_count': len(low),
        'low_stock_preview': low[:limit],
        'low_stock_extra': max(0, len(low) - limit),
        'missing_cost_count': len(missing),
        'missing_cost_preview': missing[:limit],
        'missing_cost_extra': max(0, len(missing) - limit),
    }


def set_cost_by_barcode(profile, barcode, code, cost):
    """Inline cost edit from the capitalization table (barcode priority, code fallback).

    Mirrors saveCostForBarcode: update the barcode-keyed Cost if present, else clone
    a code-matched sample into a new barcode-keyed Cost. Recompute (base AC depends on cost)."""
    barcode = _trunc('barcode', barcode)
    code = _trunc('code', code)
    cost = num(cost)
    existing = Cost.objects.filter(profile=profile).exclude(barcode='').filter(barcode=barcode).first()
    if existing:
        existing.cost = cost
        existing.cost_future = cost
        existing.save()
    else:
        sample = Cost.objects.filter(profile=profile, code=code).first()
        Cost.objects.create(
            profile=profile, barcode=barcode, code=code,
            brand=sample.brand if sample else '', article=sample.article if sample else '',
            name=sample.name if sample else '', group=sample.group if sample else '',
            kluch=code, cost=cost, cost_future=cost)
    recompute_profile(profile)
    return {'ok': True}
