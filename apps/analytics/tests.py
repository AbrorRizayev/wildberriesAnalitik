"""Tests that SQL aggregation reproduces the formula results."""
from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.accounts.models import Profile
from apps.reports.models import Cost
from apps.reports.services import ingest_detail

from . import services

User = get_user_model()


class KpiAggregationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('seller', password='pw')
        self.profile = Profile.objects.create(user=self.user, name='ИП', tax_type=1, tax_rate=2)
        Cost.objects.create(profile=self.profile, code='12345', cost=235)

    def _ingest(self, sales):
        ingest_detail(self.profile, {
            'sales': sales,
            'info': {'filename': 'r_692179585.xlsx', 'reportNum': '692179585',
                     'dateFrom': '2025-03-07', 'dateTo': '2025-03-07'},
        })

    def test_kpi_matches_formula_for_single_sale(self):
        self._ingest([{
            'srid': 'SR1', 'operation_type': 'Продажа', 'operation_reason': 'Продажа',
            'qty': 1, 'price_with_discount': 772.21, 'revenue_wb': 668.61,
            'to_pay': 531.71, 'wb_article': '12345', 'sale_date': '2025-03-07',
        }])
        kpi = services.compute_kpi(self.profile)
        self.assertEqual(kpi['row_count'], 1)
        self.assertAlmostEqual(kpi['revenue'], 772.21, places=2)
        self.assertAlmostEqual(kpi['wb_realized'], 668.61, places=2)
        self.assertAlmostEqual(kpi['cost'], 235, places=2)
        self.assertAlmostEqual(kpi['tax'], 13.37, places=2)
        self.assertEqual(kpi['sales_qty'], 1)

    def test_kpi_sums_two_rows(self):
        sale = {
            'operation_type': 'Продажа', 'operation_reason': 'Продажа', 'qty': 1,
            'price_with_discount': 100, 'revenue_wb': 90, 'to_pay': 80,
            'wb_article': '12345', 'sale_date': '2025-03-07',
        }
        self._ingest([{**sale, 'srid': 'A'}, {**sale, 'srid': 'B'}])
        kpi = services.compute_kpi(self.profile)
        self.assertEqual(kpi['row_count'], 2)
        self.assertAlmostEqual(kpi['revenue'], 200, places=2)
        self.assertAlmostEqual(kpi['wb_realized'], 180, places=2)

    def test_report_filter(self):
        self._ingest([{'srid': 'A', 'operation_type': 'Продажа', 'operation_reason': 'Продажа',
                       'qty': 1, 'price_with_discount': 100, 'sale_date': '2025-03-07', 'wb_article': '12345'}])
        kpi_all = services.compute_kpi(self.profile)
        kpi_other = services.compute_kpi(self.profile, report_num='000000000')
        self.assertEqual(kpi_all['row_count'], 1)
        self.assertEqual(kpi_other['row_count'], 0)

    def test_byproduct(self):
        self._ingest([{'srid': 'A', 'operation_type': 'Продажа', 'operation_reason': 'Продажа',
                       'qty': 1, 'price_with_discount': 772.21, 'revenue_wb': 668.61, 'to_pay': 531.71,
                       'wb_article': '12345', 'article': 'ART-1', 'sale_date': '2025-03-07'}])
        products = services.by_product(self.profile)
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]['article'], 'ART-1')
        self.assertAlmostEqual(products[0]['revenue'], 772.21, places=2)

class ChartsAndStorageServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('s2', password='pw')
        self.profile = Profile.objects.create(user=self.user, name='ИП', tax_type=1, tax_rate=2)
        Cost.objects.create(profile=self.profile, code='12345', cost=235)

    def _ingest(self, sales):
        ingest_detail(self.profile, {'sales': sales, 'info': {
            'filename': 'r.xlsx', 'reportNum': '692179585',
            'dateFrom': '2025-03-07', 'dateTo': '2025-03-07'}})

    def test_by_warehouse_and_day(self):
        self._ingest([
            {'srid': 'A', 'operation_type': 'Продажа', 'operation_reason': 'Продажа', 'qty': 2,
             'price_with_discount': 1000, 'revenue_wb': 900, 'to_pay': 800,
             'wb_article': '12345', 'warehouse': 'Коледино', 'sale_date': '2025-03-07'},
            {'srid': 'B', 'operation_type': 'Возврат', 'operation_reason': 'Возврат', 'qty': 1,
             'price_with_discount': 500, 'revenue_wb': 0, 'to_pay': 0,
             'wb_article': '12345', 'warehouse': 'Коледино', 'sale_date': '2025-03-07'},
        ])
        wh = services.by_warehouse(self.profile)
        self.assertEqual(len(wh), 1)
        self.assertEqual(wh[0]['warehouse'], 'Коледино')
        self.assertAlmostEqual(wh[0]['share_pct'], 100, places=1)
        days = services.by_day(self.profile)
        self.assertEqual(len(days), 1)
        self.assertEqual(days[0]['date'], '2025-03-07')

    def test_storage_breakdown(self):
        # A storage charge row (AD>0): WB Хранение operation.
        self._ingest([{'srid': 'S1', 'operation_type': '', 'operation_reason': 'Хранение',
                       'penalty_type': 'Хранение', 'storage_fee': 12.5, 'logistics': 0,
                       'warehouse': 'Коледино', 'sale_date': '2025-03-07',
                       'report_num': '692179585'}])
        data = services.storage_breakdown(self.profile)
        self.assertAlmostEqual(data['total'], 12.5, places=2)
        self.assertEqual(data['row_count'], 1)


class ChartsViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('s3', password='pw')
        self.profile = Profile.objects.create(user=self.user, name='ИП', tax_type=1, tax_rate=2)
        self.client.force_login(self.user)

    def test_charts_empty_state(self):
        from django.urls import reverse
        resp = self.client.get(reverse('analytics:charts'))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context['has_data'])

    def test_storage_page_loads(self):
        from django.urls import reverse
        resp = self.client.get(reverse('reports:storage'))
        self.assertEqual(resp.status_code, 200)


class SmartViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('s4', password='pw')
        self.profile = Profile.objects.create(user=self.user, name='ИП', tax_type=1, tax_rate=2)
        Cost.objects.create(profile=self.profile, code='12345', cost=235)
        self.client.force_login(self.user)

    def _ingest(self, sales):
        ingest_detail(self.profile, {'sales': sales, 'info': {
            'filename': 'r.xlsx', 'reportNum': '692179585',
            'dateFrom': '2025-03-07', 'dateTo': '2025-03-07'}})

    def test_smart_empty(self):
        from django.urls import reverse
        resp = self.client.get(reverse('analytics:smart'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['calc_json'], [])

    def test_smart_with_data(self):
        from django.urls import reverse
        self._ingest([{'srid': 'A', 'operation_type': 'Продажа', 'operation_reason': 'Продажа',
                       'qty': 1, 'price_with_discount': 772.21, 'revenue_wb': 668.61, 'to_pay': 531.71,
                       'wb_article': '12345', 'article': 'ART-1', 'size': 'M',
                       'warehouse': 'Коледино', 'sale_date': '2025-03-07'}])
        resp = self.client.get(reverse('analytics:smart'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context['calc_json']), 1)
        row = resp.context['calc_json'][0]
        self.assertEqual(row['AT'], 'ART-1')
        self.assertEqual(row['AV'], 'M')
        self.assertEqual(row['warehouse_name'], 'Коледино')
        self.assertAlmostEqual(row['I'], 772.21, places=2)
        self.assertEqual(len(resp.context['products_json']), 1)


class CalculatorViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('s5', password='pw')
        self.profile = Profile.objects.create(user=self.user, name='ИП', tax_type=1, tax_rate=2)
        self.client.force_login(self.user)

    def test_calculator_loads_with_kpi(self):
        from django.urls import reverse
        resp = self.client.get(reverse('analytics:calculator'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('kpi_json', resp.context)
        self.assertEqual(resp.context['calc_ctx_json']['tax_rate'], 2.0)
        self.assertEqual(resp.context['calc_ctx_json']['base_count'], 0)
