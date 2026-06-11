import csv
import json

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from apps.accounts.views import get_active_profile
from apps.analytics import services as analytics_services

from . import services
from .models import BaseRow, Cost, ExtExpense, ListReport, SelfPurchase, UploadHistory

MAX_UPLOAD_BYTES = 30 * 1024 * 1024  # 30 MB
DETAIL_EXTS = ('.xlsx', '.xls', '.zip', '.csv')
LIST_EXTS = ('.xlsx', '.xls')


def _validate(uploaded, allowed_exts):
    if uploaded is None:
        return "Fayl tanlanmadi"
    name = (uploaded.name or '').lower()
    if not name.endswith(allowed_exts):
        return f"Noto'g'ri fayl turi. Ruxsat: {', '.join(allowed_exts)}"
    if uploaded.size > MAX_UPLOAD_BYTES:
        return f"Fayl juda katta (maksimum {MAX_UPLOAD_BYTES // 1024 // 1024} MB)"
    return None


@login_required
def upload_page(request):
    profile = get_active_profile(request)
    list_reports = list(ListReport.objects.filter(profile=profile))
    loaded_report_nums = set(
        BaseRow.objects.filter(profile=profile).values_list('report_num', flat=True).distinct()
    )
    for lr in list_reports:
        lr.is_loaded = lr.report_num in loaded_report_nums
    ctx = {
        'active_page': 'upload',
        'base_count': BaseRow.objects.filter(profile=profile).count(),
        'list_count': ListReport.objects.filter(profile=profile).count(),
        'costs_count': Cost.objects.filter(profile=profile).count(),
        'list_reports': list_reports,
        'uploads': list(UploadHistory.objects.filter(profile=profile)[:50]),
    }
    return render(request, 'reports/upload.html', ctx)


@login_required
@require_POST
def upload_detail(request):
    profile = get_active_profile(request)
    uploaded = request.FILES.get('file')
    err = _validate(uploaded, DETAIL_EXTS)
    if err:
        return JsonResponse({'ok': False, 'error': err}, status=400)
    override = request.POST.get('report_num') or None
    try:
        parse_result = services.parse_uploaded(uploaded, 'detail')
        result = services.ingest_detail(profile, parse_result, user=request.user,
                                         override_report_num=override)
    except Exception as e:  # noqa: BLE001
        return JsonResponse({'ok': False, 'error': str(e)}, status=400)
    return JsonResponse({'ok': True, **result})


@login_required
@require_POST
def upload_list(request):
    profile = get_active_profile(request)
    uploaded = request.FILES.get('file')
    err = _validate(uploaded, LIST_EXTS)
    if err:
        return JsonResponse({'ok': False, 'error': err}, status=400)
    try:
        parse_result = services.parse_uploaded(uploaded, 'list')
        result = services.ingest_list(profile, parse_result, user=request.user)
    except Exception as e:  # noqa: BLE001
        return JsonResponse({'ok': False, 'error': str(e)}, status=400)
    return JsonResponse({'ok': True, **result})


@login_required
def list_reports_page(request):
    profile = get_active_profile(request)
    reports = list(ListReport.objects.filter(profile=profile).order_by('-date_from'))
    loaded = set(BaseRow.objects.filter(profile=profile).values_list('report_num', flat=True).distinct())

    for r in reports:
        r.is_loaded = r.report_num in loaded
        r.week_num = r.date_from.isocalendar()[1] if r.date_from else ''

    if request.GET.get('format') == 'csv':
        return _list_csv(reports, loaded)

    def total(attr):
        return sum(getattr(r, attr) or 0 for r in reports)

    totals = {
        'sale': total('sale_total'), 'to_pay': total('to_pay'),
        'logistics': total('logistics_cost'), 'storage': total('storage_cost'),
        'fines': total('fines_total'), 'other': total('other_deductions'),
        'total_to_pay': total('total_to_pay'),
    }
    return render(request, 'reports/list_reports.html', {
        'active_page': 'list-reports',
        'profile': profile,
        'currency': profile.currency,
        'reports': reports,
        'totals': totals,
        'loaded_count': len(loaded & {r.report_num for r in reports}),
        'all_loaded': all(r.is_loaded for r in reports) if reports else False,
        'has_data': bool(reports),
    })


