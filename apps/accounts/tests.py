from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User, Profile
from apps.reports.models import BaseRow


class ProfileCreateTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('owner', password='x')
        self.other = User.objects.create_user('other', password='x')
        self.client.force_login(self.user)

    def test_create_company_and_switch(self):
        # Touch any page so get_active_profile makes the default profile.
        self.client.get(reverse('accounts:settings'))
        before = self.user.profiles.count()

        resp = self.client.post(reverse('accounts:profile_create'), {
            'name': 'ИП Иванов', 'brand': 'BrandX',
            'country': '🇺🇿 UZ', 'currency': 'сўм',
            'inn': '123456', 'tax_type': '2', 'tax_rate': '5',
        })
        self.assertRedirects(resp, reverse('accounts:settings'))

        self.assertEqual(self.user.profiles.count(), before + 1)
        p = self.user.profiles.get(name='ИП Иванов')
        self.assertEqual(p.brand, 'BrandX')
        self.assertEqual(p.tax_type, 2)
        self.assertEqual(float(p.tax_rate), 5.0)
        # New company is now the active one in the session.
        self.assertEqual(self.client.session['active_profile_id'], p.id)
        # And it owns no data — separate accounting.
        self.assertEqual(BaseRow.objects.filter(profile=p).count(), 0)

    def test_name_required(self):
        before = self.user.profiles.count()
        self.client.post(reverse('accounts:profile_create'), {'name': '   '})
        self.assertEqual(self.user.profiles.count(), before)

    def test_cannot_switch_to_other_users_profile(self):
        foreign = Profile.objects.create(user=self.other, name='Foreign')
        resp = self.client.get(reverse('accounts:switch_profile', args=[foreign.id]))
        self.assertEqual(resp.status_code, 404)

class LogoutTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('owner', password='x')
        self.client.force_login(self.user)

    def test_get_logout_not_allowed(self):
        # Django 5.x: logout via GET is rejected (405).
        resp = self.client.get(reverse('accounts:logout'))
        self.assertEqual(resp.status_code, 405)

    def test_post_logout_works(self):
        resp = self.client.post(reverse('accounts:logout'))
        self.assertRedirects(resp, reverse('accounts:login'))
        # Session no longer authenticated -> protected page redirects to login.
        prot = self.client.get(reverse('accounts:settings'))
        self.assertEqual(prot.status_code, 302)
        self.assertIn(reverse('accounts:login'), prot.headers['Location'])


from datetime import timedelta

from django.utils import timezone, translation

from apps.accounts.admin import UserCreateForm


class SubscriptionTest(TestCase):
    def test_period_end_durations(self):
        start = timezone.now().replace(month=1, day=15)
        self.assertEqual(User.period_end('3d', start), start + timedelta(days=3))
        self.assertEqual(User.period_end('1m', start), start.replace(month=2))
        self.assertEqual(User.period_end('3m', start), start.replace(month=4))
        self.assertEqual(User.period_end('6m', start), start.replace(month=7))
        self.assertEqual(User.period_end('1y', start), start.replace(year=start.year + 1))

    def test_period_end_clamps_short_month(self):
        # Jan 31 + 1 month -> Feb 28/29, never an invalid date.
        start = timezone.now().replace(month=1, day=31)
        end = User.period_end('1m', start)
        self.assertEqual(end.month, 2)
        self.assertIn(end.day, (28, 29))

    def test_active_until_expiry(self):
        u = User.objects.create_user('u', password='x')
        u.subscription_until = timezone.now() + timedelta(minutes=5)
        self.assertTrue(u.subscription_active)
        u.subscription_until = timezone.now() - timedelta(minutes=1)
        self.assertFalse(u.subscription_active)

    def test_disabled_subscription_blocks(self):
        u = User.objects.create_user('u', password='x')
        u.is_active_subscription = False
        u.subscription_until = timezone.now() + timedelta(days=30)
        self.assertFalse(u.subscription_active)

    def test_admin_add_user_page_and_create(self):
        # Regression: the admin add page must render (GET 200) and create a user
        # with the chosen plan. Extending the wrong base form broke get_form with
        # "Unknown field(s) (usable_password)".
        admin = User.objects.create_superuser('boss', password='x')
        self.client.force_login(admin)
        add_url = reverse('admin:accounts_user_add')

        self.assertEqual(self.client.get(add_url).status_code, 200)

        resp = self.client.post(add_url, {
            'username': 'newcust', 'usable_password': 'true',
            'password1': 'Superpass123!', 'password2': 'Superpass123!',
            'subscription_plan': '1m',
            'profiles-TOTAL_FORMS': '0', 'profiles-INITIAL_FORMS': '0',
            'profiles-MIN_NUM_FORMS': '0', 'profiles-MAX_NUM_FORMS': '1000',
        })
        self.assertEqual(resp.status_code, 302)
        u = User.objects.get(username='newcust')
        self.assertEqual(u.subscription_plan, '1m')
        # Created within the last minute, so expiry is ~now + 1 month and live.
        self.assertGreater(u.subscription_until, timezone.now() + timedelta(days=27))
        self.assertTrue(u.subscription_active)

    def test_create_form_sets_end_date_from_plan(self):
        form = UserCreateForm(data={
            'username': 'newcust', 'password1': 'superpass123', 'password2': 'superpass123',
            'subscription_plan': '3m',
        })
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertEqual(user.subscription_plan, '3m')
        self.assertGreater(user.subscription_until, timezone.now() + timedelta(days=80))
        self.assertTrue(user.is_active_subscription)

    def test_change_form_recomputes_only_on_plan_change(self):
        admin = User.objects.create_superuser('boss', password='x')
        self.client.force_login(admin)
        u = User.objects.create_user('cust', password='x')
        u.subscription_plan = '1m'
        stale = (timezone.now() - timedelta(days=100)).replace(microsecond=0)
        u.subscription_until = stale  # stale on purpose
        u.save()

        url = reverse('admin:accounts_user_change', args=[u.id])

        def post(plan):
            # subscription_until uses the admin split date/time widget (_0 / _1).
            return self.client.post(url, {
                'username': 'cust', 'subscription_plan': plan,
                'subscription_until_0': stale.strftime('%Y-%m-%d'),
                'subscription_until_1': stale.strftime('%H:%M:%S'),
                'is_active_subscription': 'on', 'note': '',
                'date_joined_0': '2026-01-01', 'date_joined_1': '00:00:00',
                'first_name': '', 'last_name': '', 'email': '',
                'profiles-TOTAL_FORMS': '0', 'profiles-INITIAL_FORMS': '0',
                'profiles-MIN_NUM_FORMS': '0', 'profiles-MAX_NUM_FORMS': '1000',
            })

        # Re-saving with the SAME plan must not silently extend the date.
        post('1m')
        u.refresh_from_db()
        self.assertEqual(u.subscription_until.date(), stale.date())

        # Changing the plan recomputes from now and reactivates.
        post('6m')
        u.refresh_from_db()
        self.assertGreater(u.subscription_until, timezone.now() + timedelta(days=170))
        self.assertTrue(u.is_active_subscription)


