from django.contrib import admin

from .models import (
    BaseRow, CapNomenclature, CapParams, CapSales, CapStock, Cost, ExtExpense,
    ListReport, SelfPurchase, StorageRow, UploadHistory,
)


@admin.register(ListReport)
class ListReportAdmin(admin.ModelAdmin):
    list_display = ('report_num', 'profile', 'date_from', 'date_to', 'sale_total', 'to_pay', 'fines_total')
    list_filter = ('profile',)
    search_fields = ('report_num', 'legal_entity')


@admin.register(Cost)
class CostAdmin(admin.ModelAdmin):
    list_display = ('name', 'profile', 'barcode', 'code', 'group', 'cost', 'cost_future')
    list_filter = ('profile', 'group')
    search_fields = ('name', 'barcode', 'code')


@admin.register(BaseRow)
class BaseRowAdmin(admin.ModelAdmin):
    list_display = ('report_num', 'profile', 'sale_date', 'article', 'revenue', 'to_pay_rs', 'cost', 'tax')
    list_filter = ('profile', 'report_num')
    search_fields = ('srid', 'article', 'product_name')
    show_full_result_count = False


@admin.register(UploadHistory)
class UploadHistoryAdmin(admin.ModelAdmin):
    list_display = ('type', 'profile', 'filename', 'report_num', 'row_count', 'uploaded_at')
    list_filter = ('profile', 'type')


admin.site.register([
    SelfPurchase, ExtExpense, StorageRow,
    CapStock, CapSales, CapNomenclature, CapParams,
])