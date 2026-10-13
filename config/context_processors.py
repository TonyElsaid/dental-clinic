from django.conf import settings


def clinic(request):
    """Expose clinic branding to every template."""
    return {"CLINIC_NAME": settings.CLINIC_NAME}
