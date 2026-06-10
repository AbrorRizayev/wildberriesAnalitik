from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Profile, User


class ProfileInline(admin.TabularInline):
    model = Profile
    extra = 0
    fields = ('name', 'brand', 'inn', 'wb_id', 'country', 'currency', 'tax_type', 'tax_rate', 'is_active')


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = [ProfileInline]
    list_display = ('username', 'get_full_name', 'is_active_subscription', 'subscription_until', 'is_staff')
    list_filter = ('is_active_subscription', 'is_staff', 'is_active')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Obuna / billing', {'fields': ('is_active_subscription', 'subscription_until', 'note')}),
    )


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'brand', 'inn', 'tax_type', 'is_active', 'created_at')
    list_filter = ('tax_type', 'is_active', 'country')
    search_fields = ('name', 'brand', 'inn', 'wb_id', 'user__username')