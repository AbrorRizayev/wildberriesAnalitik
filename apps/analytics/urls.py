from django.urls import path

from apps.reports import views as reports_views

from . import views

app_name = 'analytics'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('charts/', views.charts, name='charts'),
    path('fines/', views.fines, name='fines'),
    path('pnl/', views.pnl, name='pnl'),
    path('monthly/', views.monthly, name='monthly'),
    path('monthly/export/', views.monthly_export, name='monthly_export'),
    path('abc/', views.abc, name='abc'),
    path('products/', views.products, name='products'),
    path('capitalization/', reports_views.capitalization_page, name='capitalization'),
    path('smart/', views.smart, name='smart'),
    path('calculator/', views.calculator, name='calculator'),
]