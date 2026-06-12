from django.urls import path

from . import views

app_name = 'reports'

urlpatterns = [
    path('upload/', views.upload_page, name='upload'),
    path('upload/detail/', views.upload_detail, name='upload_detail'),
    path('upload/list/', views.upload_list, name='upload_list'),
    path('upload/clear/', views.clear_all, name='clear_all'),
    path('upload/backup/', views.backup, name='backup'),

    path('list-reports/', views.list_reports_page, name='list_reports'),
    path('list-reports/export/', views.report_export, name='report_export'),
    path('list-reports/delete/', views.delete_report, name='delete_report'),
    path('list-reports/clear/', views.clear_list, name='clear_list'),
    path('base/', views.base_page, name='base'),
    path('base/clear/', views.clear_base, name='clear_base'),
    path('base/clear-report/', views.clear_report, name='clear_report'),
    path('costs/', views.costs_page, name='costs'),
    path('costs/add/', views.cost_add, name='cost_add'),
    path('costs/update/', views.cost_update, name='cost_update'),
    path('costs/delete/', views.cost_delete, name='cost_delete'),
    path('costs/clear/', views.costs_clear, name='costs_clear'),
    path('costs/import/', views.costs_import, name='costs_import'),
    path('recompute/', views.recompute, name='recompute'),
    path('storage/', views.storage_page, name='storage'),

    path('capitalization/upload/', views.cap_upload, name='cap_upload'),
    path('capitalization/clear/', views.cap_clear, name='cap_clear'),
    path('capitalization/params/', views.cap_params_save, name='cap_params_save'),
    path('capitalization/cost/', views.cap_cost_set, name='cap_cost_set'),
    path('capitalization/costs-import/', views.cap_costs_import, name='cap_costs_import'),
    path('self-purchase/', views.self_purchase_page, name='self_purchase'),
    path('self-purchase/save/', views.self_purchase_save, name='self_purchase_save'),
    path('self-purchase/delete/', views.self_purchase_delete, name='self_purchase_delete'),
    path('ext-expenses/', views.ext_expenses_page, name='ext_expenses'),
    path('ext-expenses/save/', views.ext_expense_save, name='ext_expense_save'),
    path('ext-expenses/delete/', views.ext_expense_delete, name='ext_expense_delete'),
]