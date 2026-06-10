"""SQL aggregation services — the backend equivalent of baza-formulas.js
calculateKPI / byProduct / byWeek / byWarehouse / byPenaltyType.

Per-row formula outputs are already stored on BaseRow columns, so the totals are
plain Postgres SUM/GROUP BY over the same numbers the JS summed — identical results,
no Python row loops.
"""
from django.db.models import Count, F, Sum
from django.db.models.functions import TruncMonth

from apps.reports.models import BaseRow

# BaseRow column -> KPI key (sums)
_SUM_FIELDS = {
    'revenue': 'revenue',            # I
    'net_qty': 'net_qty',            # H  (== sales_qty)
    'sold_qty': 'buyouts_qty',       # D
    'returned_qty': 'returns_qty',   # E
    'sold_rub': 'buyouts_rub',       # F
    'returned_rub': 'returns_rub',   # G
    'commission': 'commission',      # K
    'acquiring': 'acquiring',        # L
    'logistics_direct': 'logistics_direct',  # S
    'logistics_back': 'logistics_back',      # T
    'storage': 'storage',            # AD
    'fine': 'fines',                 # CO (raw)
    'wb_correction': 'wb_correction',  # CP (raw)
    'paid_acceptance': 'paid_reception',  # V
    'pl_deduction': 'pl_deductions',      # W
    'promotion': 'promotion',        # AE
    'transit': 'transit',            # AF
    'supply_change': 'supply_change',  # AG
    'jem': 'jem',                    # AH
    'utilization': 'utilization',    # AI
    'review_cancel': 'review_cancel',  # AJ
    'other_deduction': 'other_ded',  # AK
    'comp_brak': 'comp_brak',        # O
    'comp_uscherb': 'comp_uscherb',  # P
    'cost': 'cost',                  # AC
    'tax_base': 'tax_base',          # AA
    'tax': 'tax',                    # AB
    'ext_expenses': 'ext_expenses',  # AN
    'samovikup_cost': 'samovikup_costs',  # AL
    'to_pay_rs': 'to_pay_rs',        # Y
    'wb_realized': 'wb_realized',    # Z
    'cashback': 'cashback',          # X
}


def base_queryset(profile, report_num=None, month=None):
    qs = BaseRow.objects.filter(profile=profile)
    if report_num:
        qs = qs.filter(report_num=str(report_num))
    if month:  # 'YYYY-MM'
        try:
            y, m = month.split('-')
            qs = qs.filter(sale_date__year=int(y), sale_date__month=int(m))
        except (ValueError, AttributeError):
            pass
    return qs


def compute_kpi(profile, report_num=None, month=None):
    """Return the KPI dict (same keys/semantics as BazaFormulas.calculateKPI)."""
    return kpi_for_queryset(base_queryset(profile, report_num, month))


def kpi_for_queryset(qs):
    """KPI aggregation over an arbitrary (already profile-scoped) BaseRow queryset."""
    aggregates = {col: Sum(col) for col in _SUM_FIELDS}
    aggregates['row_count'] = Count('id')
    agg = qs.aggregate(**aggregates)

    kpi = {kpi_key: (agg[col] or 0) for col, kpi_key in _SUM_FIELDS.items()}
    kpi['row_count'] = agg['row_count'] or 0

    # Aliases matching the JS KPI object
    kpi['sales_qty'] = kpi['net_qty']
    kpi['sales_rub'] = kpi['revenue']

    kpi['logistics_total'] = kpi['logistics_direct'] + kpi['logistics_back']
    kpi['all_wb_deductions'] = (
        kpi['commission'] + kpi['acquiring'] + kpi['logistics_total']
        + kpi['storage'] + kpi['fines'] + kpi['paid_reception']
        + kpi['pl_deductions'] + kpi['promotion'] + kpi['transit']
        + kpi['supply_change'] + kpi['jem'] + kpi['utilization']
        + kpi['review_cancel'] + kpi['other_ded'])

    kpi['net_profit'] = (kpi['to_pay_rs'] - kpi['cost'] - kpi['tax']
                         - kpi['ext_expenses'] - kpi['samovikup_costs'])

    rev = kpi['revenue']
    kpi['margin_pct'] = (kpi['net_profit'] / rev * 100) if rev else 0
    kpi['roi_pct'] = (kpi['net_profit'] / kpi['cost'] * 100) if kpi['cost'] else 0
    kpi['cost_pct'] = (kpi['cost'] / rev * 100) if rev else 0
    kpi['commission_pct'] = (kpi['commission'] / rev * 100) if rev else 0
    kpi['logistics_pct'] = (kpi['logistics_total'] / rev * 100) if rev else 0
    kpi['storage_pct'] = (kpi['storage'] / rev * 100) if rev else 0
    kpi['all_ded_pct'] = (kpi['all_wb_deductions'] / rev * 100) if rev else 0
    kpi['acquiring_pct'] = (kpi['acquiring'] / rev * 100) if rev else 0
    kpi['spp_pct'] = ((rev - kpi['wb_realized']) / rev * 100) if rev else 0

    total_ops = kpi['buyouts_qty'] + kpi['returns_qty']
    kpi['buyout_pct'] = (kpi['buyouts_qty'] / total_ops * 100) if total_ops else 0
    kpi['avg_price'] = (kpi['sales_rub'] / kpi['sales_qty']) if kpi['sales_qty'] else 0

    return kpi


