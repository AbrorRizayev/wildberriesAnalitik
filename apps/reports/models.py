"""Data models for the WB analytics pipeline.

Design (see [[aira-migration-architecture]]):
- BaseRow keeps the full normalized WB row in a JSONB `raw` field and stores the
  computed formula outputs + grouping keys as real columns so that KPI / P&L / ABC
  reports run as Postgres SUM/GROUP BY instead of Python loops.
- Recompute (when settings/costs change) reads `raw`, runs the formula engine, and
  bulk-updates the computed columns.
"""
from django.conf import settings
from django.db import models


class ProfileOwned(models.Model):
    """Base class: every data row belongs to a profile (tenant isolation)."""
    profile = models.ForeignKey('accounts.Profile', on_delete=models.CASCADE, related_name='%(class)ss')

    class Meta:
        abstract = True


# ============================================================
# Список отчётов
# ============================================================
class ListReport(ProfileOwned):
    report_num = models.CharField(max_length=32, db_index=True)
    legal_entity = models.CharField(max_length=255, blank=True)
    date_from = models.DateField(null=True, blank=True)
    date_to = models.DateField(null=True, blank=True)
    created_at = models.DateField(null=True, blank=True)
    report_type = models.CharField(max_length=128, blank=True)

    sale_total = models.FloatField(default=0)
    to_pay = models.FloatField(default=0)
    discount_percent = models.FloatField(default=0)
    logistics_cost = models.FloatField(default=0)
    storage_cost = models.FloatField(default=0)
    paid_reception = models.FloatField(default=0)
    other_deductions = models.FloatField(default=0)
    fines_total = models.FloatField(default=0)
    wb_correction = models.FloatField(default=0)
    loyalty_compensation = models.FloatField(default=0)
    loyalty_participation = models.FloatField(default=0)
    loyalty_points = models.FloatField(default=0)
    total_to_pay = models.FloatField(default=0)

    class Meta:
        verbose_name = 'Отчёт (список)'
        verbose_name_plural = 'Список отчётов'
        constraints = [
            models.UniqueConstraint(fields=['profile', 'report_num'], name='uniq_listreport_per_profile'),
        ]
        ordering = ['date_from']

    def __str__(self):
        return f'{self.report_num} ({self.profile_id})'


# ============================================================
# Себестоимость
# ============================================================
class Cost(ProfileOwned):
    barcode = models.CharField(max_length=64, blank=True, db_index=True)
    code = models.CharField(max_length=64, blank=True, db_index=True)   # Код номенклатуры
    supply_num = models.CharField(max_length=64, blank=True)            # Номер поставки
    kluch = models.CharField(max_length=128, blank=True)               # supply_num + code key
    brand = models.CharField(max_length=255, blank=True)               # Бренд (display only)
    article = models.CharField(max_length=128, blank=True)             # Артикул поставщика (display)
    name = models.CharField(max_length=255, blank=True)
    group = models.CharField(max_length=128, blank=True)
    cost = models.FloatField(default=0)
    cost_future = models.FloatField(default=0)

    class Meta:
        verbose_name = 'Себестоимость'
        verbose_name_plural = 'Себестоимость'

    def __str__(self):
        return f'{self.name or self.code} = {self.cost}'