def _list_csv(reports, loaded):
    resp = HttpResponse(content_type='text/csv; charset=utf-8')
    resp['Content-Disposition'] = 'attachment; filename="aira-spisok-otchetov.csv"'
    resp.write('﻿')
    w = csv.writer(resp, delimiter=';')
    w.writerow(['№ отчёта', 'Юр. лицо', 'Дата начала', 'Дата конца', 'Тип', 'Продажа',
                'К перечислению', 'Логистика', 'Хранение', 'Штрафы', 'Прочие',
                'Итого к оплате', '#Неделя', 'Подробный'])
    for r in reports:
        w.writerow([r.report_num, r.legal_entity, r.date_from or '', r.date_to or '',
                    r.report_type, r.sale_total, r.to_pay, r.logistics_cost, r.storage_cost,
                    r.fines_total, r.other_deductions, r.total_to_pay,
                    r.date_from.isocalendar()[1] if r.date_from else '',
                    'HA' if r.report_num in loaded else "YO'Q"])
    return resp


@login_required
def report_export(request):
    """Download one weekly report (by report_num) as .xlsx — a KPI summary plus a
    per-product sales & profit/loss sheet. Query param: ?report=<report_num>.

    Requires the Подробный отчёт (БАЗА rows) for that report to be loaded; without
    it there is no per-product detail to export."""
    from django.http import Http404
    from django.utils.text import slugify

    from apps.analytics.excel import build_report_workbook

    profile = get_active_profile(request)
    report_num = request.GET.get('report') or ''
    lr = ListReport.objects.filter(profile=profile, report_num=report_num).first()
    if not lr or not BaseRow.objects.filter(profile=profile, report_num=report_num).exists():
        raise Http404("Bu achot uchun Подробный отчёт yuklanmagan")

    period = ''
    if lr.date_from and lr.date_to:
        period = f"{lr.date_from:%d.%m.%Y} – {lr.date_to:%d.%m.%Y}"
        week = lr.date_from.isocalendar()[1]
        period = f"{period}  ·  {week}-hafta"

    wb = build_report_workbook(
        title=f'Haftalik hisobot — № {report_num}',
        kpi=analytics_services.compute_kpi(profile, report_num=report_num),
        products=analytics_services.by_product(profile, report_num=report_num),
        currency=profile.currency,
        subtitle=period or profile.currency,
    )
    # Name the file by the period it covers (from–to). Fall back to the report
    # number when the report has no dates.
    if lr.date_from and lr.date_to:
        fname = f'aira-haftalik-{lr.date_from:%d.%m.%Y}-{lr.date_to:%d.%m.%Y}.xlsx'
    else:
        fname = f'aira-achot-{slugify(report_num)}.xlsx'
    return _xlsx_response(wb, fname)


def _xlsx_response(wb, filename):
    """Serialize an openpyxl Workbook into an attachment HttpResponse."""
    resp = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    resp['Content-Disposition'] = f'attachment; filename="{filename}"'
    wb.save(resp)
    return resp


@login_required
@require_POST
def delete_report(request):
    """Delete a single ListReport and (if loaded) its БАЗА rows."""
    profile = get_active_profile(request)
    report_num = request.POST.get('report_num', '')
    ListReport.objects.filter(profile=profile, report_num=report_num).delete()
    n, _ = BaseRow.objects.filter(profile=profile, report_num=report_num).delete()
    return JsonResponse({'ok': True, 'base_deleted': n})


