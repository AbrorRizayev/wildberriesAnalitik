from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import AdminUserCreationForm, UserChangeForm
from django.utils import timezone

from .models import Profile, User


class UserAdminForm(UserChangeForm):
    """Picking a subscription plan sets the end date from today.

    The admin chooses a duration (3 kunlik / 1 oylik / 3 oylik / 6 oylik /
    1 yillik) and on save ``subscription_until`` is computed as today + that
    duration and the subscription is switched on. The end date is recomputed
    only when the plan is actually changed, so editing other fields and
    re-saving never silently extends an existing subscription. ``subscription_until``
    stays editable for fine-grained manual control.
    """

    class Meta(UserChangeForm.Meta):
        model = User

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remember the plan stored before this edit to detect a real change.
        self._original_plan = self.instance.subscription_plan if self.instance.pk else ''

    def save(self, commit=True):
        user = super().save(commit=False)
        plan = self.cleaned_data.get('subscription_plan')
        if plan and plan != self._original_plan:
            user.subscription_until = User.period_end(plan, timezone.now())
            user.is_active_subscription = True
        if commit:
            user.save()
        return user


class UserCreateForm(AdminUserCreationForm):
    """Create form: pick the subscription plan alongside login/password.

    Extends Django's admin create form (``AdminUserCreationForm``, which carries
    the ``usable_password`` field the admin add page expects) — NOT the plain
    ``UserCreationForm``, otherwise the add page errors with
    "Unknown field(s) (usable_password)". On the very first save the chosen plan
    sets ``subscription_until`` from today, so the new account is born with a
    live, time-limited subscription.
    """

    subscription_plan = forms.ChoiceField(
        choices=[('', '— muddatsiz —')] + User.SUBSCRIPTION_PLANS,
        required=False,
        label='Obuna muddati',
        help_text='Tugash sanasi bugundan boshlab hisoblanadi.',
    )

    class Meta(AdminUserCreationForm.Meta):
        model = User

    def save(self, commit=True):
        user = super().save(commit=False)
        plan = self.cleaned_data.get('subscription_plan')
        if plan:
            user.subscription_plan = plan
            user.subscription_until = User.period_end(plan, timezone.now())
            user.is_active_subscription = True
        if commit:
            user.save()
        return user


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = UserAdminForm
    add_form = UserCreateForm
    list_display = ('username', 'get_full_name', 'subscription_plan', 'max_companies',
                    'is_active_subscription', 'subscription_until', 'subscription_active', 'is_staff')
    list_filter = ('is_active_subscription', 'subscription_plan', 'max_companies', 'is_staff', 'is_active')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Obuna / billing', {
            'fields': ('subscription_plan', 'subscription_until', 'is_active_subscription',
                       'max_companies', 'note'),
            'description': "Obuna muddatini tanlang — tugash sanasi bugundan boshlab hisoblanadi. "
                           "Muddat tugagach foydalanuvchi tizimga kira olmaydi. "
                           "Kompaniyalar limiti — foydalanuvchi maksimal nechta kompaniya ocha oladi.",
        }),
    )
    # Same plan + company-limit pickers are available right on the create form, so
    # the admin sets them together with the new login/password.
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Obuna / billing', {'fields': ('subscription_plan', 'max_companies')}),
    )

    @admin.display(boolean=True, description='Hozir faol?')
    def subscription_active(self, obj):
        return obj.subscription_active


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'brand', 'inn', 'tax_type', 'is_active', 'created_at')
    list_filter = ('tax_type', 'is_active', 'country')
    search_fields = ('name', 'brand', 'inn', 'wb_id', 'user__username')