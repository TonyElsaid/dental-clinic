from django import forms
from django.utils.translation import gettext_lazy as _

from accounts.mixins import BootstrapFormMixin

from .models import Service


class ServiceForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Service
        fields = ["name", "description", "price", "duration_minutes", "is_active"]
        labels = {
            "name": _("Name"),
            "description": _("Description"),
            "price": _("Price"),
            "duration_minutes": _("Duration (minutes)"),
            "is_active": _("Active"),
        }
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}