@login_required
@require_POST
def clear_list(request):
    """Delete all ListReports (keeps БАЗА and costs)."""
    profile = get_active_profile(request)
    n, _ = ListReport.objects.filter(profile=profile).delete()
    return JsonResponse({'ok': True, 'deleted': n})


PAGE_SIZE = 50


@login_required
def base_page(request):
    profile = get_active_profile(request)
    report = request.GET.get('report') or None
    article = request.GET.get('article') or None
    op_type = request.GET.get('type') or None
    search = request.GET.get('q') or None

    qs = analytics_services.base_rows_queryset(profile, report, article, op_type, search)

    if request.GET.get('format') == 'csv':
        return _base_csv(qs)

    kpi = analytics_services.kpi_for_queryset(qs)
    paginator = Paginator(qs, PAGE_SIZE)
    page = paginator.get_page(request.GET.get('page'))
    rows = [analytics_services.base_row_display(r) for r in page.object_list]

    # Preserve current filters in pagination links (minus page)
    params = request.GET.copy()
    params.pop('page', None)
    querystring = params.urlencode()

    return render(request, 'reports/base.html', {
        'active_page': 'base',
        'profile': profile,
        'currency': profile.currency,
        'kpi': kpi,
        'rows': rows,
        'page_obj': page,
        'total_rows': BaseRow.objects.filter(profile=profile).count(),
        'filtered_count': paginator.count,
        'reports': analytics_services.list_filters(profile)['reports'],
        'articles': analytics_services.base_articles(profile),
        'sel_report': report or '', 'sel_article': article or '',
        'sel_type': op_type or '', 'search': search or '',
        'querystring': querystring,
        'has_data': BaseRow.objects.filter(profile=profile).exists(),
    })


def _base_csv(qs):
    resp = HttpResponse(content_type='text/csv; charset=utf-8')
    resp['Content-Disposition'] = 'attachment; filename="aira-baza.csv"'
    resp.write('﻿')
    w = csv.writer(resp, delimiter=';')
    w.writerow(['№ отчёта', 'Тип', 'Артикул', 'Товар', 'Прод.шт', 'Возвр.шт', 'Выручка',
                'К перечисл', 'Комиссия', 'Эквайринг', 'Лог.прям', 'Лог.обр',
                'Штраф', 'Хранение', 'Себест', 'Налог', 'Опл.РС', 'Дата'])
    for r in qs.iterator():
        d = analytics_services.base_row_display(r)
        w.writerow([d['report_num'], d['badge_label'], d['article'], d['product'],
                    d['D'], d['E'], d['I'], d['J'], d['K'], d['L'], d['S'], d['T'],
                    d['fine'], d['AD'], d['AC'], d['AB'], d['Y'],
                    d['date'].isoformat() if d['date'] else ''])
    return resp


@login_required
@require_POST
def clear_base(request):
    """Delete all of the active profile's БАЗА rows (keeps list/costs)."""
    profile = get_active_profile(request)
    n, _ = BaseRow.objects.filter(profile=profile).delete()
    return JsonResponse({'ok': True, 'deleted': n})


@login_required
@require_POST
def clear_report(request):
    """Delete БАЗА rows of a single report_num."""
    profile = get_active_profile(request)
    report_num = request.POST.get('report_num', '')
    n, _ = BaseRow.objects.filter(profile=profile, report_num=report_num).delete()
    return JsonResponse({'ok': True, 'deleted': n})


@login_required
@require_POST
def clear_all(request):
    """Delete all of the active profile's report data (keeps the profile/settings)."""
    profile = get_active_profile(request)
    BaseRow.objects.filter(profile=profile).delete()
    ListReport.objects.filter(profile=profile).delete()
    UploadHistory.objects.filter(profile=profile).delete()
    return JsonResponse({'ok': True})


# ============================================================
# Себестоимость (costs)
# ============================================================
COST_EXTS = ('.xlsx', '.xls', '.csv')