def by_product(profile, report_num=None, month=None, limit=None):
    """Per-product aggregation (BazaFormulas.byProduct), sorted by revenue desc."""
    qs = base_queryset(profile, report_num, month).values('article').annotate(
        product=F('product_name'), brand=F('brand'), group=F('group'),
        revenue=Sum('revenue'), qty=Sum('net_qty'),
        buyouts_qty=Sum('sold_qty'), returns_qty=Sum('returned_qty'),
        returns_rub=Sum('returned_rub'),
        commission=Sum('commission'),
        logistics=Sum('logistics_direct') + Sum('logistics_back'),
        storage=Sum('storage'), promotion=Sum('promotion'),
        fines=Sum('fine'), cashback=Sum('cashback'),
        cost=Sum('cost'), tax=Sum('tax'), to_pay_rs=Sum('to_pay_rs'),
        wb_realized=Sum('wb_realized'),
    ).order_by('-revenue')

    # СПП: only rows with revenue > 0 contribute (matches JS byProduct). Computed
    # in a second pass to avoid the `revenue` annotation shadowing the column.
    spp_rows = (base_queryset(profile, report_num, month).filter(revenue__gt=0)
                .values('article').annotate(s=Sum(F('revenue') - F('wb_realized'))))
    spp_map = {r['article']: (r['s'] or 0) for r in spp_rows}

    products = []
    for p in qs:
        profit = (p['to_pay_rs'] or 0) - (p['cost'] or 0) - (p['tax'] or 0)
        rev = p['revenue'] or 0
        p['profit'] = profit
        p['cancellations'] = 0
        p['spp_total'] = spp_map.get(p['article'], 0)
        p['margin_pct'] = (profit / rev * 100) if rev else 0
        p['roi_pct'] = (profit / p['cost'] * 100) if p['cost'] else 0
        p['spp_pct'] = (p['spp_total'] / rev * 100) if rev else 0
        products.append(p)
    return products[:limit] if limit else products


def by_week(profile, report_num=None, month=None):
    """Per-week aggregation (BazaFormulas.byWeek), sorted by week asc."""
    qs = base_queryset(profile, report_num, month).exclude(week__isnull=True).values('week').annotate(
        revenue=Sum('revenue'), qty=Sum('sold_qty'), returns_qty=Sum('returned_qty'),
        commission=Sum('commission'), acquiring=Sum('acquiring'),
        logistics=Sum('logistics_direct') + Sum('logistics_back'),
        storage=Sum('storage'), fines=Sum('fine'), promotion=Sum('promotion'),
        cost=Sum('cost'), tax=Sum('tax'), to_pay_rs=Sum('to_pay_rs'),
        wb_realized=Sum('wb_realized'),
    ).order_by('week')

    weeks = []
    for w in qs:
        profit = (w['to_pay_rs'] or 0) - (w['cost'] or 0) - (w['tax'] or 0)
        rev = w['revenue'] or 0
        w['profit'] = profit
        w['margin_pct'] = (profit / rev * 100) if rev else 0
        w['roi_pct'] = (profit / w['cost'] * 100) if w['cost'] else 0
        weeks.append(w)
    return weeks


