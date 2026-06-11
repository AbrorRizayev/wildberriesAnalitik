"""Template filters mirroring the formatters in js/main.js."""
from django import template

register = template.Library()


def _is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


@register.filter
def fmt(num):
    """Round to integer, space-separated thousands (ru-RU style)."""
    if not _is_num(num):
        return '—'
    return f'{round(num):,}'.replace(',', ' ')


@register.filter
def money(num, currency='₽'):
    if not _is_num(num):
        return '—'
    return f'{fmt(num)} {currency}'


@register.filter
def money_short(num, currency='₽'):
    if not _is_num(num):
        return '—'
    a = abs(num)
    if a >= 1_000_000:
        return f'{num / 1_000_000:.2f}M {currency}'
    if a >= 1_000:
        return f'{num / 1_000:.1f}K {currency}'
    return f'{fmt(num)} {currency}'


@register.filter
def percent(num):
    if not _is_num(num):
        return '—'
    return f'{num:.1f}%'