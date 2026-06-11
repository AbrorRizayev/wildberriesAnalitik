import calendar
from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


def add_months(d, months):
    """Return ``d`` shifted forward by ``months`` whole calendar months.

    Day is clamped to the last valid day of the target month (e.g. Jan 31 + 1m
    → Feb 28/29) so we never build an invalid date.
    """
    index = d.month - 1 + months
    year = d.year + index // 12
    month = index % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return d.replace(year=year, month=month, day=day)


class User(AbstractUser):
    """Paying customer. Accounts are created by the admin (no public signup).

    Extends Django's AbstractUser so we can add subscription/billing fields later
    without a painful migration.
    """

    # Preset subscription durations the admin can grant. The value encodes the
    # length; ``period_end`` turns it into an expiry moment relative to a start.
    SUBSCRIPTION_PLANS = [
        ('3d', '3 kunlik'),
        ('1m', '1 oylik'),
        ('3m', '3 oylik'),
        ('6m', '6 oylik'),
        ('1y', '1 yillik'),
    ]

    # Billing / access control. Enforced by SubscriptionMiddleware: a user whose
    # subscription is off or past its end date is logged in but blocked from the app.
    is_active_subscription = models.BooleanField(
        default=True,
        help_text="Obuna faol. False bo'lsa, login bo'lsa ham ma'lumotlarga kira olmaydi.",
    )
    subscription_plan = models.CharField(
        max_length=8,
        choices=SUBSCRIPTION_PLANS,
        blank=True,
        help_text="Tanlangan obuna muddati. O'zgartirilganda tugash vaqti shu paytdan qayta hisoblanadi.",
    )
    subscription_until = models.DateTimeField(null=True, blank=True)
    note = models.CharField(max_length=255, blank=True, help_text='Admin uchun izoh')

    @staticmethod
    def period_end(plan, start=None):
        """Expiry moment for ``plan`` counting from ``start`` (default: now)."""
        start = start or timezone.now()
        if plan == '3d':
            return start + timedelta(days=3)
        months = {'1m': 1, '3m': 3, '6m': 6, '1y': 12}.get(plan)
        if months is None:
            return None
        return add_months(start, months)

    class Meta:
        verbose_name = 'Foydalanuvchi'
        verbose_name_plural = 'Foydalanuvchilar'

    def __str__(self):
        return self.get_full_name() or self.username

    @property
    def subscription_active(self):
        """True when the user is allowed into the app.

        Off if the admin disabled the subscription, or if ``subscription_until``
        is set and already in the past. A null ``subscription_until`` means no
        expiry date (unlimited while ``is_active_subscription`` stays True).
        """
        if not self.is_active_subscription:
            return False
        if self.subscription_until is not None:
            return self.subscription_until >= timezone.now()
        return True


class Profile(models.Model):
    """An IP/company under a user. Each profile owns its own data
    (base rows, costs, reports, ...). Mirrors the multi-profile concept
    from the original js/storage.js.
    """

    TAX_TYPES = [
        (1, 'УСН-доходы'),
        (2, 'УСН Д-Р'),
        (3, 'Не считать'),
        (4, 'Считать от РС'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='profiles')

    name = models.CharField(max_length=255)
    brand = models.CharField(max_length=255, blank=True)
    inn = models.CharField(max_length=32, blank=True)
    wb_id = models.CharField(max_length=64, blank=True)
    country = models.CharField(max_length=32, default='🇰🇬 KG')
    currency = models.CharField(max_length=8, default='₽')

    tax_type = models.PositiveSmallIntegerField(choices=TAX_TYPES, default=1)
    tax_rate = models.DecimalField(max_digits=6, decimal_places=2, default=2)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Profil'
        verbose_name_plural = 'Profillar'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.name} ({self.user})'

    @property
    def tax_type_name(self):
        return dict(self.TAX_TYPES).get(self.tax_type, '')