def by_warehouse(profile, report_num=None, month=None):
    """Port of BazaFormulas.byWarehouse — only real sale/return rows (D>0 or E>0),
    grouped by warehouse, sorted by revenue desc."""
    from django.db.models import Q
    qs = (base_queryset(profile, report_num, month).exclude(warehouse='')
          .filter(Q(sold_qty__gt=0) | Q(returned_qty__gt=0))
          .values('warehouse').annotate(
              revenue=Sum('revenue'), sold_qty=Sum('sold_qty'),
              returns_qty=Sum('returned_qty'), net_qty=Sum('net_qty'))
          .order_by('-revenue'))
    rows = list(qs)
    total_rev = sum(w['revenue'] or 0 for w in rows)
    for w in rows:
        sold = w['sold_qty'] or 0
        w['return_pct'] = ((w['returns_qty'] or 0) / sold * 100) if sold else 0
        w['share_pct'] = ((w['revenue'] or 0) / total_rev * 100) if total_rev else 0
    return rows


def by_day(profile, report_num=None, month=None):
    """Per-day revenue/qty (charts daily trend). Only real sale/return rows."""
    from django.db.models import Q
    qs = (base_queryset(profile, report_num, month).filter(sale_date__isnull=False)
          .filter(Q(sold_qty__gt=0) | Q(returned_qty__gt=0))
          .values('sale_date').annotate(
              revenue=Sum('revenue'), sold=Sum('sold_qty'), ret=Sum('returned_qty'))
          .order_by('sale_date'))
    return [{'date': d['sale_date'].isoformat(), 'revenue': d['revenue'] or 0,
             'qty': (d['sold'] or 0) - (d['ret'] or 0)} for d in qs]


def by_month_trend(profile, report_num=None, month=None):
    """Per-month revenue + net profit (charts monthly trend)."""
    qs = (base_queryset(profile, report_num, month).filter(sale_date__isnull=False)
          .annotate(m=TruncMonth('sale_date')).values('m').annotate(
              revenue=Sum('revenue'), to_pay_rs=Sum('to_pay_rs'),
              cost=Sum('cost'), tax=Sum('tax')).order_by('m'))
    out = []
    for r in qs:
        profit = (r['to_pay_rs'] or 0) - (r['cost'] or 0) - (r['tax'] or 0)
        out.append({'month': r['m'].strftime('%Y-%m'),
                    'revenue': r['revenue'] or 0, 'profit': profit})
    return out


def abc_analysis(products, by='revenue'):
    """Port of BazaFormulas.abcAnalysis — assign A/B/C (Pareto) categories.

    `products` is the output of by_product(). Returns a new list (sorted by the
    chosen dimension desc) with `{by}_pct`, `{by}_cum`, `{by}_cat` keys added.
    """
    ordered = sorted(products, key=lambda p: abs(p.get(by) or 0), reverse=True)
    total = sum(abs(p.get(by) or 0) for p in ordered)
    cum = 0
    out = []
    for p in ordered:
        val = abs(p.get(by) or 0)
        pct = (val / total * 100) if total else 0
        cum += pct
        if by == 'profit' and (p.get(by) or 0) < 0:
            cat = 'Убыток'
        elif cum <= 80:
            cat = 'A'
        elif cum <= 95:
            cat = 'B'
        else:
            cat = 'C'
        q = dict(p)
        q[f'{by}_pct'] = pct
        q[f'{by}_cum'] = cum
        q[f'{by}_cat'] = cat
        out.append(q)
    return out


def base_rows_queryset(profile, report=None, article=None, op_type=None, search=None):
    """Filtered BaseRow queryset for the База table (server-side filtering)."""
    from django.db.models import Q
    qs = BaseRow.objects.filter(profile=profile)
    if report:
        qs = qs.filter(report_num=str(report))
    if article:
        qs = qs.filter(article=article)
    if op_type == 'sale':
        qs = qs.filter(sold_qty__gt=0)
    elif op_type == 'return':
        qs = qs.filter(returned_qty__gt=0)
    elif op_type == 'logistics':
        qs = qs.filter(penalty_type__icontains='Логистика')
    elif op_type == 'fine':
        qs = qs.filter(~Q(fine=0) | ~Q(promotion=0))
    if search:
        qs = qs.filter(Q(article__icontains=search) | Q(product_name__icontains=search)
                       | Q(srid__icontains=search))
    return qs.order_by('id')


