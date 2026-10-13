from django import template

register = template.Library()

_BADGES = {
    "scheduled": "primary",
    "completed": "success",
    "cancelled": "secondary",
    "no_show": "danger",
    "pending": "warning text-dark",
    "partial": "info text-dark",
    "paid": "success",
}


@register.filter
def badge_class(value):
    """Map an appointment/invoice status to a Bootstrap badge colour."""
    return _BADGES.get(str(value), "secondary")
