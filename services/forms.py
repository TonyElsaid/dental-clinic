from django import forms

from accounts.mixins import BootstrapFormMixin

from .models import Service


class ServiceForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Service
        fields = ["name", "description", "price", "duration_minutes", "is_active"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}