# ============================================================
# База — main rows
# ============================================================
class BaseRow(ProfileOwned):
    report_num = models.CharField(max_length=32, db_index=True)
    srid = models.CharField(max_length=128, blank=True, db_index=True)

    # Full normalized WB row (parser output). Source of truth for recompute.
    raw = models.JSONField(default=dict)

    # ---- Grouping / display keys ----
    sale_date = models.DateField(null=True, blank=True, db_index=True)  # BM
    week = models.DateField(null=True, blank=True, db_index=True)       # AP
    month = models.CharField(max_length=16, blank=True)                 # AQ
    year = models.IntegerField(null=True, blank=True)                   # AR
    article = models.CharField(max_length=128, blank=True, db_index=True)  # AT
    brand = models.CharField(max_length=255, blank=True)               # AS
    product_name = models.CharField(max_length=512, blank=True)        # AU
    size = models.CharField(max_length=64, blank=True)                 # AV
    group = models.CharField(max_length=128, blank=True, db_index=True)   # AX
    warehouse = models.CharField(max_length=128, blank=True, db_index=True)
    penalty_type = models.CharField(max_length=255, blank=True, db_index=True)  # CQ
    legal_entity = models.CharField(max_length=255, blank=True)        # AY

    # ---- Raw amounts still needed for SQL aggregation ----
    raw_logistics = models.FloatField(default=0)   # CK
    fine = models.FloatField(default=0)            # CO
    wb_correction = models.FloatField(default=0)   # CP

    # ---- Computed formula outputs (letter in comment = Excel column) ----
    sold_qty = models.FloatField(default=0)        # D  Продано шт.
    returned_qty = models.FloatField(default=0)    # E  Возвращено шт.
    sold_rub = models.FloatField(default=0)        # F  Продано руб.
    returned_rub = models.FloatField(default=0)    # G  Возвращено руб.
    net_qty = models.FloatField(default=0)         # H  Продаж шт.
    revenue = models.FloatField(default=0)         # I  Выручка
    to_transfer = models.FloatField(default=0)     # J  К перечислению
    commission = models.FloatField(default=0)      # K  Комиссия
    acquiring = models.FloatField(default=0)       # L  Эквайринг
    spp = models.FloatField(default=0)             # N  СПП
    comp_brak = models.FloatField(default=0)       # O  Компенсация брака
    comp_uscherb = models.FloatField(default=0)    # P  Компенсация ущерба
    logistics_direct = models.FloatField(default=0)  # S  Прямая логистика
    logistics_back = models.FloatField(default=0)    # T  Обратная логистика
    paid_acceptance = models.FloatField(default=0)   # V  Платная приёмка
    pl_deduction = models.FloatField(default=0)      # W  Удержания за ПЛ
    cashback = models.FloatField(default=0)          # X  CashBack
    to_pay_rs = models.FloatField(default=0)         # Y  Оплата на РС
    wb_realized = models.FloatField(default=0)       # Z  WB реализовал
    tax_base = models.FloatField(default=0)          # AA Налоговая база
    tax = models.FloatField(default=0)               # AB Налог
    cost = models.FloatField(default=0)              # AC Себестоимость
    storage = models.FloatField(default=0)           # AD Хранение
    promotion = models.FloatField(default=0)         # AE ВБ.Продвижение
    transit = models.FloatField(default=0)           # AF Транзит
    supply_change = models.FloatField(default=0)     # AG Изменение условий поставки
    jem = models.FloatField(default=0)               # AH Подписка "Джем"
    utilization = models.FloatField(default=0)       # AI Утилизация
    review_cancel = models.FloatField(default=0)     # AJ Списание за отзыв
    other_deduction = models.FloatField(default=0)   # AK Другие удержания
    samovikup_cost = models.FloatField(default=0)    # AL Затраты самовыкупов
    ext_expenses = models.FloatField(default=0)      # AN Внешние расходы

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Строка базы'
        verbose_name_plural = 'База'
        indexes = [
            models.Index(fields=['profile', 'report_num']),
            models.Index(fields=['profile', 'article']),
            models.Index(fields=['profile', 'warehouse']),
            models.Index(fields=['profile', 'penalty_type']),
            models.Index(fields=['profile', 'week']),
        ]

    def __str__(self):
        return f'{self.report_num}/{self.srid}'