@login_required
def costs_page(request):
    profile = get_active_profile(request)
    costs = list(Cost.objects.filter(profile=profile).order_by('brand', 'article', 'id'))
    code_info = services.base_code_info(profile)
    used_codes = set(code_info)
    defined_codes = {str(c.code) for c in costs if c.code}
    missing_codes = sorted(used_codes - defined_codes)

    for c in costs:
        c.is_used = str(c.code) in used_codes
        if not c.cost:
            c.check_label, c.check_class = 'Нет ССт', 'check-err'
        elif c.is_used:
            c.check_label, c.check_class = 'Ok', 'check-ok'
        else:
            c.check_label, c.check_class = 'Не используется', 'check-warn'

    total = len(costs)
    used_count = sum(1 for c in costs if c.is_used)
    avg_cost = (sum(c.cost for c in costs) / total) if total else 0

    missing = [code_info[c] for c in missing_codes]

    return render(request, 'reports/costs.html', {
        'active_page': 'costs',
        'profile': profile,
        'currency': profile.currency,
        'costs': costs,
        'total': total,
        'used_count': used_count,
        'avg_cost': avg_cost,
        'missing': missing,
        'missing_count': len(missing),
        'missing_preview': missing[:5],
        'missing_examples': missing[:20],
        'missing_extra': max(0, len(missing) - 20),
        # JSON for the client-side Excel/CSV export (faithful to the original page)
        'costs_json': [
            {'brand': c.brand, 'article': c.article, 'product': c.name,
             'code': c.code, 'cost': c.cost, 'group': c.group}
            for c in costs
        ],
        'code_info_json': code_info,
    })


@login_required
@require_POST
def cost_add(request):
    profile = get_active_profile(request)
    article = (request.POST.get('article') or '').strip()
    code = (request.POST.get('code') or '').strip()
    if not article or not code:
        return JsonResponse({'ok': False, 'error': 'Artikul va Kod majburiy'}, status=400)
    Cost.objects.create(
        profile=profile, brand=(request.POST.get('brand') or '').strip(),
        article=article, name=(request.POST.get('product') or '').strip(),
        code=code, kluch=code, group=(request.POST.get('group') or '').strip(),
        cost=services.num(request.POST.get('cost')),
    )
    services.recompute_profile(profile)
    return JsonResponse({'ok': True})


@login_required
@require_POST
def cost_update(request):
    profile = get_active_profile(request)
    cost = Cost.objects.filter(profile=profile, id=request.POST.get('id')).first()
    if not cost:
        return JsonResponse({'ok': False, 'error': 'Topilmadi'}, status=404)
    field = request.POST.get('field')
    value = request.POST.get('value', '')
    allowed = {'brand', 'article', 'product', 'code', 'cost', 'group'}
    if field not in allowed:
        return JsonResponse({'ok': False, 'error': 'Noto‘g‘ri maydon'}, status=400)
    if field == 'cost':
        cost.cost = services.num(value)
    elif field == 'product':
        cost.name = value.strip()
    elif field == 'code':
        cost.code = value.strip()
        cost.kluch = (cost.supply_num or '') + value.strip()
    else:
        setattr(cost, field, value.strip())
    cost.save()
    services.recompute_profile(profile)
    return JsonResponse({'ok': True})


@login_required
@require_POST
def cost_delete(request):
    profile = get_active_profile(request)
    Cost.objects.filter(profile=profile, id=request.POST.get('id')).delete()
    services.recompute_profile(profile)
    return JsonResponse({'ok': True})


@login_required
@require_POST
def costs_clear(request):
    profile = get_active_profile(request)
    n, _ = Cost.objects.filter(profile=profile).delete()
    services.recompute_profile(profile)
    return JsonResponse({'ok': True, 'deleted': n})


