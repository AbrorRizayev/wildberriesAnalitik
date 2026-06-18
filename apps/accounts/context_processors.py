from .models import Profile
from .views import get_active_profile


def profile(request):
    """Expose the active profile + the user's profile list to every template
    (used by the sidebar/topbar that appear on all pages).
    """
    if not request.user.is_authenticated:
        return {}
    active = get_active_profile(request)
    profiles = list(request.user.profiles.filter(is_active=True))
    limit = request.user.max_companies
    return {
        'active_profile': active,
        'profiles': profiles,
        # Choices for the "add company" modal in the topbar.
        'tax_types_choices': Profile.TAX_TYPES,
        # Per-user company limit (set by admin) + whether more can be added.
        'company_limit': limit,
        'can_add_company': len(profiles) < limit,
    }