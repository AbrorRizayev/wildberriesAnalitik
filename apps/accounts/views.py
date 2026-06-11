from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Profile

SESSION_KEY = 'active_profile_id'


@login_required
def subscription_expired(request):
    """Notice shown to a logged-in user whose subscription has lapsed.

    Active subscribers have no reason to be here, so bounce them back to the app.
    """
    if request.user.subscription_active:
        return redirect('analytics:dashboard')
    return render(request, 'accounts/subscription_expired.html', {
        'subscription_until': request.user.subscription_until,
    })


def get_active_profile(request):
    """Return the request user's active profile, creating a default one if none exist.

    The active profile id is kept in the session. Always scoped to request.user,
    so a user can never select another user's profile.
    """
    if not request.user.is_authenticated:
        return None

    profiles = list(request.user.profiles.filter(is_active=True))
    if not profiles:
        # First login: create a default profile from the username.
        default = Profile.objects.create(
            user=request.user,
            name=request.user.get_full_name() or request.user.username,
        )
        request.session[SESSION_KEY] = default.id
        return default

    pid = request.session.get(SESSION_KEY)
    for p in profiles:
        if p.id == pid:
            return p
    # Stale or missing session value: fall back to the first profile.
    request.session[SESSION_KEY] = profiles[0].id
    return profiles[0]


@login_required
def switch_profile(request, profile_id):
    # get_object_or_404 scoped to the user => ownership enforced.
    profile = get_object_or_404(Profile, id=profile_id, user=request.user)
    request.session[SESSION_KEY] = profile.id
    return redirect(request.META.get('HTTP_REFERER') or 'analytics:dashboard')


@login_required
@require_POST
def profile_create(request):
    """Create a new company (Profile) under the current user and switch to it.

    Each profile owns its own data (base rows, costs, reports, ...), so the new
    company starts empty with its own separate accounting.
    """
    name = (request.POST.get('name') or '').strip()
    if not name:
        return redirect(request.META.get('HTTP_REFERER') or 'analytics:dashboard')

    profile = Profile(user=request.user, name=name)
    profile.brand = (request.POST.get('brand') or '').strip()
    profile.country = request.POST.get('country') or profile.country
    profile.currency = request.POST.get('currency') or profile.currency
    profile.inn = (request.POST.get('inn') or '').strip()
    try:
        profile.tax_type = int(request.POST.get('tax_type') or profile.tax_type)
    except (TypeError, ValueError):
        pass
    try:
        profile.tax_rate = float(request.POST.get('tax_rate') or profile.tax_rate)
    except (TypeError, ValueError):
        pass
    profile.save()

    # Make the freshly created company the active one.
    request.session[SESSION_KEY] = profile.id
    return redirect('accounts:settings')


@login_required
def settings_page(request):
    from apps.reports.models import BaseRow, Cost, ListReport
    profile = get_active_profile(request)
    return render(request, 'accounts/settings.html', {
        'active_page': 'settings',
        'profile': profile,
        'tax_types': Profile.TAX_TYPES,
        'list_count': ListReport.objects.filter(profile=profile).count(),
        'base_count': BaseRow.objects.filter(profile=profile).count(),
        'costs_count': Cost.objects.filter(profile=profile).count(),
    })


@login_required
@require_POST
def settings_save(request):
    from apps.reports.services import recompute_tax
    profile = get_active_profile(request)

    old_tax_type, old_tax_rate = profile.tax_type, profile.tax_rate

    profile.name = (request.POST.get('name') or profile.name).strip()
    profile.brand = (request.POST.get('brand') or '').strip()
    profile.country = request.POST.get('country') or profile.country
    profile.currency = request.POST.get('currency') or profile.currency
    profile.inn = (request.POST.get('inn') or '').strip()
    try:
        profile.tax_type = int(request.POST.get('tax_type') or profile.tax_type)
    except (TypeError, ValueError):
        pass
    try:
        profile.tax_rate = float(request.POST.get('tax_rate') or 0)
    except (TypeError, ValueError):
        profile.tax_rate = 0
    profile.save()

    # Tax settings only affect columns AA/AB; recompute just those (fast SQL update)
    # instead of re-running the whole formula engine over every row.
    tax_changed = (profile.tax_type != old_tax_type
                   or float(profile.tax_rate) != float(old_tax_rate))
    if tax_changed:
        recompute_tax(profile)

    return redirect('accounts:settings')