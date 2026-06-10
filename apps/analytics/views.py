from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.accounts.views import get_active_profile
from apps.reports.models import BaseRow

from . import services


def _has_data(profile):
    return BaseRow.objects.filter(profile=profile).exists()


@login_required
def dashboard(request):
    profile = get_active_profile(request)
    report_num = request.GET.get('report') or None
    month = request.GET.get('month') or None

    kpi = services.compute_kpi(profile, report_num=report_num, month=month)
    filters = services.list_filters(profile)
    products = services.by_product(profile, report_num=report_num, month=month, limit=10)
    weeks = services.by_week(profile, report_num=report_num, month=month)

    return render(request, 'analytics/dashboard.html', {
        'active_page': 'dashboard',
        'profile': profile,
        'kpi': kpi,
        'products': products,
        'weeks': weeks,
        'currency': profile.currency,
        'filter_reports': filters['reports'],
        'selected_report': report_num or '',
        'has_data': kpi['row_count'] > 0,
    })


@login_required
def calculator(request):
    profile = get_active_profile(request)
    kpi = services.compute_kpi(profile)
    return render(request, 'analytics/calculator.html', {
        'active_page': 'calculator',
        'profile': profile,
        'kpi_json': kpi,
        'calc_ctx_json': {
            'currency': profile.currency,
            'tax_rate': float(profile.tax_rate),
            'profile_id': profile.id,
            'profile_name': profile.name,
            'base_count': kpi['row_count'],
        },
    })


@login_required
def smart(request):
    profile = get_active_profile(request)
    products = services.by_product(profile)
    return render(request, 'analytics/smart.html', {
        'active_page': 'analytics',
        'profile': profile,
        'products_json': [{
            'article': p['article'] or '', 'product': p['product'] or '',
            'revenue': p['revenue'] or 0, 'profit': p['profit'] or 0,
            'cost': p['cost'] or 0, 'qty': p['qty'] or 0,
            'buyouts_qty': p['buyouts_qty'] or 0, 'returns_qty': p['returns_qty'] or 0,
            'returns_rub': p['returns_rub'] or 0,
            'margin_pct': p['margin_pct'] or 0, 'roi_pct': p['roi_pct'] or 0,
        } for p in products],
        'warehouses_json': services.by_warehouse(profile),
        'calc_json': services.smart_calc_rows(profile),
    })


@login_required
def charts(request):
    profile = get_active_profile(request)
    report_num = request.GET.get('report') or None
    month = request.GET.get('month') or None

    kpi = services.compute_kpi(profile, report_num=report_num, month=month)
    products = services.by_product(profile, report_num=report_num, month=month)
    weeks_raw = services.by_week(profile, report_num=report_num, month=month)
    warehouses = services.by_warehouse(profile, report_num=report_num, month=month)
    days = services.by_day(profile, report_num=report_num, month=month)
    months = services.by_month_trend(profile, report_num=report_num, month=month)

    # JSON-safe slices for the charts (article/product/revenue; week as label string)
    products_json = [{'article': p['article'] or '—', 'product': p['product'] or '',
                      'revenue': p['revenue'] or 0} for p in products]
    weeks_json = [{'week': w['week'].isoformat() if w['week'] else '',
                   'revenue': w['revenue'] or 0, 'profit': w['profit'] or 0,
                   'margin_pct': w['margin_pct'] or 0} for w in weeks_raw]

    best_day = max(days, key=lambda d: d['revenue'], default=None)
    top_warehouse = warehouses[0] if warehouses else None
    top10_share = 0
    if kpi['revenue']:
        top10_share = round(sum(p['revenue'] for p in products_json[:10]) / kpi['revenue'] * 100)

    return render(request, 'analytics/charts.html', {
        'active_page': 'charts',
        'profile': profile,
        'currency': profile.currency,
        'kpi': kpi,
        'products_json': products_json,
        'weeks_json': weeks_json,
        'warehouses_json': warehouses,
        'days_json': days,
        'months_json': months,
        'product_count': len(products_json),
        'warehouse_count': len(warehouses),
        'month_count': len(months),
        'best_day': best_day,
        'top_warehouse': top_warehouse,
        'top10_share': top10_share,
        'filter_reports': services.list_filters(profile)['reports'],
        'filter_months': services.month_keys(profile),
        'selected_report': report_num or '',
        'selected_month': month or '',
        'has_data': kpi['row_count'] > 0,
    })


