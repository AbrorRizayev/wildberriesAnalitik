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


from django.utils import translation


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
