from django.contrib import admin
from django.urls import include, path

from apps.core import views as core_views

urlpatterns = [
    # Public marketing landing page at the domain root (indexed by search engines).
    path('', core_views.landing, name='landing'),
    path('robots.txt', core_views.robots_txt, name='robots_txt'),
    path('sitemap.xml', core_views.sitemap_xml, name='sitemap_xml'),

    path('admin/', admin.site.urls),
    # set_language view — lets the UZ/RU switch persist the chosen language.
    path('i18n/', include('django.conf.urls.i18n')),
    path('', include('apps.accounts.urls')),
    path('', include('apps.analytics.urls')),
    path('', include('apps.reports.urls')),
]