def base_row_display(row):
    """Map a BaseRow to the short fields the База table renders (Excel letters)."""
    pt = row.penalty_type or ''
    if row.sold_qty > 0:
        badge_label, badge_class = 'Продажа', 'badge-sale'
    elif row.returned_qty > 0:
        badge_label, badge_class = 'Возврат', 'badge-return'
    elif 'Логистика' in pt:
        badge_label, badge_class = 'Логистика', 'badge-log'
    elif row.fine or row.promotion:
        badge_label, badge_class = 'Штраф', 'badge-fine'
    else:
        badge_label, badge_class = (pt or '—'), ''
    return {
        'report_num': row.report_num, 'badge_label': badge_label, 'badge_class': badge_class,
        'article': row.article, 'product': row.product_name, 'date': row.sale_date,
        'D': row.sold_qty, 'E': row.returned_qty, 'I': row.revenue, 'J': row.to_transfer,
        'K': row.commission, 'L': row.acquiring, 'S': row.logistics_direct,
        'T': row.logistics_back, 'fine': row.fine, 'AD': row.storage, 'AC': row.cost,
        'AB': row.tax, 'Y': row.to_pay_rs,
    }


def base_articles(profile):
    return sorted(a for a in BaseRow.objects.filter(profile=profile)
                  .exclude(article='').values_list('article', flat=True).distinct() if a)


def penalty_types(profile):
    """All distinct non-empty penalty_type values (for the fines type filter)."""
    vals = (BaseRow.objects.filter(profile=profile).exclude(penalty_type='')
            .values_list('penalty_type', flat=True).distinct())
    return sorted({v.strip() for v in vals if v and v.strip()})


def by_penalty_type(profile, report_num=None, month=None):
    """Port of BazaFormulas.byPenaltyType — group logistics/fine/correction rows
    by penalty_type. Each row's amount = raw_logistics + fine + wb_correction;
    rows with amount == 0 or no penalty_type are skipped."""
    qs = (base_queryset(profile, report_num, month).exclude(penalty_type='')
          .values('penalty_type', 'sale_date', 'report_num', 'article',
                  'product_name', 'brand', 'size', 'warehouse', 'srid',
                  'raw_logistics', 'fine', 'wb_correction'))
    groups = {}
    all_rows = []
    for r in qs:
        pt = (r['penalty_type'] or '').strip()
        if not pt:
            continue
        logistics = r['raw_logistics'] or 0
        fine = r['fine'] or 0
        wb_corr = r['wb_correction'] or 0
        total = logistics + fine + wb_corr
        if total == 0:
            continue
        row = {
            'date': r['sale_date'].isoformat() if r['sale_date'] else '',
            'report_num': r['report_num'] or '', 'article': r['article'] or '',
            'product': r['product_name'] or '', 'brand': r['brand'] or '',
            'size': r['size'] or '', 'warehouse': r['warehouse'] or '',
            'srid': r['srid'] or '', 'logistics': logistics, 'fine': fine,
            'wb_correction': wb_corr, 'amount': total,
        }
        g = groups.setdefault(pt, {'type': pt, 'total': 0, 'count': 0, 'rows': []})
        g['total'] += total
        g['count'] += 1
        g['rows'].append(row)
        all_rows.append({**row, 'type': pt})

    for g in groups.values():
        g['rows'].sort(key=lambda x: x['amount'], reverse=True)
    types = sorted(groups.values(), key=lambda t: t['total'], reverse=True)
    grand_total = sum(t['total'] for t in types)
    for t in types:
        t['share_pct'] = (t['total'] / grand_total * 100) if grand_total else 0
    return {'types': types, 'allRows': all_rows,
            'grandTotal': grand_total, 'totalCount': len(all_rows)}


def month_keys(profile):
    """Distinct 'YYYY-MM' keys present in sale_date, newest first."""
    qs = (BaseRow.objects.filter(profile=profile, sale_date__isnull=False)
          .annotate(m=TruncMonth('sale_date')).values_list('m', flat=True).distinct())
    return sorted({d.strftime('%Y-%m') for d in qs if d}, reverse=True)


