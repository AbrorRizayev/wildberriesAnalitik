from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(
        template_name='accounts/login.html',
        redirect_authenticated_user=True,
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('profile/switch/<int:profile_id>/', views.switch_profile, name='switch_profile'),
    path('profile/create/', views.profile_create, name='profile_create'),
    path('settings/', views.settings_page, name='settings'),
    path('settings/save/', views.settings_save, name='settings_save'),
]