# ============================================================
# Самовыкупы
# ============================================================
class SelfPurchase(ProfileOwned):
    srid = models.CharField(max_length=128, blank=True, db_index=True)
    article = models.CharField(max_length=128, blank=True)
    date = models.DateField(null=True, blank=True)
    cost = models.FloatField(default=0)        # tannarx
    logistics = models.FloatField(default=0)   # logistika
    total = models.FloatField(default=0)       # cost + logistics (feeds formula AL)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = 'Самовыкуп'
        verbose_name_plural = 'Самовыкупы'

    def __str__(self):
        return f'{self.srid} = {self.total}'


# ============================================================
# Внешние расходы
# ============================================================
class ExtExpense(ProfileOwned):
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=128, blank=True)
    month = models.CharField(max_length=16, blank=True)
    date = models.DateField(null=True, blank=True)
    amount = models.FloatField(default=0)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = 'Внешний расход'
        verbose_name_plural = 'Внешние расходы'

    def __str__(self):
        return f'{self.name} = {self.amount}'


# ============================================================
# Хранение
# ============================================================
class StorageRow(ProfileOwned):
    raw = models.JSONField(default=dict)
    barcode = models.CharField(max_length=64, blank=True, db_index=True)
    article = models.CharField(max_length=128, blank=True)
    date = models.DateField(null=True, blank=True)
    amount = models.FloatField(default=0)

    class Meta:
        verbose_name = 'Хранение (строка)'
        verbose_name_plural = 'Хранение'

    def __str__(self):
        return f'{self.barcode} = {self.amount}'


# ============================================================
# Капитализация
# ============================================================
class CapStock(ProfileOwned):
    raw = models.JSONField(default=dict)
    barcode = models.CharField(max_length=64, blank=True, db_index=True)
    article = models.CharField(max_length=128, blank=True)
    warehouse = models.CharField(max_length=128, blank=True)
    qty = models.FloatField(default=0)

    class Meta:
        verbose_name_plural = 'Капитализация — остатки'


class CapSales(ProfileOwned):
    raw = models.JSONField(default=dict)
    barcode = models.CharField(max_length=64, blank=True, db_index=True)
    article = models.CharField(max_length=128, blank=True)
    qty = models.FloatField(default=0)

    class Meta:
        verbose_name_plural = 'Капитализация — продажи'


class CapNomenclature(ProfileOwned):
    raw = models.JSONField(default=dict)
    barcode = models.CharField(max_length=64, blank=True, db_index=True)
    article = models.CharField(max_length=128, blank=True)
    name = models.CharField(max_length=512, blank=True)

    class Meta:
        verbose_name_plural = 'Капитализация — номенклатура'


class CapParams(ProfileOwned):
    profile = models.OneToOneField('accounts.Profile', on_delete=models.CASCADE, related_name='cap_params')
    days_of_sales = models.IntegerField(default=7)
    delivery_days = models.IntegerField(default=7)
    reserve_days = models.IntegerField(default=7)
    delivery_cost = models.FloatField(default=0)
    selected_warehouse = models.CharField(max_length=128, default='Все склады')
    stock_uploaded_at = models.DateTimeField(null=True, blank=True)
    sales_uploaded_at = models.DateTimeField(null=True, blank=True)
    nomenclature_uploaded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name_plural = 'Капитализация — параметры'


# ============================================================
# Yuklash tarixi
# ============================================================
class UploadHistory(ProfileOwned):
    TYPE_CHOICES = [('list', 'Список отчётов'), ('detail', 'Подробный отчёт')]
    type = models.CharField(max_length=16, choices=TYPE_CHOICES)
    filename = models.CharField(max_length=255, blank=True)
    report_num = models.CharField(max_length=32, blank=True)
    date_from = models.DateField(null=True, blank=True)
    date_to = models.DateField(null=True, blank=True)
    row_count = models.IntegerField(default=0)
    total_sum = models.FloatField(default=0)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Загрузка'
        verbose_name_plural = 'История загрузок'
        ordering = ['-uploaded_at']

    def __str__(self):
        return f'{self.type} {self.filename}'