"""Tests that the Python formula port reproduces the verified Excel/JS results."""
from django.test import SimpleTestCase

from apps.core.formulas import calculate_row, num


class ReadmeReferenceRowTest(SimpleTestCase):
    """Reproduces the reference row from README.md ('Test natija' table)."""

    def setUp(self):
        self.row = {
            'operation_type': 'Продажа',      # BJ -> A = 1
            'operation_reason': 'Продажа',    # BK -> C = 1
            'qty': 1,                          # BN
            'price_with_discount': 772.21,     # BT -> F
            'revenue_wb': 668.61,              # BP -> Z
            'to_pay': 531.71,                  # CH -> J
            'wb_article': '12345',             # BD -> cost lookup key
        }
        self.ctx = {
            'reportNum': '',
            'settings': {'tax_type': 1, 'tax_rate': 2},
            'costs': [{'code': '12345', 'cost': 235}],
            'samovikupy': [],
            'extExpenses': [],
            'listReports': [],
        }

    def test_readme_values(self):
        c = calculate_row(self.row, self.ctx)
        self.assertEqual(c['A'], 1)                       # koef GENERAL
        self.assertEqual(c['C'], 1)                       # koef SALES
        self.assertAlmostEqual(c['F'], 772.21, places=2)  # Продано руб.
        self.assertAlmostEqual(c['I'], 772.21, places=2)  # Выручка
        self.assertAlmostEqual(c['J'], 531.71, places=2)  # К перечислению
        self.assertAlmostEqual(c['Z'], 668.61, places=2)  # WB реализовал
        self.assertAlmostEqual(c['AC'], 235, places=2)    # Себестоимость
        self.assertAlmostEqual(c['AB'], 13.37, places=2)  # Налог (668.61 * 2%)


class TaxTypeTest(SimpleTestCase):
    base_row = {
        'operation_type': 'Продажа', 'operation_reason': 'Продажа',
        'qty': 1, 'price_with_discount': 772.21, 'revenue_wb': 668.61,
        'to_pay': 531.71, 'wb_article': '12345',
    }
    costs = [{'code': '12345', 'cost': 235}]

    def _calc(self, tax_type, tax_rate=2):
        ctx = {'settings': {'tax_type': tax_type, 'tax_rate': tax_rate},
               'costs': self.costs, 'samovikupy': [], 'listReports': []}
        return calculate_row(self.base_row, ctx)

    def test_usn_dohody_base_is_wb_realized(self):
        c = self._calc(1)
        self.assertAlmostEqual(c['AA'], c['Z'], places=4)   # AA = Z

    def test_usn_dr_base(self):
        c = self._calc(2)
        self.assertAlmostEqual(c['AA'], c['Y'] - c['AC'] - c['AN'], places=4)

    def test_ne_schitat_zero(self):
        c = self._calc(3)
        self.assertEqual(c['AA'], 0)
        self.assertEqual(c['AB'], 0)

    def test_schitat_ot_rs(self):
        c = self._calc(4)
        self.assertAlmostEqual(c['AA'], c['Y'], places=4)   # AA = Y


class ReturnRowTest(SimpleTestCase):
    def test_return_row(self):
        row = {
            'operation_type': 'Возврат', 'operation_reason': 'Возврат',
            'qty': 1, 'price_with_discount': 772.21, 'revenue_wb': 668.61,
            'to_pay': 531.71, 'wb_article': '12345',
        }
        ctx = {'settings': {'tax_type': 1, 'tax_rate': 2},
               'costs': [{'code': '12345', 'cost': 235}], 'samovikupy': [], 'listReports': []}
        c = calculate_row(row, ctx)
        self.assertEqual(c['A'], -1)               # Возврат
        self.assertEqual(c['C'], -1)
        self.assertEqual(c['D'], 0)
        self.assertEqual(c['E'], 1)                # returned qty
        self.assertEqual(c['F'], 0)
        self.assertAlmostEqual(c['G'], 772.21, places=2)
        self.assertAlmostEqual(c['I'], -772.21, places=2)   # negative revenue
        self.assertAlmostEqual(c['Z'], -668.61, places=2)   # A * abs(BP)
        # AC: cost*(Q+R) + cost*C = 235*0 + 235*(-1) = -235
        self.assertAlmostEqual(c['AC'], -235, places=2)


class AcquiringLogicTest(SimpleTestCase):
    """The L (Эквайринг) branch logic must match baza-formulas.js exactly."""

    def _calc(self, **over):
        row = {'operation_type': 'Продажа', 'operation_reason': 'Продажа', 'qty': 1,
               'price_with_discount': 100, 'to_pay': 50}
        row.update(over)
        ctx = {'settings': {'tax_type': 1, 'tax_rate': 2}, 'costs': [], 'samovikupy': [], 'listReports': []}
        return calculate_row(row, ctx)

    def test_cd_positive_and_a_nonzero(self):
        c = self._calc(acquiring=5, acquiring_percent=1.5)   # CD>0, A=1 -> L = CC*A + M
        self.assertAlmostEqual(c['L'], 5, places=4)

    def test_cc_only(self):
        c = self._calc(acquiring=5, acquiring_percent=0)     # CD=0, CC!=0 -> L = CC + M
        self.assertAlmostEqual(c['L'], 5, places=4)

    def test_no_acquiring(self):
        c = self._calc()                                     # CC=0 -> L = M = 0
        self.assertEqual(c['L'], 0)


class SamovikupTest(SimpleTestCase):
    def test_samovikup_skips_cost(self):
        row = {'operation_type': 'Продажа', 'operation_reason': 'Продажа', 'qty': 1,
               'price_with_discount': 772.21, 'to_pay': 531.71, 'wb_article': '12345',
               'srid': 'SR1'}
        ctx = {'settings': {'tax_type': 1, 'tax_rate': 2},
               'costs': [{'code': '12345', 'cost': 235}],
               'samovikupy': [{'srid': 'SR1', 'total': 400}], 'listReports': []}
        c = calculate_row(row, ctx)
        self.assertEqual(c['AM'], 'Самовыкуп')
        self.assertEqual(c['AO'], 'Не нужна СС')   # samovikup -> no cost needed
        self.assertEqual(c['AC'], 0)
        self.assertEqual(c['AL'], 400)


class NumHelperTest(SimpleTestCase):
    def test_num(self):
        self.assertEqual(num(''), 0)
        self.assertEqual(num(None), 0)
        self.assertEqual(num('1 234,56'), 1234.56)   # spaces + comma decimal
        self.assertEqual(num('(100)'), 0)            # JS num() does NOT handle parens
        self.assertEqual(num(42), 42)
        self.assertEqual(num('abc'), 0)