@login_required
@require_POST
def costs_import(request):
    profile = get_active_profile(request)
    uploaded = request.FILES.get('file')
    err = _validate(uploaded, COST_EXTS)
    if err:
        return JsonResponse({'ok': False, 'error': err}, status=400)
    try:
        rows = services.parse_costs_file(uploaded)
        result = services.import_costs(profile, rows)
    except Exception as e:  # noqa: BLE001
        return JsonResponse({'ok': False, 'error': str(e)}, status=400)
    return JsonResponse({'ok': True, **result})


# ============================================================
# Капитализация (capitalization)
# ============================================================
CAP_EXTS = ('.xlsx', '.xls', '.zip')
CAP_KINDS = ('stock', 'sales', 'nomenclature')


@login_required
def capitalization_page(request):
    profile = get_active_profile(request)
    data = services.cap_data(profile)
    return render(request, 'analytics/capitalization.html', {
        'active_page': 'capitalization',
        'profile': profile,
        'cap_stock_json': data['stock'],
        'cap_sales_json': data['sales'],
        'cap_nomenclature_json': data['nomenclature'],
        'cap_params_json': data['params'],
        'cap_costs_json': data['costs'],
    })


@login_required
@require_POST
def cap_upload(request):
    profile = get_active_profile(request)
    kind = request.POST.get('kind')
    if kind not in CAP_KINDS:
        return JsonResponse({'ok': False, 'error': 'Noto‘g‘ri tur'}, status=400)
    uploaded = request.FILES.get('file')
    err = _validate(uploaded, CAP_EXTS)
    if err:
        return JsonResponse({'ok': False, 'error': err}, status=400)
    try:
        rows = services.parse_cap_file(uploaded, kind)
        if not rows:
            return JsonResponse({'ok': False, 'error': 'Fayl strukturasi mos kelmadi yoki bo‘sh'}, status=400)
        result = services.ingest_cap(profile, kind, rows)
    except Exception as e:  # noqa: BLE001
        return JsonResponse({'ok': False, 'error': str(e)}, status=400)
    return JsonResponse({'ok': True, **result})


@login_required
@require_POST
def cap_clear(request):
    profile = get_active_profile(request)
    kind = request.POST.get('kind')
    if kind not in CAP_KINDS:
        return JsonResponse({'ok': False, 'error': 'Noto‘g‘ri tur'}, status=400)
    return JsonResponse({'ok': True, **services.clear_cap(profile, kind)})


@login_required
@require_POST
def cap_params_save(request):
    profile = get_active_profile(request)
    params = services.save_cap_params(profile, request.POST)
    return JsonResponse({'ok': True, 'params': params})


@login_required
@require_POST
def cap_cost_set(request):
    profile = get_active_profile(request)
    result = services.set_cost_by_barcode(
        profile, request.POST.get('barcode'), request.POST.get('code'),
        request.POST.get('cost'))
    return JsonResponse(result)


# ============================================================
# Хранение (storage) — read-only aggregation over BaseRow.storage
# ============================================================
@login_required
def storage_page(request):
    profile = get_active_profile(request)
    report_num = request.GET.get('report') or None
    month = request.GET.get('month') or None
    data = analytics_services.storage_breakdown(profile, report_num=report_num, month=month)

    if request.GET.get('format') == 'csv':
        return _storage_csv(data['rows'])

    # Attach the date range to each report row (from ListReport).
    lr_map = {lr.report_num: lr for lr in ListReport.objects.filter(profile=profile)}
    for r in data['reports']:
        lr = lr_map.get(r['report_num'])
        r['date_from'] = lr.date_from if lr else None
        r['date_to'] = lr.date_to if lr else None
        r['share_pct'] = (r['total'] / data['total'] * 100) if data['total'] else 0

    return render(request, 'reports/storage.html', {
        'active_page': 'storage',
        'profile': profile,
        'currency': profile.currency,
        'data': data,
        'filter_reports': analytics_services.list_filters(profile)['reports'],
        'filter_months': analytics_services.month_keys(profile),
        'selected_report': report_num or '',
        'selected_month': month or '',
        'has_data': data['row_count'] > 0,
    })