class SubscriptionMiddlewareTest(TestCase):
    def test_expired_user_redirected_to_notice(self):
        u = User.objects.create_user('cust', password='x')
        u.subscription_until = timezone.now() - timedelta(days=1)
        u.save()
        self.client.force_login(u)
        resp = self.client.get(reverse('analytics:dashboard'))
        self.assertRedirects(resp, reverse('accounts:subscription_expired'))

    def test_expired_user_sees_notice_page(self):
        u = User.objects.create_user('cust', password='x')
        u.subscription_until = timezone.now() - timedelta(days=1)
        u.save()
        self.client.force_login(u)
        resp = self.client.get(reverse('accounts:subscription_expired'))
        self.assertEqual(resp.status_code, 200)

    def test_active_user_not_blocked(self):
        u = User.objects.create_user('cust', password='x')
        u.subscription_until = timezone.now() + timedelta(days=10)
        u.save()
        self.client.force_login(u)
        resp = self.client.get(reverse('analytics:dashboard'))
        self.assertEqual(resp.status_code, 200)

    def test_staff_never_blocked(self):
        admin = User.objects.create_user('boss', password='x', is_staff=True)
        admin.subscription_until = timezone.now() - timedelta(days=999)
        admin.save()
        self.client.force_login(admin)
        resp = self.client.get(reverse('analytics:dashboard'))
        self.assertEqual(resp.status_code, 200)


class LanguageSwitchTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('owner', password='x')
        self.client.force_login(self.user)

    def test_set_language_persists_and_translates(self):
        # Switch to Uzbek.
        resp = self.client.post(reverse('set_language'),
                                {'language': 'uz', 'next': reverse('accounts:settings')})
        self.assertEqual(resp.status_code, 302)
        page = self.client.get(reverse('accounts:settings'))
        body = page.content.decode()
        self.assertIn('Sozlamalar', body)       # uz nav label
        self.assertIn('Hisobotlar', body)        # "Список отчётов" -> uz
        self.assertIn('Tannarx', body)           # "Себестоимость" -> uz

        # Switch to Russian.
        self.client.post(reverse('set_language'),
                         {'language': 'ru', 'next': reverse('accounts:settings')})
        body = self.client.get(reverse('accounts:settings')).content.decode()
        self.assertIn('Настройки', body)         # "Sozlamalar" -> ru
        self.assertIn('Дашборд', body)           # "Dashboard" -> ru
        self.assertIn('ИНСТРУМЕНТЫ', body)       # "VOSITALAR" -> ru

    def test_uz_catalog_loaded(self):
        with translation.override('uz'):
            self.assertEqual(translation.gettext('Себестоимость'), 'Tannarx')
        with translation.override('ru'):
            self.assertEqual(translation.gettext('Sozlamalar'), 'Настройки')
