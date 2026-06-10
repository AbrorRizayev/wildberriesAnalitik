from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse


def landing(request):
    """Public marketing landing page served at the domain root (no auth required).

    This is the page a search engine indexes for the domain, so it carries the
    SEO meta/OG/JSON-LD tags. Authenticated users still see it, but the CTA
    switches to "go to dashboard".
    """
    return render(request, 'landing.html', {
        'is_authed': request.user.is_authenticated,
    })


def robots_txt(request):
    """Minimal robots.txt allowing indexing and pointing crawlers to the sitemap."""
    sitemap_url = request.build_absolute_uri(reverse('sitemap_xml'))
    lines = [
        'User-agent: *',
        'Allow: /$',
        'Allow: /login/',
        'Disallow: /admin/',
        'Disallow: /dashboard/',
        'Disallow: /upload/',
        '',
        f'Sitemap: {sitemap_url}',
    ]
    return HttpResponse('\n'.join(lines), content_type='text/plain')


def sitemap_xml(request):
    """Tiny sitemap listing the public pages so search engines find the domain root."""
    urls = [
        request.build_absolute_uri(reverse('landing')),
        request.build_absolute_uri(reverse('accounts:login')),
    ]
    items = ''.join(
        f'<url><loc>{u}</loc><changefreq>weekly</changefreq><priority>{p}</priority></url>'
        for u, p in zip(urls, ['1.0', '0.5'])
    )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f'{items}</urlset>'
    )
    return HttpResponse(xml, content_type='application/xml')