def _storage_csv(rows):
    resp = HttpResponse(content_type='text/csv; charset=utf-8')
    resp['Content-Disposition'] = 'attachment; filename="aira-storage.csv"'
    resp.write('﻿')
    w = csv.writer(resp, delimiter=';')
    w.writerow(['Sana', 'Achot', 'Sklad', 'Brand', 'Artikul', 'Tovar', 'Saqlash'])
    for r in rows:
        w.writerow([r['sale_date'].isoformat() if r['sale_date'] else '', r['report_num'],
                    r['warehouse'], r['brand'], r['article'],
                    (r['product_name'] or '').replace(';', ' '), round(r['storage'] or 0, 2)])
    return resp


# ============================================================
# Внешние расходы (ext-expenses)
# ============================================================
EXPENSE_CATEGORIES = ['Реклама', 'Маркетинг', 'Закупка товара', 'Логистика',
                      'Налоги', 'Зарплата', 'Аренда', 'Услуги', 'Другое']


@login_required
def ext_expenses_page(request):
    profile = get_active_profile(request)
    all_items = list(ExtExpense.objects.filter(profile=profile))

    f_cat = request.GET.get('category') or ''
    f_month = request.GET.get('month') or ''

    # Category breakdown (over ALL items, like the original)
    by_cat = {}
    for e in all_items:
        cat = e.category or 'Другое'
        d = by_cat.setdefault(cat, {'cat': cat, 'count': 0, 'total': 0})
        d['count'] += 1
        d['total'] += e.amount or 0
    total_amount = sum(e.amount or 0 for e in all_items)
    categories = sorted(by_cat.values(), key=lambda d: d['total'], reverse=True)
    for d in categories:
        d['pct'] = (d['total'] / total_amount * 100) if total_amount else 0

    months = sorted({(e.date.strftime('%Y-%m')) for e in all_items if e.date}, reverse=True)

    # Filtered list
    items = all_items
    if f_cat:
        items = [e for e in items if (e.category or 'Другое') == f_cat]
    if f_month:
        items = [e for e in items if e.date and e.date.strftime('%Y-%m') == f_month]
    items = sorted(items, key=lambda e: e.date or _to_date('1900-01-01'), reverse=True)
    for e in items:
        e.cat_class = _CAT_CLASS.get(e.category, 'cat-boshqa')
    filtered_total = sum(e.amount or 0 for e in items)

    return render(request, 'reports/ext_expenses.html', {
        'active_page': 'ext_expenses',
        'profile': profile,
        'currency': profile.currency,
        'items': items,
        'all_count': len(all_items),
        'total_amount': total_amount,
        'filtered_total': filtered_total,
        'categories': categories,
        'category_count': len(categories),
        'month_count': len(months),
        'months': months,
        'avg': (total_amount / len(all_items)) if all_items else 0,
        'all_categories': EXPENSE_CATEGORIES,
        'sel_category': f_cat,
        'sel_month': f_month,
        'has_data': bool(all_items),
    })


_CAT_CLASS = {
    'Реклама': 'cat-reklama', 'Маркетинг': 'cat-marketing',
    'Закупка товара': 'cat-tovarlar', 'Логистика': 'cat-logistika',
    'Налоги': 'cat-soliq', 'Зарплата': 'cat-boshqa', 'Аренда': 'cat-boshqa',
    'Услуги': 'cat-boshqa', 'Другое': 'cat-boshqa',
}


