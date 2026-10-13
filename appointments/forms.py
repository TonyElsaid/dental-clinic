from django import forms
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from accounts import roles
from accounts.mixins import BootstrapFormMixin
from accounts.models import User
from patients.models import Patient
from services.models import Service

from .models import Appointment


class AppointmentForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ["patient", "dentist", "service", "date", "start_time", "status", "notes"]
        labels = {
            "patient": _("Patient"),
            "dentist": _("Dentist"),
            "service": _("Service"),
            "date": _("Date"),
            "start_time": _("Start time"),
            "status": _("Status"),
            "notes": _("Notes"),
        }
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "start_time": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["patient"].queryset = Patient.objects.all()
        self.fields["dentist"].queryset = User.objects.filter(role=roles.DENTIST, is_active=True)
        services = Q(is_active=True)
        if self.instance.pk:  # keep a since-retired service selectable when editing
            services |= Q(pk=self.instance.service_id)
        self.fields["service"].queryset = Service.objects.filter(services)

    def clean_date(self):
        date = self.cleaned_data["date"]
        if not self.instance.pk and date < timezone.localdate():
            raise forms.ValidationError(_("New appointments cannot be booked in the past."))
        return date