@login_required
def fines(request):
    profile = get_active_profile(request)
    report_num = request.GET.get('report') or None
    month = request.GET.get('month') or None
    ptype = request.GET.get('type') or None

    penalty = services.by_penalty_type(profile, report_num=report_num, month=month)
    if ptype:
        penalty['types'] = [t for t in penalty['types'] if t['type'] == ptype]
        penalty['allRows'] = [r for r in penalty['allRows'] if r['type'] == ptype]
        penalty['grandTotal'] = sum(t['total'] for t in penalty['types'])
        penalty['totalCount'] = sum(t['count'] for t in penalty['types'])

    kpi = services.compute_kpi(profile, report_num=report_num, month=month)

    return render(request, 'analytics/fines.html', {
        'active_page': 'fines',
        'profile': profile,
        'penalty_json': penalty,
        'total_revenue': kpi['revenue'],
        'filter_reports': services.list_filters(profile)['reports'],
        'filter_months': services.month_keys(profile),
        'filter_types': services.penalty_types(profile),
        'selected_report': report_num or '',
        'selected_month': month or '',
        'selected_type': ptype or '',
        'currency': profile.currency,
        'has_data': _has_data(profile),
    })


@login_required
def monthly(request):
    profile = get_active_profile(request)
    months = services.by_month(profile)

    total_profit = sum(m['kpi']['net_profit'] for m in months)
    total_revenue = sum(m['kpi']['revenue'] for m in months)
    avg_profit = (total_profit / len(months)) if months else 0
    total_rows = sum(m['row_count'] for m in months)
    best_month = max(months, key=lambda m: m['kpi']['net_profit'], default=None)

    return render(request, 'analytics/monthly.html', {
        'active_page': 'monthly',
        'profile': profile,
        'months_json': months,
        'total_profit': total_profit,
        'total_revenue': total_revenue,
        'avg_profit': avg_profit,
        'total_rows': total_rows,
        'best_month_key': best_month['ymKey'] if best_month else '',
        'best_month_profit': best_month['kpi']['net_profit'] if best_month else 0,
        'currency': profile.currency,
        'has_data': bool(months),
    })


@login_required
def abc(request):
    profile = get_active_profile(request)
    rows = services.by_product(profile)
    abc_revenue = services.abc_analysis(rows, 'revenue')
    abc_profit = services.abc_analysis(rows, 'profit')
    count_by_cat = {'A': 0, 'B': 0, 'C': 0}
    for p in abc_revenue:
        cat = p.get('revenue_cat')
        if cat in count_by_cat:
            count_by_cat[cat] += 1
    return render(request, 'analytics/abc.html', {
        'active_page': 'abc',
        'profile': profile,
        'abc_revenue': abc_revenue,
        'abc_profit': abc_profit,
        'count_by_cat': count_by_cat,
        'total_products': len(rows),
        'currency': profile.currency,
        'has_data': bool(rows),
    })


@login_required
def products(request):
    profile = get_active_profile(request)
    rows = services.by_product(profile)
    return render(request, 'analytics/products.html', {
        'active_page': 'products',
        'profile': profile,
        'products_json': rows,
        'currency': profile.currency,
        'has_data': bool(rows),
    })


@login_required
def pnl(request):
    profile = get_active_profile(request)
    weeks = services.by_week(profile)

    keys = ('revenue', 'qty', 'returns_qty', 'commission', 'acquiring',
            'logistics', 'storage', 'fines', 'promotion', 'cost', 'tax', 'profit')
    totals = {k: 0 for k in keys}
    for w in weeks:
        for k in keys:
            totals[k] += w.get(k) or 0
    totals['margin_pct'] = (totals['profit'] / totals['revenue'] * 100) if totals['revenue'] else 0
    totals['roi_pct'] = (totals['profit'] / totals['cost'] * 100) if totals['cost'] else 0

    return render(request, 'analytics/pnl.html', {
        'active_page': 'pnl',
        'profile': profile,
        'weeks': weeks,
        'totals': totals,
        'currency': profile.currency,
        'has_data': bool(weeks),
    })