"""Tests for the parser port (column detection, value cleaning, file reading)."""
import io

from django.test import SimpleTestCase

from apps.core import parser
from apps.core.formulas import calculate_row

# A realistic-ish subset of WB Подробный отчёт headers.
WB_HEADERS = [
    'Srid', 'Номер поставки', 'Баркод', 'Бренд', 'Артикул поставщика',
    'Код номенклатуры', 'Название', 'Размер', 'Тип документа',
    'Обоснование для оплаты', 'Дата продажи', 'Кол-во',
    'Цена розничная с учетом согласованной скидки',
    'Вайлдберриз реализовал товар (Пр)',
    'Продавцу за реализованный товар', 'Услуги по доставке товара покупателю',
    'Общая сумма штрафов', 'Виды логистики, штрафов и корректировок ВВ',
    'Склад', 'Хранение',
]


class DetectColumnsTest(SimpleTestCase):
    def test_maps_core_columns(self):
        m = parser.detect_columns(WB_HEADERS)
        self.assertIn('Srid', m['srid'])
        self.assertIn('Код номенклатуры', m['wb_article'])
        self.assertIn('Артикул поставщика', m['article'])
        self.assertIn('Тип документа', m['operation_type'])
        self.assertIn('Дата продажи', m['sale_date'])
        self.assertIn('Цена розничная с учетом согласованной скидки', m['price_with_discount'])
        self.assertIn('Вайлдберриз реализовал товар (Пр)', m['revenue_wb'])
        self.assertIn('Продавцу за реализованный товар', m['to_pay'])
        self.assertIn('Услуги по доставке товара покупателю', m['logistics'])
        self.assertIn('Общая сумма штрафов', m['fine'])
        self.assertIn('Виды логистики, штрафов и корректировок ВВ', m['penalty_type'])
        self.assertIn('Склад', m['warehouse'])
        self.assertIn('Хранение', m['storage_fee'])

    def test_exact_match_size_not_greedy(self):
        # '__exact:размер' must NOT match 'Размер скидки' etc.
        m = parser.detect_columns(['Размер скидки', 'Размер'])
        self.assertEqual(m['size'], ['Размер'])


class CleanValueTest(SimpleTestCase):
    def test_numeric_space_and_comma(self):
        self.assertEqual(parser.clean_value('1 234,56', 'to_pay'), 1234.56)

    def test_numeric_parentheses_negative(self):
        # parser cleanValue DOES convert (x) -> -x (unlike formulas.num()).
        self.assertEqual(parser.clean_value('(100)', 'fine'), -100.0)

    def test_text_passthrough(self):
        self.assertEqual(parser.clean_value('  Продажа  ', 'operation_type'), 'Продажа')


class ParseDateTest(SimpleTestCase):
    def test_iso(self):
        self.assertEqual(parser.parse_date('2025-3-7'), '2025-03-07')

    def test_dmy(self):
        self.assertEqual(parser.parse_date('07.03.25'), '2025-03-07')

    def test_passthrough(self):
        self.assertEqual(parser.parse_date('неизвестно'), 'неизвестно')


class CsvPipelineTest(SimpleTestCase):
    def test_csv_to_calculation(self):
        csv = (
            'Srid;Тип документа;Обоснование для оплаты;Кол-во;'
            'Цена розничная с учетом согласованной скидки;'
            'Вайлдберриз реализовал товар;Продавцу за реализованный товар;Код номенклатуры\n'
            'SR1;Продажа;Продажа;1;772,21;668,61;531,71;12345\n'
        )
        res = parser.parse_csv_text(csv, 'report_692179585.csv')
        self.assertEqual(len(res['sales']), 1)
        sale = res['sales'][0]
        self.assertEqual(sale['operation_type'], 'Продажа')
        self.assertEqual(sale['price_with_discount'], 772.21)

        ctx = {'settings': {'tax_type': 1, 'tax_rate': 2},
               'costs': [{'code': '12345', 'cost': 235}], 'samovikupy': [], 'listReports': []}
        c = calculate_row(sale, ctx)
        self.assertAlmostEqual(c['I'], 772.21, places=2)
        self.assertAlmostEqual(c['J'], 531.71, places=2)
        self.assertAlmostEqual(c['Z'], 668.61, places=2)
        self.assertAlmostEqual(c['AC'], 235, places=2)


class ExcelReadTest(SimpleTestCase):
    """Round-trip: write an xlsx with openpyxl, read it back with the calamine port."""

    def _make_xlsx(self):
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(['Какой-то заголовок отчёта'])  # junk row before header
        ws.append(WB_HEADERS)
        ws.append(['SR1', 'P1', '200000', 'Piccino', 'ART-1', '12345', 'Товар', 'M',
                   'Продажа', 'Продажа', '2025-03-07', 1, 772.21, 668.61, 531.71,
                   0, 0, '', 'Коледино', 0])
        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    def test_excel_detail_parse(self):
        data = self._make_xlsx()
        res = parser.parse_excel(data, 'Еженедельный_отчет_692179585.xlsx')
        self.assertEqual(len(res['sales']), 1)
        self.assertEqual(res['info']['reportNum'], '692179585')  # from filename
        sale = res['sales'][0]
        self.assertEqual(sale['operation_type'], 'Продажа')
        self.assertEqual(sale['wb_article'], '12345')
        self.assertEqual(sale['sale_date'], '2025-03-07')
        self.assertEqual(sale['price_with_discount'], 772.21)


class ListReportParseTest(SimpleTestCase):
    def test_list_row(self):
        row = {
            '№ отчёта': '692179585 ',
            'Юридическое лицо': 'ИП Тест',
            'Дата начала': '2025-03-03',
            'Дата конца': '2025-03-09',
            'Продажа': '1 000 000,50',
            'Стоимость логистики': '12 345,67',
            'Общая сумма штрафов': '100',
        }
        r = parser.normalize_list_row(row)
        self.assertEqual(r['report_num'], '692179585')
        self.assertEqual(r['legal_entity'], 'ИП Тест')
        self.assertEqual(r['date_from'], '2025-03-03')
        self.assertEqual(r['sale_total'], 1000000.5)
        self.assertEqual(r['logistics_cost'], 12345.67)
        self.assertEqual(r['fines_total'], 100)