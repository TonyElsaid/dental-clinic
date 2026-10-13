from django import forms
from django.contrib.auth import password_validation
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from accounts.mixins import BootstrapFormMixin
from accounts.models import User

from .models import Patient


class PatientForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Patient
        fields = [
            "first_name", "last_name", "date_of_birth", "gender", "phone", "email",
            "emergency_contact_name", "emergency_contact_phone",
            "address", "medical_history", "allergies",
        ]
        labels = {
            "first_name": _("First name"),
            "last_name": _("Last name"),
            "date_of_birth": _("Date of birth"),
            "gender": _("Gender"),
            "phone": _("Phone"),
            "email": _("Email"),
            "emergency_contact_name": _("Emergency contact name"),
            "emergency_contact_phone": _("Emergency contact phone"),
            "address": _("Address"),
            "medical_history": _("Medical history"),
            "allergies": _("Allergies"),
        }
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "address": forms.Textarea(attrs={"rows": 2}),
            "medical_history": forms.Textarea(attrs={"rows": 3}),
            "allergies": forms.Textarea(attrs={"rows": 2}),
        }

    def clean_date_of_birth(self):
        dob = self.cleaned_data["date_of_birth"]
        if dob > timezone.localdate():
            raise forms.ValidationError(_("Date of birth cannot be in the future."))
        return dob


class PortalAccountForm(BootstrapFormMixin, forms.Form):
    """Create a patient-portal login for an existing patient record."""

    username = forms.CharField(max_length=150)
    password1 = forms.CharField(label=_("Password"), widget=forms.PasswordInput)
    password2 = forms.CharField(label=_("Confirm password"), widget=forms.PasswordInput)

    def __init__(self, *args, patient=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.patient = patient

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError(_("That username is already taken."))
        return username

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("password1"), cleaned.get("password2")
        if p1 and p2:
            if p1 != p2:
                self.add_error("password2", _("The two passwords do not match."))
            else:
                try:
                    password_validation.validate_password(p1)
                except forms.ValidationError as exc:
                    self.add_error("password1", exc)
        return cleaned

    def save(self):
        user = User.objects.create_user(
            username=self.cleaned_data["username"],
            password=self.cleaned_data["password1"],
            first_name=self.patient.first_name,
            last_name=self.patient.last_name,
            email=self.patient.email,
            role=User.Role.PATIENT,
        )
        self.patient.user = user
        self.patient.save(update_fields=["user"])
        return user