@login_required
@require_POST
def ext_expense_save(request):
    profile = get_active_profile(request)
    name = (request.POST.get('description') or '').strip()
    amount = services.num(request.POST.get('amount'))
    if not name or not amount:
        return JsonResponse({'ok': False, 'error': 'Tavsif va summa majburiy'}, status=400)
    date = services._to_date(request.POST.get('date'))
    fields = {
        'name': name[:255],
        'category': (request.POST.get('category') or 'Другое').strip()[:128],
        'date': date,
        'month': date.strftime('%Y-%m') if date else '',
        'amount': amount,
        'note': (request.POST.get('note') or '').strip()[:255],
    }
    item_id = request.POST.get('id')
    if item_id:
        n = ExtExpense.objects.filter(profile=profile, id=item_id).update(**fields)
        if not n:
            return JsonResponse({'ok': False, 'error': 'Topilmadi'}, status=404)
    else:
        ExtExpense.objects.create(profile=profile, **fields)
    return JsonResponse({'ok': True})


@login_required
@require_POST
def ext_expense_delete(request):
    profile = get_active_profile(request)
    ExtExpense.objects.filter(profile=profile, id=request.POST.get('id')).delete()
    return JsonResponse({'ok': True})


# ============================================================
# Самовыкупы (self-purchase)
# ============================================================
@login_required
def self_purchase_page(request):
    profile = get_active_profile(request)
    items = list(SelfPurchase.objects.filter(profile=profile).order_by('-date', '-id'))
    total_cost = sum(i.cost for i in items)
    total_logistics = sum(i.logistics for i in items)
    grand_total = total_cost + total_logistics
    count = len(items)
    return render(request, 'reports/self_purchase.html', {
        'active_page': 'self_purchase',
        'profile': profile,
        'currency': profile.currency,
        'items': items,
        'count': count,
        'total_cost': total_cost,
        'total_logistics': total_logistics,
        'grand_total': grand_total,
        'avg': (grand_total / count) if count else 0,
        'has_data': count > 0,
    })


@login_required
@require_POST
def self_purchase_save(request):
    profile = get_active_profile(request)
    srid = (request.POST.get('srid') or '').strip()
    if not srid:
        return JsonResponse({'ok': False, 'error': 'SRID majburiy'}, status=400)
    cost = services.num(request.POST.get('cost'))
    logistics = services.num(request.POST.get('logistics'))
    fields = {
        'srid': srid[:128],
        'article': (request.POST.get('article') or '').strip()[:128],
        'date': services._to_date(request.POST.get('date')),
        'cost': cost, 'logistics': logistics, 'total': cost + logistics,
        'note': (request.POST.get('note') or '').strip()[:255],
    }
    item_id = request.POST.get('id')
    if item_id:
        n = SelfPurchase.objects.filter(profile=profile, id=item_id).update(**fields)
        if not n:
            return JsonResponse({'ok': False, 'error': 'Topilmadi'}, status=404)
    else:
        SelfPurchase.objects.create(profile=profile, **fields)
    services.recompute_profile(profile)
    return JsonResponse({'ok': True})


@login_required
@require_POST
def self_purchase_delete(request):
    profile = get_active_profile(request)
    SelfPurchase.objects.filter(profile=profile, id=request.POST.get('id')).delete()
    services.recompute_profile(profile)
    return JsonResponse({'ok': True})


@login_required
@require_POST
def recompute(request):
    """Re-run the formula engine over the profile's stored rows (cache refresh)."""
    profile = get_active_profile(request)
    result = services.recompute_profile(profile)
    return JsonResponse({'ok': True, **result})


@login_required
def backup(request):
    """Export the active profile's data as a JSON download."""
    profile = get_active_profile(request)
    data = {
        'profile': {'name': profile.name, 'brand': profile.brand, 'inn': profile.inn},
        'list_reports': list(ListReport.objects.filter(profile=profile).values()),
        'costs': list(Cost.objects.filter(profile=profile).values()),
        'self_purchases': list(SelfPurchase.objects.filter(profile=profile).values()),
        'base': list(BaseRow.objects.filter(profile=profile).values('report_num', 'srid', 'raw')),
    }
    payload = json.dumps(data, ensure_ascii=False, default=str, indent=2)
    resp = HttpResponse(payload, content_type='application/json')
    resp['Content-Disposition'] = 'attachment; filename="aira-backup.json"'
    return resp