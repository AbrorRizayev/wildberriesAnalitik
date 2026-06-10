from django.contrib.auth.models import AbstractUser
from django.db import models



class User(AbstractUser):
    """Paying customer. Accounts are created by the admin (no public signup).

    Extends Django's AbstractUser so we can add subscription/billing fields later
    without a painful migration.
    """

    # Billing / access control (room to grow; not enforced yet in MVP)
    is_active_subscription = models.BooleanField(
        default=True,
        help_text="Obuna faol. False bo'lsa, login bo'lsa ham ma'lumotlarga kira olmaydi.",
    )
    subscription_until = models.DateField(null=True, blank=True)
    note = models.CharField(max_length=255, blank=True, help_text='Admin uchun izoh')

    class Meta:
        verbose_name = 'Foydalanuvchi'
        verbose_name_plural = 'Foydalanuvchilar'

    def __str__(self):
        return self.get_full_name() or self.username


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