def by_month(profile):
    """Per-month KPI + top product (port of the monthly page's monthsMap loop)."""
    months = []
    for ym in month_keys(profile):
        kpi = compute_kpi(profile, month=ym)
        prods = by_product(profile, month=ym)
        months.append({
            'ymKey': ym,
            'kpi': kpi,
            'row_count': kpi['row_count'],
            'product_count': len(prods),
            'top_product': prods[0] if prods else None,
        })
    return months


def smart_calc_rows(profile):
    """Trimmed per-row dataset for the Smart Аналитика explorer (client-side tabs).

    Keys mirror the letter-fields the original page reads off calculated rows
    (AT/AP/AV/warehouse_name/D/E/I/Y/AC/AB) so the ported JS works unchanged."""
    rows = base_queryset(profile).values(
        'article', 'sale_date', 'size', 'warehouse',
        'sold_qty', 'returned_qty', 'revenue', 'to_pay_rs', 'cost', 'tax')
    return [{
        'AT': r['article'] or '',
        'AP': r['sale_date'].isoformat() if r['sale_date'] else '',
        'AV': r['size'] or '',
        'warehouse_name': r['warehouse'] or '',
        'D': r['sold_qty'] or 0, 'E': r['returned_qty'] or 0, 'I': r['revenue'] or 0,
        'Y': r['to_pay_rs'] or 0, 'AC': r['cost'] or 0, 'AB': r['tax'] or 0,
    } for r in rows]


def storage_breakdown(profile, report_num=None, month=None):
    """Aggregate the Хранение (storage, column AD) charges by week / product /
    warehouse / report — the Хранение page is a read-only view over BaseRow.storage."""
    qs = base_queryset(profile, report_num, month).filter(storage__gt=0)
    total = qs.aggregate(t=Sum('storage'))['t'] or 0
    row_count = qs.count()

    weeks = list(qs.exclude(week__isnull=True).values('week')
                 .annotate(total=Sum('storage'), count=Count('id')).order_by('week'))
    max_week = max((w['total'] or 0 for w in weeks), default=1) or 1
    for w in weeks:
        w['week_label'] = w['week'].isoformat()
        w['pct'] = (w['total'] or 0) / max_week * 100

    products = list(qs.values('article', 'product_name', 'brand')
                    .annotate(total=Sum('storage'), count=Count('id')).order_by('-total'))
    max_product = (products[0]['total'] if products else 1) or 1
    for p in products:
        p['pct'] = (p['total'] or 0) / max_product * 100

    # Warehouses with their top products nested.
    wh_totals = {}
    for r in qs.values('warehouse').annotate(total=Sum('storage'), count=Count('id')):
        wh_totals[r['warehouse'] or '—'] = {'warehouse': r['warehouse'] or '—',
                                            'total': r['total'] or 0, 'count': r['count'],
                                            'products': []}
    for r in (qs.values('warehouse', 'article', 'product_name')
              .annotate(total=Sum('storage'), count=Count('id')).order_by('-total')):
        wh = wh_totals.get(r['warehouse'] or '—')
        if wh:
            wh['products'].append({'article': r['article'] or '—',
                                   'product': r['product_name'] or '',
                                   'total': r['total'] or 0, 'count': r['count']})
    warehouses = sorted(wh_totals.values(), key=lambda w: w['total'], reverse=True)
    for w in warehouses:
        w['share_pct'] = (w['total'] / total * 100) if total else 0
        w['top_products'] = w['products'][:5]
        w['extra_products'] = max(0, len(w['products']) - 5)

    reports = list(qs.values('report_num').annotate(total=Sum('storage'), count=Count('id')).order_by('-total'))

    rows = list(qs.values('sale_date', 'report_num', 'warehouse', 'brand', 'article',
                          'product_name', 'storage').order_by('-sale_date', 'id')[:500])

    return {
        'total': total, 'row_count': row_count,
        'weeks': weeks, 'products': products, 'warehouses': warehouses,
        'reports': reports, 'rows': rows,
        'avg_per_week': (total / len(weeks)) if weeks else 0,
        'avg_per_row': (total / row_count) if row_count else 0,
    }


def list_filters(profile):
    """Distinct report numbers and months for the dashboard filter bar."""
    reports = list(BaseRow.objects.filter(profile=profile)
                   .exclude(report_num='').values_list('report_num', flat=True).distinct())
    return {'reports': sorted(reports)}