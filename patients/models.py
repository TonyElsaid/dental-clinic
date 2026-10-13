from datetime import date

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q
from django.urls import reverse

phone_validator = RegexValidator(
    regex=r"^\+?[0-9 ()\-]{7,20}$",
    message="Enter a valid phone number (digits, spaces, +, -, parentheses).",
)


class PatientQuerySet(models.QuerySet):
    def visible_to(self, user):
        """Restrict patients according to the viewer's role.

        * admin / receptionist: everyone
        * dentist: only patients that have an appointment with them
        * patient: only their own record
        """
        if user.is_front_desk:
            return self
        if user.is_dentist:
            return self.filter(appointments__dentist=user).distinct()
        if user.is_patient_user:
            return self.filter(user=user)
        return self.none()

    def search(self, text):
        """Every word must match name, phone or email."""
        queryset = self
        for term in (text or "").split():
            queryset = queryset.filter(
                Q(first_name__icontains=term)
                | Q(last_name__icontains=term)
                | Q(phone__icontains=term)
                | Q(email__icontains=term)
            )
        return queryset


class Patient(models.Model):
    class Gender(models.TextChoices):
        FEMALE = "F", "Female"
        MALE = "M", "Male"
        OTHER = "O", "Other / prefer not to say"

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1, choices=Gender.choices, default=Gender.OTHER)
    phone = models.CharField(max_length=20, validators=[phone_validator])
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_phone = models.CharField(
        max_length=20, blank=True, validators=[phone_validator]
    )
    medical_history = models.TextField(blank=True, help_text="Conditions, medications, past surgeries...")
    allergies = models.TextField(blank=True, help_text="Leave blank if none known.")

    # Optional link to a login account for the patient portal.
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="patient_profile",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = PatientQuerySet.as_manager()

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return self.full_name

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def age(self):
        today = date.today()
        dob = self.date_of_birth
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    def get_absolute_url(self):
        return reverse("patients:detail", args=[self.pk])
