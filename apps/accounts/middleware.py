from django.shortcuts import redirect
from django.urls import reverse


class SubscriptionMiddleware:
    """Block logged-in users whose subscription has expired or been disabled.

    A user can still authenticate (so they reach a clear "renew your plan" page
    instead of a confusing login error), but every app page redirects them to the
    subscription-expired notice until an admin renews ``subscription_until`` or
    flips ``is_active_subscription`` back on.

    Admins (staff/superuser) are never blocked, and a small set of paths stay
    reachable so the user can read the notice, switch language, and log out.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)

        if (user is not None and user.is_authenticated
                and not user.is_staff
                and not user.subscription_active
                and not self._is_exempt(request.path)):
            return redirect('accounts:subscription_expired')

        return self.get_response(request)

    def _is_exempt(self, path):
        """Paths a blocked user is still allowed to reach."""
        exempt = (
            reverse('accounts:subscription_expired'),
            reverse('accounts:logout'),
            reverse('accounts:login'),
            reverse('landing'),
        )
        if path in exempt:
            return True
        # Admin panel, language switch and static/media must keep working.
        prefixes = ('/admin/', '/i18n/', '/static/', '/media/')
        return path.startswith(prefixes)